FROM python:3.10-slim

EXPOSE 8000

RUN useradd --user-group --system --create-home --no-log-init app && chown -R app /app

WORKDIR /app

ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y \
    python3-dev \
    pkg-config \
    build-essential \
    netcat-openbsd \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY . .

RUN chmod +x /app/entrypoint.sh

RUN pip install --no-cache-dir -r requirements.txt

# Install AWS RDS TLS certificate
RUN curl https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem -o /etc/ssl/certs/global-bundle.pem \
  && update-ca-certificates

USER app

ENTRYPOINT ["/app/entrypoint.sh"]