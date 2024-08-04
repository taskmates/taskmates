FROM alpine:latest

# Install Docker and other necessary tools
RUN apk add --no-cache \
    docker \
    docker-compose \
    bash \
    curl

# Copy your devcontainer configuration
COPY .devcontainer /devcontainer

# Set up an entrypoint script
COPY runner/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
