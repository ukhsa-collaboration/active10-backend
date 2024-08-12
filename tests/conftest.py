from uuid import uuid4

import pytest
import jwt
import time
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import sessionmaker

from crud.user_crud import UserCRUD
from main import app
from db.session import get_db_session, Base
from models import User
from service.nhs_login_service import NHSLoginService
from utils.base_config import config as settings

DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    DATABASE_URL,
    connect_args={
        "check_same_thread": False,
    },
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

user_uuid_pk = uuid4()


@pytest.fixture(scope="module")
def db_engine():
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="module")
def db_session(db_engine):
    connection = db_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    user_crud = UserCRUD(session)
    default_user = User(
        id=user_uuid_pk,
        unique_id="3a8d2869-0b2e-485a-9e67-8a906e6194ce",
        nhs_number="1234567890",
        first_name="Default",
        email="default@example.com",
        gender="male",
        postcode="12345",
        identity_level="1"
    )
    _ = user_crud.create_user(default_user)

    yield session
    session.close()
    transaction.rollback()
    connection.close()


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
JWT_SECRET = settings.secret
TOKEN_EXPIRY_5_MINUTES_AS_SEC = 300


def authenticated_user_token():
    user_id = "3a8d2869-0b2e-485a-9e67-8a906e6194ce"
    payload = {"user_id": user_id, "expires": time.time() + TOKEN_EXPIRY_5_MINUTES_AS_SEC}
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

    return token


def unauthenticated_user_token():
    user_id = "99999999asdfa"
    payload = {"user_id": user_id, "expires": time.time() + TOKEN_EXPIRY_5_MINUTES_AS_SEC}
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

    return token


def expired_user_token():
    user_id = "3a8d2869-0b2e-485a-9e67-8a906e6194ce"
    payload = {"user_id": user_id, "expires": time.time() - TOKEN_EXPIRY_5_MINUTES_AS_SEC}
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

    return token
