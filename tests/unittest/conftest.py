import time
from contextlib import contextmanager
from typing import ClassVar
from uuid import uuid4

import jwt
import pytest
from alembic import command
from alembic.config import Config
from docker.errors import DockerException
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import NullPool, create_engine
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

try:
    postgres = PostgresContainer("postgres:16")
    postgres.start()
except DockerException as exc:  # pragma: no cover - only exercised when docker unavailable
    pytest.skip(
        f"Docker not available for Postgres test container: {exc}",
        allow_module_level=True,
    )

engine = create_engine(postgres.get_connection_url(), poolclass=NullPool)
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
    transaction.rollback()
    session.close()
    connection.close()


class MockNHSLoginService(NHSLoginService):
    state_store: ClassVar[dict[str, dict]] = {}
    code_store: ClassVar[dict[str, dict]] = {}

    def __init__(self):
        self.userCRUD = UserCRUD()
        self.token_crud = None
        self.redis_service = None
        self.pds_client = None

    def start_authorization(  # noqa: PLR0913
        self,
        response_type: str,
        client_id: str,
        redirect_uri: str,
        code_challenge: str,
        code_challenge_method: str,
        client_state: str | None,
        scope: str | None,
    ) -> str:
        state = "mock_state"
        self.__class__.state_store[state] = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "code_challenge": code_challenge,
            "code_challenge_method": code_challenge_method,
            "client_state": client_state,
            "scope": scope,
        }
        return f"https://auth.aos.signin.nhs.uk/authorize?state={state}"

    def process_callback(self, req_args: dict) -> str:
        state = req_args.get("state")
        if not state:
            raise HTTPException(status_code=400, detail="Missing state")

        state_data = self.__class__.state_store.get(state)
        if not state_data:
            raise HTTPException(status_code=400, detail="Invalid or expired state")

        if req_args.get("error"):
            return (
                f"{state_data['redirect_uri']}?error={req_args.get('error')}"
                f"&state={state_data.get('client_state')}"
            )

        code = "mock_code"
        self.__class__.code_store[code] = {
            "user_id": str(user_uuid_pk),
            "code_challenge": state_data["code_challenge"],
            "code_challenge_method": state_data["code_challenge_method"],
            "client_id": state_data["client_id"],
            "redirect_uri": state_data["redirect_uri"],
        }
        return f"{state_data['redirect_uri']}?code={code}&state={state_data.get('client_state')}"

    def exchange_code_for_token(
        self,
        code: str,
        code_verifier: str,
        client_id: str | None,
        redirect_uri: str | None,
    ) -> dict:
        if code not in self.__class__.code_store:
            raise HTTPException(status_code=400, detail="Invalid or expired code")

        return {
            "access_token": "mock_jwt",
            "token_type": "Bearer",
            "expires_in": 300,
            "user": {"id": str(user_uuid_pk), "email": "default@example.com"},
        }


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
