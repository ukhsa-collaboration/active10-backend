# Active10 Backend Service

## Description

   Backend service for Active10 applications

## Getting Started

### Prerequisites

- Python 3.10+
- pip (Python package installer)

### Installation

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
   SECRET=
   APP_URI=
   DB_HOST=
   DB_PORT=
   DB_USER=
   DB_PASS=
   DB_NAME=
   DB_ROOT_PASS=
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
2. **Run the tests:**
    ```bash
    pytest
    ```

### Contributing
Please read the [CONTRIBUTING.md](./CONTRIBUTING.md) for details on our code of conduct, and the process for submitting pull requests to us.


### License
This project is licensed under the [MIT License](./LICENSE.md). See the LICENSE file for details.