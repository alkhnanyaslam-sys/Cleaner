FROM python:3.11-slim

# System deps: ffmpeg is required for audio/video extraction
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
# CPU-only torch by default (smaller image). For GPU, override with
# --build-arg TORCH_INDEX and pass the CUDA wheel index instead.
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p temp logs database

ENV PYTHONUNBUFFERED=1

CMD ["python", "main.py"]
