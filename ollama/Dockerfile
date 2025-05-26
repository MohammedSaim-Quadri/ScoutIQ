FROM ollama/ollama:latest

# Install curl
RUN apt-get update && apt-get install -y curl

# Pull llama3 model on container startup
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
