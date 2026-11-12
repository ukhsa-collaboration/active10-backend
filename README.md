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

- Python 3.10+
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

## Keycloak Configuration

The `/v3` API signs users in through Keycloak and keeps their sessions in Redis, using the existing `REDIS_*` settings. It stays disabled, answering 503, until all four of these are set:

- `KEYCLOAK_REALM_URL`: the realm URL, for example `https://<host>/realms/<realm>`
- `KEYCLOAK_CLIENT_ID`: the Active10 API client, expected in the token audience
- `KEYCLOAK_APP_CLIENT_ID`: the app client, used to revoke refresh tokens
- `SESSION_TTL_MINUTES`: how long a v3 session lasts

Optional, with defaults: `KEYCLOAK_AUDIENCE` (the API client id), `KEYCLOAK_ALGORITHMS` (`RS256`), `KEYCLOAK_REQUIRED_CLAIMS` (`scope,email,sid`), `KEYCLOAK_JWKS_CACHE_MINUTES` (10), `KEYCLOAK_LEEWAY_SECONDS` (10) and `KEYCLOAK_HTTP_TIMEOUT_SECONDS` (30). `/v1` and NHS Login do not use any of these.

## OpenTelemetry Tracing (AWS X-Ray)

The app traces the NHS Login flow with OpenTelemetry and ships spans over OTLP to an ADOT collector, which forwards them on to AWS X-Ray. The collector runs as its own service, `adot-collector`, in `docker-compose.yml`, so it starts automatically with the rest of the stack.

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

Run the NHS Login flow, or any authenticated request, to generate a trace, then open X-Ray traces in CloudWatch and look for the `active10-auth` service. To filter by auth step use `annotation.auth_step = "nhs-login-token-exchange"`. X-Ray annotation keys can't contain dots, so the `auth.step` attribute on the span becomes `auth_step` once it's indexed.

If no traces show up, check that the collector container is running and on the `proxy` network, and that the region and IAM permissions are right. The export errors logged while running `make unit-tests` are expected, there's no collector in that environment and the tests don't need one.

## Testing

### Run Test Suite

Install `requirements-dev.txt` alongside `requirements.txt` first.

```bash
# Run all unit tests
make unit-tests

# Run the Keycloak (v3) unit tests
make unit-tests-v3
```

### Test Configuration

Tests are configured in `pyproject.toml` with coverage reporting for:

- API endpoints (`api/`)
- Business logic (`service/`)
- Database operations (`crud/`)
- Models (`models/`)
- Authentication (`auth/`)
- NHS integrations (`nhs/`)

## Error Responses

Errors from the `/v3` API return a code alongside the message. Branch on the code, not the message, which is written for people and may be reworded. `/v1`, `/v2` and `/nhs_login` keep their existing error responses.

```json
{
  "detail": "Session not found",
  "error": { "code": "SESSION_NOT_FOUND", "message": "Session not found" }
}
```

Codes, each defined in `ErrorCode` in `utils/custom_exceptions.py`:

- `NOT_AUTHENTICATED` (401): the request carried no bearer token, or a malformed Authorization header. Sign in again.
- `TOKEN_EXPIRED` (401): the access token is past its expiry. Refresh it with the refresh token and retry.
- `TOKEN_INVALID` (401): the token failed verification, or the session behind it belongs to someone else. Sign in again.
- `SESSION_NOT_FOUND` (401): the token is valid but no backend session exists. Call `/v3/users/sync` and retry.
- `SERVICE_UNAVAILABLE` (503): a dependency is unreachable, or the Keycloak settings are not configured. The request can be retried.
- `ACCOUNT_CONFLICT` (409): more than one account matches the user's NHS number, or the account could not be linked. Nothing was changed, so the user should contact support.
- `NHS_NUMBER_MISSING` (422): the identity provider returned no NHS number. Nothing was changed, and signing in again will not help, so the user should contact support.
- `UPSTREAM_PROFILE_INCOMPLETE` (502): the identity provider returned a profile missing required fields.
- `REFRESH_TOKEN_INVALID` (400): logout or disconnect was sent a refresh token that Keycloak rejects (usually the previous one) or that belongs to a different sign-in than the access token. Nothing was changed, so retry with the refresh token from the same sign-in.
- `INTERNAL_ERROR` (500): an unexpected failure, for example the account could not be deleted. The request can be retried.
- `INVALID_REQUEST` (400): the request was understood but its values are not acceptable, for example unsubscribing from a list the user is not on.
- `NOT_FOUND` (404): the record does not exist, or does not belong to the caller.
- `ALREADY_EXISTS` (400): a record with the same data is already stored.
- `UPSTREAM_ERROR` (502): a third party service, such as GoJauntly, failed. The request can be retried.

Logout and disconnect revoke the refresh token at Keycloak before changing anything else. If either then answers 500 or 503, the refresh token may already be revoked, so sign in again before retrying.

Validation errors (422) come from FastAPI and keep its `detail` format, which lists the offending fields.

## License

This project is licensed under the [GNU GPLv3](./LICENSE.md).
