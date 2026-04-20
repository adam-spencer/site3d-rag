FROM python:3.10-slim

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
RUN curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR="/usr/local/bin" sh

ENV HOME=/home/user
ENV PATH="/usr/local/bin:$PATH"
WORKDIR $HOME/app

COPY pyproject.toml uv.lock ./
RUN uv pip install --system -r pyproject.toml

COPY . .

# HF Spaces requires 0.0.0.0 binding
CMD ["uvicorn", "api.server:app", "--host", "0.0.0.0", "--port", "8000"]
