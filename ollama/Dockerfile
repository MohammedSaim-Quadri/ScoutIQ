FROM ollama/ollama:0.1.26

# Update package lists and upgrade packages to fix vulnerabilities
RUN apt-get update && apt-get upgrade -y && apt-get clean

# Pull llama3 model on container startup
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
