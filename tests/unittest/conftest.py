import time
from contextlib import contextmanager
from uuid import uuid4

import jwt
import pytest
from alembic import command
from alembic.config import Config
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import StaticPool, create_engine
from sqlalchemy.orm import sessionmaker
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer

from crud.user_crud import UserCRUD
from db.session import Base, get_db_session
from main import app
from models import User, UserToken
from service.nhs_login_service import NHSLoginService
from service.redis_service import RedisService, get_redis_service
from utils.base_config import config as settings

user_uuid_pk = uuid4()

postgres = PostgresContainer("postgres:16")
postgres.start()
engine = create_engine(postgres.get_connection_url(), poolclass=StaticPool)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Start a Redis container for tests
redis_container = RedisContainer("redis:7-alpine")
redis_container.start()


@pytest.fixture(scope="session")
def db_engine():
    database_url = postgres.get_connection_url()

    alembic_cfg = Config()
    alembic_cfg.set_main_option("sqlalchemy.url", database_url)
    alembic_cfg.set_main_option("script_location", "db/migrations")

    with engine.begin() as connection:
        alembic_cfg.attributes["connection"] = connection
        command.upgrade(alembic_cfg, "head")

    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    postgres.stop()


@pytest.fixture(scope="session", autouse=True)
def redis_engine():
    """
    Initialize Redis client settings to point at the testcontainer Redis.

    This overrides runtime settings so RedisService connects to the container.
    """
    host = redis_container.get_container_host_ip()
    port = redis_container.get_exposed_port(6379)

    # Point config at test Redis
    settings.redis_host = host
    settings.redis_port = int(port)
    settings.redis_db = 0
    settings.redis_password = ""

    # Initialize Redis client
    RedisService._pool = None
    RedisService._client = None
    RedisService.initialize_pool()

    yield RedisService

    # Teardown Redis client
    redis_client = RedisService.get_client()
    if redis_client:
        redis_client.flushdb()

    RedisService._pool = None
    RedisService._client = None
    redis_container.stop()


@pytest.fixture(scope="module")
def db_session(db_engine):
    connection = db_engine.connect()
    transaction = connection.begin()
    session = TestSessionLocal(bind=connection)

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
        date_of_birth="1990-01-01",
    )
    if not session.query(User).filter_by(id=user_uuid_pk).first():
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
def client(db_session, redis_engine):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db
    app.dependency_overrides[NHSLoginService] = MockNHSLoginService
    app.dependency_overrides[get_redis_service] = lambda: RedisService()

    with TestClient(app) as client:
        yield client


JWT_ALGORITHM = "HS256"
JWT_SECRET = settings.auth_jwt_secret
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
