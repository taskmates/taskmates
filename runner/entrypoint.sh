#!/bin/bash

# Print current user and group information
#echo "Current user: $(id)"

# Check Docker socket permissions
#echo "Docker socket permissions:"
#ls -l /var/run/docker.sock

# Print environment variables
#echo "Environment variables:"
#env

# Check Docker client version
#echo "Docker client version:"
#docker version --format '{{.Client.Version}}'

# Check Docker server version
#echo "Docker server version:"
#docker version --format '{{.Server.Version}}' || echo "Failed to get server version"

# Check Docker info
#echo "Docker info:"
#docker info || echo "Failed to get Docker info"

# List contents of current directory
#echo "Contents of current directory:"
#ls -la

# Check if Docker is available
if ! docker ps >/dev/null 2>&1; then
    echo "Error: Docker is not available. Make sure the Docker socket is properly mounted."
    echo "Docker socket error details:"
    docker ps
    exit 1
fi

#echo "Docker is available. Proceeding with container startup."

# Use the devcontainer configuration to start other containers
if [ -f "/devcontainer/docker-compose.yml" ]; then
    docker-compose -f /devcontainer/docker-compose.yml up -d
elif [ -f "/devcontainer/docker-compose.yaml" ]; then
    docker-compose -f /devcontainer/docker-compose.yaml up -d
else
    echo "Warning: Neither /devcontainer/docker-compose.yml nor /devcontainer/docker-compose.yaml found. Skipping container startup."
fi

# Keep the container running
tail -f /dev/null
