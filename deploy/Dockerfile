FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg curl && \
    rm -rf /var/lib/apt/lists/*

COPY server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server /app/server

# 前端产物目录
RUN mkdir -p /app/web/dist

ENV DATA_DIR=/app/server/data
RUN mkdir -p /app/server/data

EXPOSE 8001

CMD ["python", "-m", "uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8001"]
