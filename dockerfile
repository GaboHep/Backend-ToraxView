# Dockerfile
FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Dependencias mínimas para OpenCV y PIL
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Instala deps primero (mejor cache)
COPY requirements.txt .
RUN python -m pip install --upgrade pip && pip install -r requirements.txt

# Copia código y pesos
COPY . .

# Reduce hilos para no saturar CPU compartida
ENV TORCH_NUM_THREADS=1
# Railway expone PORT; uvicorn debe usarlo
ENV PORT=8000

EXPOSE 8000

# Usa el PORT inyectado por Railway
CMD ["sh", "-c", "python -m uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
