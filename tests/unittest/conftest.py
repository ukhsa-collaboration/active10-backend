import time
from contextlib import contextmanager
from uuid import uuid4

import jwt
import pytest
from alembic import command
from alembic.config import Config
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import sessionmaker
from sqlalchemy_utils import drop_database
from testcontainers.postgres import PostgresContainer

from crud.user_crud import UserCRUD
from db.session import get_db_session, Base
from main import app
from models import User, UserToken
from service.nhs_login_service import NHSLoginService
from utils.base_config import config as settings


@pytest.fixture(scope="session", autouse=True)
def set_test_setttings():
    """
    Set config to avoid needing an .env file whilst unit testing.
    """
    settings.nhs_login_authority_url = "foo"
    settings.nhs_login_client_id = "foo"
    settings.nhs_login_callback_url = "foo"
    settings.nhs_login_scopes = "foo"
    settings.nhs_api_url = "foo"
    settings.nhs_api_key = "foo"
    settings.auth_jwt_secret = "foo"
    settings.nhs_pds_jwt_private_key = "foo"
    settings.db_host = "foo"
    settings.db_port = "foo"
    settings.db_user = "foo"
    settings.db_pass = "foo"
    settings.db_name = "foo"
    settings.app_uri = "foo"
    settings.gojauntly_key_id = "foo"
    settings.gojauntly_private_key = "foo"
    settings.gojauntly_issuer_id = "foo"
    settings.aws_sqs_queue_url = "foo"
    settings.aws_sqs_activities_migrations_queue_url = "foo"
    settings.aws_sns_activity_topic_arn = "foo"
    settings.aws_sns_activities_migration_topic_arn = "foo"
    settings.sendgrid_webhook_public_key = "foo"
    settings.test_nhs_login_api = "foo"
    settings.test_nhs_email = "foo"
    settings.test_nhs_password = "foo"
    settings.test_nhs_otp = "foo"


user_uuid_pk = uuid4()

postgres = PostgresContainer("postgres:16")
postgres.start()
engine = create_engine(postgres.get_connection_url(), poolclass=StaticPool)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


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
    drop_database(database_url)


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
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db
    app.dependency_overrides[NHSLoginService] = MockNHSLoginService

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
