import time
from uuid import uuid4

import jwt
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import sessionmaker
from sqlalchemy_utils import create_database, database_exists, drop_database

from crud.user_crud import UserCRUD
from db.session import get_db_session, Base
from main import app
from models import User
from service.nhs_login_service import NHSLoginService
from utils.base_config import config as settings


def get_test_database_url():
    db_host = settings.db_host
    db_port = settings.db_port
    db_user = settings.db_user
    db_password = settings.db_pass

    database_url = f"postgresql+psycopg://{db_user}:{db_password}@{db_host}:{db_port}/test-db"

    if not database_exists(database_url):
        create_database(database_url)

    return database_url


engine = create_engine(
    get_test_database_url(),
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

user_uuid_pk = uuid4()


@pytest.fixture(scope="session")
def db_engine():
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    drop_database(get_test_database_url())


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
        identity_level="1",
        date_of_birth="1990-01-01"
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


@pytest.fixture(scope="function")
def authenticated_user(db_session):

    user = db_session.query(User).filter(User.id == user_uuid_pk).first()

    payload = {"user_id": str(user.id), "exp": time.time() + TOKEN_EXPIRY_5_MINUTES_AS_SEC}
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    user.current_token = token
    db_session.commit()

    return user


@pytest.fixture(scope="function")
def unauthenticated_user(db_session):

    user = db_session.query(User).filter(User.id == user_uuid_pk).first()

    payload = {"user_id": str(uuid4()), "exp": time.time() + TOKEN_EXPIRY_5_MINUTES_AS_SEC}
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    user.current_token = token
    db_session.commit()

    return user
