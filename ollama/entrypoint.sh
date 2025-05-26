#!/bin/sh

# Start Ollama in the background
ollama serve &

# Wait a bit for server to initialize
sleep 5

# Pull the LLaMA3 model
curl -X POST http://localhost:11434/api/pull -H "Content-Type: application/json" -d '{"name": "llama3.2:1b"}'

# Start nginx in the foreground
nginx -g 'daemon off;'
