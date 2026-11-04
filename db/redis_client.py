from collections.abc import Generator

from redis import ConnectionPool, Redis
from redis.connection import Connection, SSLConnection

from utils.base_config import config

# The v3 API's pool. Unlike RedisService, errors propagate so callers can answer 503.
pool = ConnectionPool(
    connection_class=SSLConnection if config.redis_use_ssl else Connection,
    host=config.redis_host,
    port=config.redis_port,
    db=config.redis_db,
    password=config.redis_password or None,
    socket_connect_timeout=5,
    socket_timeout=5,
    decode_responses=True,
)


def get_redis() -> Generator[Redis, None, None]:
    """Dependency that provides a Redis client for the v3 API."""
    with Redis(connection_pool=pool) as client:
        yield client
