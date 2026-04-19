FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Install uv globally
RUN curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR="/usr/local/bin" sh

# Set memory-sensitive huggingface properties
ENV HOME=/home/user
ENV PATH="/usr/local/bin:$PATH"
WORKDIR $HOME/app

# Copy dependency files first for caching
COPY pyproject.toml uv.lock ./

# Install dependencies into system layer
RUN uv pip install --system -r pyproject.toml

# Copy project files
COPY . .

# HuggingFace requires explicit 0.0.0.0 bindings for external accessibility!
CMD ["uvicorn", "api.server:app", "--host", "0.0.0.0", "--port", "8000"]
