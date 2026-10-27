# Stage 1: build the React app
FROM node:20-alpine AS web
WORKDIR /web
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Python API that also serves the built UI from the same origin
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./
COPY --from=web /web/dist ./static
ENV PORT=8000
EXPOSE 8000
# bootstrap fetches Elexon data only if backend/data/*.csv were not committed
CMD ["sh", "-c", "python -m app.bootstrap && uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
