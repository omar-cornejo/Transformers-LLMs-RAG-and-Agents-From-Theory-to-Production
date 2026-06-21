#!/bin/sh
ollama serve &
sleep 2
for model in "$LLM_MODEL" "$LLM_VISION_MODEL"; do
  if ! ollama list | grep -q "$model"; then
    echo "Model $model not found, pulling..."
    ollama pull "$model"
  fi
done
wait
