FROM python:3.12.9-slim-bookworm@sha256:4c2f7a6b8c9d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends libmagic1 && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --break-system-packages -r requirements.txt

COPY . .

EXPOSE 8000

STOPSIGNAL SIGTERM

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health', timeout=2)" || exit 1

USER 1000:1000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]