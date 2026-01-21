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
   make docker-up
   ```

3. **Access the application:**
   - API: `https://active10.localhost`
   - API Documentation: `https://active10.localhost/docs`

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
