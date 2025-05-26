FROM ollama/ollama:latest

# Install curl and nginx
RUN apt-get update && apt-get install -y curl nginx

# Copy nginx config
COPY default.conf /etc/nginx/sites-enabled/default

# Copy startup script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 80
ENTRYPOINT ["/entrypoint.sh"]
