# ☕ Lumière Coffee — Docker image
# Build:  docker build -t lumiere-coffee .
# Run:    docker run -p 8000:8000 lumiere-coffee

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy dependency list first (layer-cache friendly)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the app
COPY . .

# Expose the port the server listens on
EXPOSE 8000

# Environment defaults (override at runtime with -e or docker-compose)
ENV PORT=8000

# Start the server
CMD ["python", "server.py"]
