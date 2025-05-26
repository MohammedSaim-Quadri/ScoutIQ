#!/bin/sh

#start the ollama server
/bin/ollama serve &

#wait a bit for service to start
sleep 5

# pull the llama3.2 model
curl -X POST http://localhost:11434/api/pull -d '{"name": "llama3.2:1b"}'

# keep container running
sleep 10
tail -f /dev/null
