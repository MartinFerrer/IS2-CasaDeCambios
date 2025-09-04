# syntax=docker/dockerfile:1.7

# This Dockerfile was modified from the following article:
# https://medium.com/@hmbarotov/dockerizing-django-with-uv-postgres-and-redis-e1dd9abe9640
# Use a Python slim bookworm image with uv pre-installed
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

# Change the working directory to the app directory
WORKDIR /app

# Set environment variables:
# Prevent Python from writing .pyc files to disc
# Prevent Python from buffering stdout and stderr (for logging)
# Enable uv bytecode compilation
# Use copy mode for uv (no symlinks)
# Don't download Python versions (we use the system Python)
# Set the uv tool binary directory
# Set the uv project environment directory
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_TOOL_BIN_DIR=/usr/local/bin \
    UV_PROJECT_ENVIRONMENT=/app/.venv

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    netcat-traditional \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Since there's no point in shipping lock files, we move them
# into a directory that is NOT copied into the runtime image.
# The trailing slash makes COPY create `/_lock/` automagically.
COPY pyproject.toml uv.lock /_lock/

# Install the project's dependencies using the lockfile and settings
# This layer is cached until uv.lock or pyproject.toml change
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

# Copy the rest of the project source code
COPY . /app

# Ensure correct EOF of entrypoint.sh and make it executable
RUN sed -i "s/\r$//g" /app/entrypoint.sh && chmod +x /app/entrypoint.sh

# Download tailwind binary only if it doesn't exist (for production builds)
RUN if [ ! -f /app/static/css/tailwindcss-linux-x64 ]; then \
    curl -sL https://github.com/tailwindlabs/tailwindcss/releases/latest/download/tailwindcss-linux-x64 \
    -o /app/static/css/tailwindcss-linux-x64; \
    fi
RUN chmod +x /app/static/css/tailwindcss-linux-x64

# Compile CSS at build time and fail if output.css missing (for production builds)
RUN /app/static/css/tailwindcss-linux-x64 \
    -i /app/static/css/input.css \
    -o /app/static/css/output.css \
    --minify
RUN test -f /app/static/css/output.css

# Install the project itself
# Installing separately from dependencies allows optimal layer caching
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"

# run entrypoint.sh
ENTRYPOINT ["/app/entrypoint.sh"]
