# Active10 Backend Service

## Description

   Backend service for Active10 applications

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
   NHS_LOGIN_AUTHORITY_URL=
   NHS_LOGIN_CLIENT_ID=
   NHS_LOGIN_SCOPES=
   NHS_LOGIN_CALLBACK_URL=
   NHS_API_URL=
   NHS_API_KEY=
   AUTH_JWT_SECRET=
   APP_URI=
   DB_HOST=
   DB_PORT=
   DB_USER=
   DB_PASS=
   DB_NAME=
   AWS_SQS_QUEUE_URL=
   AWS_SQS_ACTIVITIES_MIGRATIONS_QUEUE_URL=
   GOJAUNTLY_KEY_ID=
   GOJAUNTLY_PRIVATE_KEY=
   GOJAUNTLY_ISSUER_ID=
   NHS_PDS_JWT_PRIVATE_KEY=
   
   # Local only
   AWS_REGION=
   AWS_ACCESS_KEY_ID=
   AWS_SECRET_ACCESS_KEY=
   # Update the environment variables with your values.
    </pre>
   
2. **Run the application** using Docker Compose:
   
   ```bash
   docker-compose up --build
   ```

3. **Access the application:**

   The app will be available at `http://localhost:8000`. If you're using HTTPS, it will be accessible at `https://localhost:8000`.

### Docker Details

The `docker-compose.yaml` file defines two services:

- **app**: The FastAPI backend service.
- **db**: A PostgreSQL 13 database service.

The `app` service depends on the PostgreSQL database and runs using environment variables specified in the `.env` file. The app is accessible via port 8000, and the database is available on port 5432.

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
   NHS_LOGIN_AUTHORITY_URL=
   NHS_LOGIN_CLIENT_ID=
   NHS_LOGIN_SCOPES=
   NHS_LOGIN_CALLBACK_URL=
   NHS_API_URL=
   NHS_API_KEY=
   AUTH_JWT_SECRET=
   APP_URI=
   DB_HOST=
   DB_PORT=
   DB_USER=
   DB_PASS=
   DB_NAME=
   AWS_SQS_QUEUE_URL=
   AWS_SQS_ACTIVITIES_MIGRATIONS_QUEUE_URL=
   GOJAUNTLY_KEY_ID=
   GOJAUNTLY_PRIVATE_KEY=
   GOJAUNTLY_ISSUER_ID=
   NHS_PDS_JWT_PRIVATE_KEY=
 
   # Local only
   AWS_REGION=
   AWS_ACCESS_KEY_ID=
   AWS_SECRET_ACCESS_KEY=
   # Update the environment variables with your values.
    </pre>

4. **Run the database migrations:**
    ```bash
    alembic upgrade head
    ```

5. **Start the FastAPI application:**
    ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000 --ssl-certfile cert/cert.pem --ssl-keyfile cert/key.pem
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
   uvicorn main:app --host 0.0.0.0 --port 8000 --ssl-certfile cert/cert.pem --ssl-keyfile cert/key.pem
   ```
3. **Run the tests:**
    ```bash
    pytest --wire
    ```

### Contributing
Please read the [CONTRIBUTING.md](./CONTRIBUTING.md) for details on our code of conduct, and the process for submitting pull requests to us.


### License
This project is licensed under the [MIT License](./LICENSE.md). See the LICENSE file for details.