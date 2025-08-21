############################################
# Node stage: build CSS (Tailwind + daisyUI)
############################################
FROM node:20-alpine AS node-builder
WORKDIR /app

# copy package.json (and package-lock.json if present)
COPY package.json ./
# copy tailwind config and css input file(s)
COPY tailwind.config.js ./
COPY static/css ./static/css

# install node deps and build the css once
RUN npm install --silent
# build minified css (tailwind-build script from your package.json)
RUN npm run tailwind-build

RUN echo "DEBUG:"
RUN npm run tailwind-build && ls -la ./static/css

# syntax=docker/dockerfile:1.7
# This Dockerfile was modified from the following article: 
# https://medium.com/@hmbarotov/dockerizing-django-with-uv-postgres-and-redis-e1dd9abe9640
# Base image: Python slim bookworm
FROM python:3.13-slim-bookworm AS base

# Change the working directory to the app directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/app/.venv

# install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    netcat-traditional \
    curl \
    ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# install uv inside Docker
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Since there's no point in shipping lock files, we move them
# into a directory that is NOT copied into the runtime image.
# The trailing slash makes COPY create `/_lock/` automagically.
COPY pyproject.toml uv.lock /_lock/

# Synchronize dependencies.
# This layer is cached until uv.lock or pyproject.toml change.
RUN --mount=type=cache,target=/root/.cache \
    cd /_lock && \
    uv sync \
    --frozen \
    --no-install-project

# copy entrypoint.sh
COPY ./entrypoint.sh .
RUN sed -i "s/\r$//g" /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# copy project
COPY . .

# Copy the pre-built tailwind output.css from node-builder (if it exists)
# this will overwrite whatever is in /app/static/css/output.css
COPY --from=node-builder /app/static/css/output.css /app/static/css/output.css

# run entrypoint.sh
ENTRYPOINT ["/app/entrypoint.sh"]