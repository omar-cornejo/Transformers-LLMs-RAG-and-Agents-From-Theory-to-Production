# EASY-CHATGPT

A chatbot server built with FastAPI (backend) and vanilla JS/HTML/CSS (frontend).
It acts as a proxy between the chat client and an LLM (via Ollama).

## Quick Start

1. Clone this repo and `cd` into it.

2. Copy `.env.example` to `.env` and edit if needed:
   ```bash
   cp .env.example .env
   ```

3. Make sure Ollama is running with your chosen model:
   ```bash
   ollama pull qwen2.5:1.5b
   ```

4. Run with Docker Compose:
   ```bash
   docker compose up
   ```

5. Open http://localhost:6661 in your browser.

## Usage

- **Baseline mode**: sends message, waits for full response.
- **Streaming mode** (default): streams the response token by token via SSE.
- **Vision mode**: attach an image to your message (requires a vision-capable model).

The **Context View** (toggle with the button) shows what's being sent to the model and the token usage.

## Configuration

Edit `.env` to change the model, base URL, API key, or system prompt.

| Variable | Default | Description |
|---|---|---|
| `LLM_MODEL` | `qwen2.5:1.5b` | Model name in Ollama |
| `LLM_BASE_URL` | `http://ollama:11434/v1` | OpenAI-compatible API base URL |
| `LLM_API_KEY` | `ollama` | API key (ollama ignores this) |
| `SYSTEM_PROMPT` | Helpful assistant | System prompt for the model |

## Architecture

```
Browser -> FastAPI (port 6661) -> Ollama (port 11434) -> LLM Model
```

The frontend is vanilla JS served as static files by FastAPI.
