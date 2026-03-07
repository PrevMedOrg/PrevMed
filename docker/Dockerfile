# Use Python 3.13.5 slim for smaller image size
FROM python:3.13.5-slim

# Build argument to control installation mode:
# - "local": Install from local repository (default, for development)
# - "pypi": Install from PyPI (for production deployment)
ARG INSTALL_MODE=local

# Set environment variables to prevent Python from writing pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies
# - r-base: R language support for scoring scripts
# - r-base-dev: R development headers needed for rpy2
# - build-essential: gcc, g++, make for compiling Python packages with C extensions
# - python3-dev: Python development headers for compilation
# - libtirpc-dev: Required for rpy2 on some systems
# - curl: For uv installation
RUN apt-get update && apt-get install -y --no-install-recommends \
    r-base \
    r-base-dev \
    build-essential \
    python3-dev \
    libtirpc-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast Python package management
# Copy from official uv image is more reliable than install script
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Create app directory and set as working directory
WORKDIR /app

# Copy setup files first for better layer caching
# README.md is needed by setup.py for long_description
COPY --chown=nobody:nogroup setup.py .
COPY --chown=nobody:nogroup README.md .
COPY --chown=nobody:nogroup PrevMed/__init__.py PrevMed/__init__.py

# Install Python dependencies using uv based on INSTALL_MODE
# - local mode: Install from current directory (development)
# - pypi mode: Install from PyPI (production)
RUN if [ "$INSTALL_MODE" = "pypi" ]; then \
        echo "Installing PrevMed from PyPI..." && \
        uv pip install --system PrevMed; \
    else \
        echo "Installing PrevMed from local repository..." && \
        uv pip install --system .; \
    fi

# Copy the rest of the application
COPY --chown=nobody:nogroup . .

# Create directories for logs and data with proper permissions
RUN mkdir -p /app/logs /app/survey_data && \
    chown -R nobody:nogroup /app/logs /app/survey_data

# Switch to nobody user (UID 65534) for security
USER nobody

# Expose the default Gradio port
EXPOSE 7860

# Set the entrypoint to the prevmed CLI
ENTRYPOINT ["python", "-m", "PrevMed"]

# Default command - can be overridden in docker-compose.yml or docker run
CMD ["--survey-yaml", "examples/ProbaLYNCH/ProbaLYNCH.yaml", "--scoring-script", "examples/ProbaLYNCH/ProbaLYNCH.R"]
