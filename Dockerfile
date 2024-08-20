# syntax=docker/dockerfile:1.5
FROM python:3.11-slim-bullseye

# Install build dependencies and tools
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    make \
    fd-find \
    ack-grep \
    curl \
    git \
    && curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg \
    && chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
    && apt-get update \
    && apt-get install -y gh \
    && rm -rf /var/lib/apt/lists/* \
    && ln -s $(which fdfind) /usr/local/bin/fd \
    && ln -s $(which ack-grep) /usr/local/bin/ack

# Install poetry
RUN pip install --no-cache-dir poetry

# Create directories
RUN mkdir -p /workspace /opt/taskmates

# Set up TaskMates in /opt/taskmates
WORKDIR /opt/taskmates

# Copy only requirements to cache them in docker layer
COPY pyproject.toml poetry.lock* ./

# Install project dependencies
RUN poetry config virtualenvs.create false \
  && poetry install --no-dev --no-interaction --no-ansi --quiet

# Copy project
COPY . .

# Install the project itself
RUN poetry install --no-dev --no-interaction --no-ansi --quiet

# Set the final working directory to /workspace
WORKDIR /workspace

# Set environment variables
ENV PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random

EXPOSE 55000

ENV QUART_APP=app
CMD ["taskmates", "server", "--host", "0.0.0.0", "--port", "55000", "--working-dir", "/workspace"]
