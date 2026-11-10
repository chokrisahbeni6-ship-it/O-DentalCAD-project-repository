FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libgl1 libglib2.0-0 libxrender1 curl \
    && rm -rf /var/lib/apt/lists/*
# L'application ne tourne plus en administrateur
RUN useradd --create-home --uid 10001 app \
    && mkdir -p /data/results && chown app:app /data/results
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD curl -fs http://localhost:8000/health || exit 1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
