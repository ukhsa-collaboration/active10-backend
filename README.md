# Active10 Backend Service

A FastAPI-based backend service for the Active10 mobile app, providing activity tracking, and NHS Login integration.

### Project Structure

```
├── api/                    # API endpoints
│   ├── v1/                # Version 1 API routes
│   ├── v2/                # Version 2 API routes
│   ├── nhs_login.py       # NHS Login authentication
│   └── healthcheck.py     # Health monitoring
├── auth/                  # Authentication & authorization
├── crud/                  # Database operations
├── db/                    # Database configuration & migrations
├── models/                # SQLAlchemy database models
├── schemas/               # Pydantic request/response schemas
├── service/               # Business logic layer
├── nhs/                   # NHS API integrations
├── gojauntly/             # GoJauntly integration
├── utils/                 # Utility functions
└── tests/                 # Test suites
```

## Getting Started

### Prerequisites

- Python 3.11+
- PostgreSQL 16+
- Docker

### Quick Start with Docker

1. **Clone and setup environment:**
  ```bash
   git clone <repository-url>
   cd active10-backend
  ```
2. **Start services:**
  ```bash
   docker compose up
  ```
3. **Access the application:**
  - API: `https://active10.localhost`
  - API Documentation: `https://active10.localhost/docs`

## OpenTelemetry Tracing (AWS X-Ray)

The app uses OpenTelemetry to trace incoming requests, database and Redis calls, outbound HTTP, and AWS messages. Spans are sent over OTLP to an ADOT collector, which forwards them to AWS X-Ray. The collector runs as its own service, `adot-collector`, in `docker-compose.yml`, so it starts automatically with the rest of the stack.

### Prerequisites

- AWS credentials with X-Ray write access, either the `AWSXRayDaemonWriteAccess` managed policy or just `xray:PutTraceSegments` and `xray:PutTelemetryRecords`. The collector picks these up from your shell environment or from `~/.aws`, which is mounted read-only into the container. Prefer an IAM role over static keys where you can.
- `AWSXRayReadOnlyAccess` for anyone who needs to view the traces afterwards.
- `AWS_REGION` set to whichever region you want traces in. `collector-config.yaml` defaults this to `eu-west-2` if it isn't set, and traces only show up in the console for that region.

### Setup

Add these to your `.env`:

```bash
OTEL_EXPORTER_OTLP_ENDPOINT=http://adot-collector:4317
OTEL_EXPORTER_OTLP_INSECURE=false
OTEL_SERVICE_NAME=active10-auth
```

Export AWS credentials for local development:

```bash
export AWS_REGION=eu-west-2
export AWS_ACCESS_KEY_ID=<your-key-id>
export AWS_SECRET_ACCESS_KEY=<your-secret-key>
```

then start the stack with `docker compose up --build`.

Run any authenticated request to generate a trace, then open X-Ray traces in CloudWatch and look for the `active10-auth` service. The shared application flow and step attributes are indexed, so traces can be filtered in X-Ray with `annotation[app.flow]` and `annotation[app.step]`.

Trace context is included in SNS and SQS message attributes. Consumers should extract that context before creating their processing span so the producer and consumer appear in the same trace.

If no traces show up, check that the collector container is running and on the `proxy` network, and that the region and IAM permissions are right. The export errors logged while running `make unit-tests` are expected, there's no collector in that environment and the tests don't need one.

## Testing

### Run Test Suite

```bash
# Run all unit tests
make unit-tests
```

### Test Configuration

Tests are configured in `pyproject.toml` with coverage reporting for:

- API endpoints (`api/`)
- Business logic (`service/`)
- Database operations (`crud/`)
- Models (`models/`)
- Authentication (`auth/`)
- NHS integrations (`nhs/`)

## License

This project is licensed under the [GNU GPLv3](./LICENSE.md).