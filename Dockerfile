FROM python:3.10-slim@sha256:fd76ade0c607f27677bc04be3c60749f400eedc941d9e72967e19a4cedff80c2 AS base

ARG APP_VERSION
ARG APP_CODE_COMMIT_HASH
ENV APP_VERSION="${APP_VERSION:-dev}"
ENV APP_CODE_COMMIT_HASH="${APP_CODE_COMMIT_HASH:-dev}"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/home/app/.local/bin:$PATH"

EXPOSE 8000

WORKDIR /app

# Prefer security updates over reproducability
# hadolint ignore=DL3008
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    pkg-config \
    netcat-openbsd \
    curl \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem \
      -o /usr/local/share/ca-certificates/aws-rds-global-bundle.pem \
 && update-ca-certificates

COPY requirements.txt .

# hadolint ignore=DL3013
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

RUN useradd --user-group --system --create-home app \
 && chown -R app:app /app

COPY --chown=app:app . .

RUN chmod +x /app/entrypoint.sh

USER app

ENTRYPOINT ["/app/entrypoint.sh"]
