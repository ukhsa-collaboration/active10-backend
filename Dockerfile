FROM python:3.10-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y \
    python3-dev \
    default-libmysqlclient-dev \
    pkg-config \
    build-essential \
    netcat-openbsd \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
COPY ./private_key.pem /app/

RUN pip install --no-cache-dir -r requirements.txt

COPY entrypoint.sh /app/

RUN chmod +x /app/entrypoint.sh

COPY . .

EXPOSE 8000
