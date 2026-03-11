# The Brownfield Cartographer - Docker Environment
# Use a specialized uv image for faster builds
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

WORKDIR /app

# Install dependencies first for caching
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    uv sync --frozen --no-install-project --no-dev

# Copy the rest of the application
ADD . /app

# Final stage
FROM python:3.12-slim-bookworm

WORKDIR /app

# Copy the environment from the builder
COPY --from=builder /app /app

# Install system dependencies for docling/torch if needed
# (Assuming slim is enough for basic CPU run, otherwise add libgl1, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Define volume for target repository analysis
VOLUME /repo

# Set entrypoint
ENTRYPOINT ["python", "src/cli.py"]
CMD ["--help"]


