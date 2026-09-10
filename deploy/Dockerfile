# Stage 1: Build frontend
FROM node:18-slim AS frontend-builder
WORKDIR /app/web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

# Stage 2: Python backend
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg curl && \
    rm -rf /var/lib/apt/lists/*

COPY server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server /app/server

# Copy built frontend into nginx html directory
RUN mkdir -p /usr/share/nginx/html
COPY --from=frontend-builder /app/web/dist /usr/share/nginx/html

ENV DATA_DIR=/app/server/data
RUN mkdir -p /app/server/data

EXPOSE 8001

CMD ["python", "-m", "uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8001"]
