import base64
import json
import os
import uuid
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from openai import AsyncOpenAI
from pydantic import BaseModel

from rag_agent import RagAgent

app = FastAPI()
rag_agent = RagAgent()

client = AsyncOpenAI(
    base_url=os.environ.get("LLM_BASE_URL", "http://localhost:11434/v1"),
    api_key=os.environ.get("LLM_API_KEY", "ollama"),
)

LLM_MODEL = os.environ.get("LLM_MODEL", "qwen2.5:1.5b")
LLM_VISION_MODEL = os.environ.get("LLM_VISION_MODEL", "moondream:1.8b")
SYSTEM_PROMPT = os.environ.get(
    "SYSTEM_PROMPT",
    "You are a helpful assistant. Respond in Markdown when formatting is useful (code blocks, lists, headings).",
)

conversations = {}
OUT_OF_SCOPE_REPLY = "I don't have that information in the provided context."


def is_within_context(user_message: str) -> bool:
    return rag_agent.is_in_scope(user_message)


def refusal_payload(conversation_id: str) -> dict:
    return {
        "conversation_id": conversation_id,
        "reply": OUT_OF_SCOPE_REPLY,
        "available_topics": rag_agent.get_supported_topics(),
        "token_usage": None,
        "messages_sent": None,
    }

frontend_path = Path(__file__).parent / "frontend"
if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    conversation_id: str | None = None
    message: str


class ContextResponse(BaseModel):
    conversation_id: str
    messages: list
    token_usage: dict | None = None


@app.get("/")
async def root():
    index_path = frontend_path / "index.html"
    if index_path.exists():
        return HTMLResponse(index_path.read_text())
    return {"status": "ok"}


def get_or_create_conversation(conversation_id: str | None) -> str:
    if conversation_id is None or conversation_id not in conversations:
        conversation_id = str(uuid.uuid4())
        conversations[conversation_id] = {
            "messages": [{"role": "system", "content": SYSTEM_PROMPT}],
            "token_usage": None,
        }
    return conversation_id


def build_messages_for_openai(conv_messages: list, user_content: str | list) -> list:
    result = [m for m in conv_messages if m["role"] != "system"]
    result.insert(0, {"role": "system", "content": SYSTEM_PROMPT})
    result.append({"role": "user", "content": user_content})
    return result


@app.post("/chat")
async def chat(request: ChatRequest):
    conv_id = get_or_create_conversation(request.conversation_id)
    conv = conversations[conv_id]

    if not is_within_context(request.message):
        return refusal_payload(conv_id)

    rag_enriched_message = rag_agent.get_promt(request.message)
    messages = build_messages_for_openai(conv["messages"], rag_enriched_message)

    try:
        response = await client.chat.completions.create(
            model=LLM_MODEL,
            messages=messages,
            stream=False,
        )
        reply = response.choices[0].message.content
        usage = response.usage

        conv["messages"].append({"role": "user", "content": request.message})
        conv["messages"].append({"role": "assistant", "content": reply})
        conv["token_usage"] = {
            "prompt_tokens": usage.prompt_tokens,
            "completion_tokens": usage.completion_tokens,
            "total_tokens": usage.total_tokens,
        }

        return {
            "conversation_id": conv_id,
            "reply": reply,
            "token_usage": conv["token_usage"],
            "messages_sent": messages,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    conv_id = get_or_create_conversation(request.conversation_id)
    conv = conversations[conv_id]

    if not is_within_context(request.message):
        async def refusal_stream():
            yield f"data: {json.dumps({'type': 'token', 'content': OUT_OF_SCOPE_REPLY})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'conversation_id': conv_id, 'token_usage': None, 'messages_sent': None, 'available_topics': rag_agent.get_supported_topics()})}\n\n"

        return StreamingResponse(refusal_stream(), media_type="text/event-stream")

    rag_enriched_message = rag_agent.get_promt(request.message)
    messages = build_messages_for_openai(conv["messages"], rag_enriched_message)

    try:
        stream = await client.chat.completions.create(
            model=LLM_MODEL,
            messages=messages,
            stream=True,
            stream_options={"include_usage": True},
        )

        async def generate():
            full_reply = ""
            final_usage = None

            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_reply += content
                    yield f"data: {json.dumps({'type': 'token', 'content': content})}\n\n"
                if chunk.usage:
                    final_usage = {
                        "prompt_tokens": chunk.usage.prompt_tokens,
                        "completion_tokens": chunk.usage.completion_tokens,
                        "total_tokens": chunk.usage.total_tokens,
                    }

            conv["messages"].append({"role": "user", "content": request.message})
            conv["messages"].append({"role": "assistant", "content": full_reply})
            conv["token_usage"] = final_usage

            yield f"data: {json.dumps({'type': 'done', 'conversation_id': conv_id, 'token_usage': final_usage, 'messages_sent': messages})}\n\n"

        return StreamingResponse(generate(), media_type="text/event-stream")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat/vision")
async def chat_vision(
    conversation_id: str = Form(None),
    message: str = Form(""),
    image: UploadFile = File(None),
):
    conv_id = get_or_create_conversation(conversation_id)
    conv = conversations[conv_id]

    if not image:
        raise HTTPException(status_code=400, detail="No image provided")

    text = message.strip() or "Describe this image"

    content = [{"type": "text", "text": text}]

    image_data = await image.read()
    image_b64 = base64.b64encode(image_data).decode("utf-8")
    mime = image.content_type or "image/png"
    content.append(
        {
            "type": "image_url",
            "image_url": {"url": f"data:{mime};base64,{image_b64}"},
        }
    )

    messages = build_messages_for_openai(conv["messages"], content)

    try:
        response = await client.chat.completions.create(
            model=LLM_VISION_MODEL,
            messages=messages,
            stream=False,
        )
        reply = response.choices[0].message.content
        usage = response.usage

        conv["messages"].append({"role": "user", "content": f"{text} [image attached]"})
        conv["messages"].append({"role": "assistant", "content": reply})
        conv["token_usage"] = {
            "prompt_tokens": usage.prompt_tokens,
            "completion_tokens": usage.completion_tokens,
            "total_tokens": usage.total_tokens,
        }

        return {
            "conversation_id": conv_id,
            "reply": reply,
            "token_usage": conv["token_usage"],
            "messages_sent": messages,
        }
    except Exception as e:
        detail = str(e)
        if "multimodal" in detail.lower() or "vision" in detail.lower():
            raise HTTPException(
                status_code=400,
                detail=f"Model '{LLM_VISION_MODEL}' does not support vision. Use a multimodal model like llava or moondream.",
            )
        raise HTTPException(status_code=500, detail=detail)


@app.get("/context/{conversation_id}")
async def get_context(conversation_id: str):
    conv = conversations.get(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {
        "conversation_id": conversation_id,
        "messages": conv["messages"],
        "token_usage": conv["token_usage"],
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
