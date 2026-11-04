import json
import os
import time
from pathlib import Path
from uuid import uuid4

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from dotenv import load_dotenv

# Prepare the environment before the app is imported, so plain pytest works without the Makefile.
# Keycloak values live here, not in tests.env, because tests.env ships in the image.
load_dotenv(Path(__file__).resolve().parents[1] / "tests.env", override=False)
os.environ.setdefault("KEYCLOAK_REALM_URL", "http://keycloak.test/realms/active10")
os.environ.setdefault("KEYCLOAK_CLIENT_ID", "active10-api")
os.environ.setdefault("KEYCLOAK_APP_CLIENT_ID", "active10-app")
os.environ.setdefault("SESSION_TTL_MINUTES", "60")
if "PRIVATE KEY" not in os.environ.get("GOJAUNTLY_PRIVATE_KEY", ""):
    os.environ["GOJAUNTLY_PRIVATE_KEY"] = (
        ec.generate_private_key(ec.SECP256R1())
        .private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption(),
        )
        .decode()
    )

import fakeredis  # noqa: E402
import jwt  # noqa: E402
import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from cryptography.hazmat.primitives.asymmetric import rsa  # noqa: E402
from docker.errors import DockerException  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from jwt.algorithms import RSAAlgorithm  # noqa: E402
from sqlalchemy import NullPool, create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from testcontainers.postgres import PostgresContainer  # noqa: E402

from auth.v3.keycloak import JWKS_CACHE_KEY  # noqa: E402
from auth.v3.session_store import save_session  # noqa: E402
from crud.user_crud import UserCRUD  # noqa: E402
from db.redis_client import get_redis  # noqa: E402
from db.session import Base, get_db_session  # noqa: E402
from main import app  # noqa: E402
from models import User  # noqa: E402
from schemas.user import SessionUser  # noqa: E402
from utils.base_config import config  # noqa: E402

user_uuid_pk = uuid4()

fake_redis = fakeredis.FakeRedis(decode_responses=True)

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


@pytest.fixture(scope="session")
def db_engine():
    alembic_cfg = Config()
    alembic_cfg.set_main_option("sqlalchemy.url", postgres.get_connection_url())
    alembic_cfg.set_main_option("script_location", "db/migrations")

    with engine.begin() as connection:
        alembic_cfg.attributes["connection"] = connection
        command.upgrade(alembic_cfg, "head")

    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    postgres.stop()


@pytest.fixture(scope="module")
def db_session(db_engine):
    connection = db_engine.connect()
    transaction = connection.begin()
    session = TestSessionLocal(bind=connection)

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
        _ = UserCRUD(session).create_user(default_user)

    yield session
    if transaction.is_active:
        transaction.rollback()
    session.close()
    connection.close()


@pytest.fixture(scope="module")
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db
    app.dependency_overrides[get_redis] = lambda: fake_redis

    with TestClient(app) as client:
        yield client


KEYCLOAK_KID = "test-signing-key"
keycloak_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
keycloak_public_jwk = json.loads(RSAAlgorithm.to_jwk(keycloak_private_key.public_key()))
keycloak_public_jwk.update({"kid": KEYCLOAK_KID, "use": "sig", "alg": "RS256"})


def create_access_token(keycloak_sub: str, sid: str, **overrides) -> str:
    """
    Mints a Keycloak shaped access token signed by the test key. The key is published to the
    fake JWKS cache on every call, since some modules flush Redis between tests.
    """
    fake_redis.set(JWKS_CACHE_KEY, json.dumps({"keys": [keycloak_public_jwk]}))
    now = int(time.time())
    claims = {
        "sub": keycloak_sub,
        "sid": sid,
        "iss": config.keycloak_issuer,
        "aud": config.keycloak_expected_audience,
        "iat": now,
        "exp": now + 300,
        "scope": "openid profile email",
        "email": "default@example.com",
    }
    claims.update(overrides)
    return jwt.encode(
        claims, keycloak_private_key, algorithm="RS256", headers={"kid": KEYCLOAK_KID}
    )


def sign_in(db_session, with_session: bool) -> User:
    """
    Gives the default user a Keycloak identity and an access token for a new sign-in, exposed
    as user.access_token and user.session_id, with a saved session only when asked.
    """
    user = db_session.get(User, user_uuid_pk)
    if not user.keycloak_sub:
        user.keycloak_sub = str(uuid4())
        db_session.commit()

    sid = str(uuid4())
    if with_session:
        session = SessionUser(
            user_id=user.id, keycloak_sub=user.keycloak_sub, user_email=user.email
        )
        save_session(fake_redis, sid, session)
    user.session_id = sid
    user.access_token = create_access_token(user.keycloak_sub, sid)
    return user


@pytest.fixture
def authenticated_user(db_session):
    return sign_in(db_session, with_session=True)


@pytest.fixture
def unauthenticated_user(db_session):
    """A valid token whose sign-in has no backend session, so v3 answers SESSION_NOT_FOUND."""
    return sign_in(db_session, with_session=False)
