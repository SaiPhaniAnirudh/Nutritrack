#!/usr/bin/env bash

# Start Ollama daemon in the background
echo "Starting Ollama server..."
ollama serve &

# Wait for Ollama to be ready
echo "Waiting for Ollama to start..."
until curl -s http://127.0.0.1:11434/api/tags >/dev/null; do
    sleep 2
done
echo "Ollama is ready!"

# Pull the model (this will execute on Hugging Face servers)
echo "Pulling llava-phi3 model..."
ollama pull llava-phi3

# Start the Flask AI server on port 7860 (Hugging Face expects port 7860)
echo "Starting NutriTrack AI server..."
python Llm_server.py --port 7860 --host 0.0.0.0
