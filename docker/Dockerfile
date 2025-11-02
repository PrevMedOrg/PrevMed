# Use Python 3.13.5 slim for smaller image size
FROM python:3.13.5-slim

# Set environment variables to prevent Python from writing pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies
# - r-base: R language support for scoring scripts
# - libtirpc-dev: Required for rpy2 on some systems
# - curl: For uv installation
RUN apt-get update && apt-get install -y --no-install-recommends \
    r-base \
    libtirpc-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast Python package management
# Copy from official uv image is more reliable than install script
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Create app directory and set as working directory
WORKDIR /app

# Create non-root user for running the application
RUN useradd -m -u 1000 prevmed && \
    chown -R prevmed:prevmed /app

# Copy setup files first for better layer caching
COPY --chown=prevmed:prevmed setup.py .
COPY --chown=prevmed:prevmed PrevMed/__init__.py PrevMed/__init__.py

# Install Python dependencies using uv (now in PATH)
RUN uv pip install --system .

# Copy the rest of the application
COPY --chown=prevmed:prevmed . .

# Create directories for logs and data with proper permissions
RUN mkdir -p /app/logs /app/survey_data /app/temp_pdfs && \
    chown -R prevmed:prevmed /app/logs /app/survey_data /app/temp_pdfs

# Switch to non-root user
USER prevmed

# Expose the default Gradio port
EXPOSE 7860

# Set the entrypoint to the prevmed CLI
ENTRYPOINT ["python", "-m", "PrevMed"]

# Default command - can be overridden in docker-compose.yml or docker run
CMD ["--survey-yaml", "examples/PREMM5/premm5.yaml", "--scoring-script", "examples/PREMM5/premm5.R"]
