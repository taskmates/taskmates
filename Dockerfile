# syntax = docker/dockerfile:1.5
FROM python:3.11.2-bullseye AS builder

RUN apt-get update && apt-get install -y \
  cmake \
  pkg-config \
  portaudio19-dev

RUN curl -sSL https://install.python-poetry.org | python3 -

WORKDIR /app

COPY ./pyproject.toml ./poetry.lock* /app/

ENV PATH="/root/.local/bin:$PATH" \
  PYTHONFAULTHANDLER=1 \
  PYTHONUNBUFFERED=1 \
  PYTHONHASHSEED=random \
  PIP_NO_CACHE_DIR=off \
  PIP_DISABLE_PIP_VERSION_CHECK=on \
  PIP_DEFAULT_TIMEOUT=100 \
  # Poetry's configuration:
  POETRY_NO_INTERACTION=1 \
  POETRY_VIRTUALENVS_CREATE=false \
  POETRY_CACHE_DIR='/var/cache/pypoetry' \
  POETRY_HOME='/usr/local' \
  POETRY_VERSION=1.7.1

RUN poetry install --no-root --no-interaction

COPY . .

RUN poetry install --no-interaction

EXPOSE 5000
ENV QUART_APP=app
CMD poetry run hypercorn --bind 0.0.0.0:5000 taskmates.server.server:app
