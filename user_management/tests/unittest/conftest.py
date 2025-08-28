import time
from contextlib import contextmanager
from uuid import uuid4
from datetime import date

import jwt
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import sessionmaker
from sqlalchemy_utils import drop_database, create_database, database_exists
from testcontainers.postgres import PostgresContainer

from app.cruds.user_crud import UserCRUD
from app.db.session import get_db_session, Base
from app.main import app
from app.models import User, UserToken
from app.services.nhs_login_service import NHSLoginService
from app.core.config import settings

user_uuid_pk = uuid4()

# Start PostgreSQL container
postgres = PostgresContainer("postgres:16")
postgres.start()

# Create engine with proper configuration
engine = create_engine(
    postgres.get_connection_url(),
    poolclass=StaticPool,
    connect_args={"check_same_thread": False}
    if "sqlite" in postgres.get_connection_url()
    else {},
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session")
def db_engine():
    database_url = postgres.get_connection_url()

    # Ensure database exists
    if not database_exists(database_url):
        create_database(database_url)

    # Create all tables using metadata instead of alembic for tests
    Base.metadata.create_all(bind=engine)

    yield engine

    # Cleanup
    try:
        Base.metadata.drop_all(bind=engine)
        if database_exists(database_url):
            drop_database(database_url)
    except Exception:
        pass  # Ignore cleanup errors
    finally:
        postgres.stop()


@pytest.fixture(scope="module")  # Keep module scope to match client fixture
def db_session(db_engine):
    connection = db_engine.connect()
    transaction = connection.begin()
    session = TestSessionLocal(bind=connection)

    # Create default user for tests
    try:
        default_user = User(
            id=user_uuid_pk,
            unique_id="3a8d2869-0b2e-485a-9e67-8a906e6194ce",
            nhs_number="1234567890",
            first_name="Default",
            email="default@example.com",
            gender="male",
            postcode="12345",
            identity_level="1",
            date_of_birth=date(1990, 1, 1),  # Use date object instead of string
        )

        # Check if user already exists
        existing_user = session.query(User).filter_by(id=user_uuid_pk).first()
        if not existing_user:
            session.add(default_user)
            session.commit()
    except Exception as e:
        session.rollback()
        raise e

    yield session

    # Cleanup
    try:
        session.close()
        transaction.rollback()
        connection.close()
    except Exception:
        pass  # Ignore cleanup errors


class MockNHSLoginService(NHSLoginService):
    def __init__(self):
        super().__init__(UserCRUD())

    def process_callback(self, req_args: dict) -> str:
        code = req_args.get("code")
        state = req_args.get("state")

        if not state and not code:
            raise HTTPException(status_code=400, detail="Missing state and code")

        if not code:
            raise HTTPException(status_code=400, detail="Missing code")

        if not state:
            raise HTTPException(status_code=400, detail="Missing state")

        return f"active10dev://nhs_login_callback?code={code}&state={state}"


@pytest.fixture(scope="module")
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db
    app.dependency_overrides[NHSLoginService] = MockNHSLoginService

    with TestClient(app) as client:
        yield client


JWT_ALGORITHM = "HS256"
JWT_SECRET = settings.AUTH_JWT_SECRET
TOKEN_EXPIRY_5_MINUTES_AS_SEC = 300


def create_user_token(user, db_session, is_authenticated=True) -> None:
    if user.token:
        db_session.delete(user.token)
        db_session.commit()

    user_id = str(user.id) if is_authenticated else str(uuid4())
    payload = {"user_id": user_id, "exp": time.time() + TOKEN_EXPIRY_5_MINUTES_AS_SEC}
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

    user_token = UserToken(user_id=user.id, token=token)
    db_session.add(user_token)
    db_session.commit()
    db_session.refresh(user)


@pytest.fixture(scope="function")
def authenticated_user(db_session):
    user = db_session.query(User).filter(User.id == user_uuid_pk).first()
    create_user_token(user, db_session, is_authenticated=True)
    return user


@pytest.fixture(scope="function")
def unauthenticated_user(db_session):
    user = db_session.query(User).filter(User.id == user_uuid_pk).first()
    create_user_token(user, db_session, is_authenticated=False)
    return user


@contextmanager
def override_get_db_context_session(db_session):
    yield db_session
