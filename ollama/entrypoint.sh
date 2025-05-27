#!/bin/sh

# Start Ollama in the background
echo "Starting ollama server..."
ollama serve &

# Wait a bit for server to initialize
sleep 15

# Pull the LLaMA3 model
echo "Pulling Llama3 model..."
curl -X POST http://localhost:11434/api/pull -H "Content-Type: application/json" -d '{"name": "llama3.2:1b"}'

# Start nginx in the foreground
echo "Model pulled, Starting nginx..."
nginx -g 'daemon off;'
