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
    && rm -rf /var/lib/apt/lists/* \
    && ln -s $(which fdfind) /usr/local/bin/fd \
    && ln -s $(which ack-grep) /usr/local/bin/ack

WORKDIR /app

# Install poetry
RUN pip install --no-cache-dir poetry

# Copy only requirements to cache them in docker layer
COPY pyproject.toml poetry.lock* /app/

# Install project dependencies
RUN poetry config virtualenvs.create false \
  && poetry install --no-dev --no-interaction --no-ansi --quiet

# Copy project
COPY . .

# Install the project itself
RUN poetry install --no-dev --no-interaction --no-ansi --quiet

# Set environment variables
ENV PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random

EXPOSE 55000

ENV QUART_APP=app
CMD ["hypercorn", "--bind", "0.0.0.0:55000", "taskmates.server.server:app"]
