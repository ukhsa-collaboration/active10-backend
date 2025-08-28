# Active10 - User Management Microservice

## Description

User Management microservice for the Active10 application. This service provides user management, and NHS
Login integration for the Active10 app. Built with FastAPI, PostgreSQL, and Alembic for migrations.

## Features

- NHS Login authentication and callback flow
- User profile and email preferences management
- Integration with NHS Personal Demographics Service (PDS)
- RESTful API endpoints for user and authentication operations
- Health check endpoint
- Dockerized deployment and local development support
- Alembic migrations for database schema

## API Endpoints

### Root & Health

- `GET /` — Welcome message
- `GET /health` — Health check

### NHS Login

- `GET /nhs_login/{app_name}/{app_internal_id}` — Redirect to NHS Login
- `GET /nhs_login/callback` — NHS Login callback handler
- `POST /nhs_login/logout` — Logout user
- `POST /nhs_login/disconnect` — Disconnect user

### User (v1)

- `GET /v1/users` — Get user profile
- `POST /v1/users/email_preferences/subscribe` — Subscribe to email preferences
- `POST /v1/users/email_preferences/unsubscribe` — Unsubscribe from email preferences

## Authentication & NHS Integration

- NHS Login flow is handled via `/nhs_login` endpoints
- Request header "Bh-User-Id" is used for user authentication
- NHS PDS integration for user demographic data

## Database

- PostgreSQL
- Alembic for migrations

## Testing

- Unit tests: `tests/unittest/`
- Integration tests: `tests/integration/`
- Test dependencies and fixtures provided
- Example test command:
  ```bash
  pytest --headless --wire
  ```

## Scripts

- `scripts/start-backend.sh`: Runs Alembic migrations and starts the FastAPI server

## Configuration

- Environment variables are required (see `.env.example`)
- SSL certificates for HTTPS in `cert/`

---

## Getting Started

### Prerequisites

- Python 3.10+
- pip (Python package installer)
- Docker (optional for Docker setup)

### Installation

You can run the project in two ways:

- [Using Docker](#running-with-docker)
- [Using Uvicorn](#running-with-uvicorn)

---

## Running with Docker

If you'd prefer to run the project using Docker, follow these steps:

### Steps

1. **Set the environment variables:**

   Create a `.env` file in the root directory and add the following variables:
   <pre>
   AUTH_JWT_SECRET=HS256
   AUTH_JWT_EXPIRY_IN_SECONDS=3600

   # PostgreSQL Database Configuration
   DB_HOST=host
   DB_PORT=5432
   DB_USER=postgres
   DB_PASS=password
   DB_NAME=db-name


   # NHS Integration
   NHS_LOGIN_AUTHORITY_URL=https://
   NHS_LOGIN_CLIENT_ID=app-id
   NHS_LOGIN_SCOPES="openid profile profile_extended email basic_demographics"
   NHS_LOGIN_CALLBACK_URL=https://domain/app/callback
   NHS_API_URL=https://
   NHS_API_KEY=api-key
   APP_URI=app_url://

   NHS_PDS_JWT_PRIVATE_KEY="private-key"

   # Integration Testing
   TEST_NHS_LOGIN_API="https://0.0.0.0:8000/nhs_login/active10/12345"
   TEST_NHS_EMAIL="example@dev.com"
   TEST_NHS_PASSWORD="pass"
   TEST_NHS_OTP="otp"
    </pre>

2. **Run the application** using Docker Compose:

   ```bash
   docker compose -f docker-compose-dev.yml up --build
   ```

3. **Access the application:**

   The app will be available at `http://localhost:8000`. If you're using HTTPS, it will be accessible at
   `https://localhost:8000`.

### Docker Details

The `docker-compose.yaml` file defines two services:

- **app**: The FastAPI backend service.
- **db**: A PostgreSQL 13 database service.

The `app` service depends on the PostgreSQL database and runs using environment variables specified in the `.env` file.
The app is accessible via port 8000, and the database is available on port 5432.

---

## Running with Uvicorn

### Steps

1. **Create and activate a virtual environment:**

   ```bash
   python3 -m venv venv
   ```

   ```bash
   source venv/bin/activate
   ```

   On Windows use

   ```bash
   venv\Scripts\activate
   ```

2. **Install the dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
3. **Set the environment variables:**

   Create a `.env` file in the root directory and add the following variables:
   <pre>
   AUTH_JWT_SECRET=HS256
   AUTH_JWT_EXPIRY_IN_SECONDS=3600

   # PostgreSQL Database Configuration
   DB_HOST=host
   DB_PORT=5432
   DB_USER=postgres
   DB_PASS=password
   DB_NAME=db-name


   # NHS Integration
   NHS_LOGIN_AUTHORITY_URL=https://
   NHS_LOGIN_CLIENT_ID=app-id
   NHS_LOGIN_SCOPES="openid profile profile_extended email basic_demographics"
   NHS_LOGIN_CALLBACK_URL=https://domain/app/callback
   NHS_API_URL=https://
   NHS_API_KEY=api-key
   APP_URI=app_url://

   NHS_PDS_JWT_PRIVATE_KEY="private-key"

   # Integration Testing
   TEST_NHS_LOGIN_API="https://0.0.0.0:8000/nhs_login/active10/12345"
   TEST_NHS_EMAIL="example@dev.com"
   TEST_NHS_PASSWORD="pass"
   TEST_NHS_OTP="otp"
    </pre>

4. **Run the database migrations:**

   ```bash
   alembic upgrade head
   ```

5. **Start the FastAPI application:**
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --ssl-certfile cert/cert.pem --ssl-keyfile cert/key.pem
   ```
   The above is applicable only when running in a local development environment.
6. **Access the application:**

   Open your browser and navigate to https://localhost:8000.

### Running Tests

1. **Install test dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
2. **Start the FastAPI application:**
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --ssl-certfile cert/cert.pem --ssl-keyfile cert/key.pem
   ```
3. **Run the tests:**
   ```bash
   pytest --headless --wire
   ```