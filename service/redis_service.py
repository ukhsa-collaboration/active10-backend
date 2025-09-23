import hashlib
import pickle
from typing import Any

import redis

from utils.base_config import config, logger

DEFAULT_AUTH_TTL: int = 2592000  # 30 days in seconds


class RedisService:
    """
    RedisService handles Redis connection pooling and provides convenient methods
    to interact with Redis for caching and session management.

    This class uses a singleton connection pool and shared Redis client to ensure
    efficient reuse of connections across the application.
    """

    _pool = None
    _client = None

    @classmethod
    def initialize_pool(cls):
        """
        Initialize the Redis connection pool and client if not already done.

        Creates a single connection pool shared among all RedisService users.
        Logs success or error during initialization.
        """
        if cls._pool is None:
            try:
                cls._pool = redis.ConnectionPool(
                    host=config.redis_host,
                    port=config.redis_port,
                    db=config.redis_db,
                    password=config.redis_password if config.redis_password else None,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    retry_on_timeout=True,
                    decode_responses=False,
                )
                cls._client = redis.Redis(connection_pool=cls._pool, ssl=True)
                cls._client.ping()
                logger.info("Redis connection pool and client created successfully")
            except Exception as e:
                logger.error(f"Failed to create Redis connection pool: {e}")
                cls._pool = None
                cls._client = None

    @classmethod
    def get_client(cls) -> redis.Redis | None:
        """
        Retrieve the Redis client instance from the shared connection pool.

        Lazily initializes the pool and client on first call.

        Returns:
            Redis client instance if available, else None.
        """
        if cls._client is None:
            cls.initialize_pool()
        return cls._client

    @staticmethod
    def hash_token(token: str) -> str:
        """
        Generate a SHA-256 hash of the given token string.

        Args:
            token (str): The token string to hash.

        Returns:
            str: The hexadecimal hash digest of the token.
        """
        return hashlib.sha256(token.encode()).hexdigest()

    @classmethod
    def is_available(cls) -> bool:
        """
        Check if the Redis client is connected and available.

        Returns:
            bool: True if Redis client responds to ping, False otherwise.
        """
        client = cls.get_client()
        if not client:
            return False
        try:
            client.ping()
            return True
        except Exception:
            return False

    @classmethod
    def set(cls, key: str, value: Any, ttl: int | None = DEFAULT_AUTH_TTL) -> bool:
        """
        Set a key-value pair in Redis with optional expiration time (TTL).

        Serializes the value using pickle before storing.

        Args:
            key (str): The Redis key to set.
            value (Any): The Python object to serialize and store.
            ttl (int, optional): Time-to-live in seconds. If None, no expiry.

        Returns:
            bool: True if operation succeeded, False on failure.
        """
        if not cls.is_available():
            return False
        try:
            serialized_value = pickle.dumps(value)
            if ttl:
                return cls._client.setex(key, ttl, serialized_value)
            else:
                return cls._client.set(key, serialized_value)
        except Exception as e:
            logger.error(f"Error setting Redis key {key}: {e}")
            return False

    @classmethod
    def get(cls, key: str) -> Any | None:
        """
        Retrieve and deserialize a value stored by key from Redis.

        Args:
            key (str): The Redis key to fetch.

        Returns:
            Any: The deserialized value, or None if key does not exist or on error.
        """
        if not cls.is_available():
            return None
        try:
            serialized_value = cls._client.get(key)
            if serialized_value is None:
                return None
            return pickle.loads(serialized_value)
        except Exception as e:
            logger.error(f"Error getting Redis key {key}: {e}")
            return None

    @classmethod
    def delete(cls, key: str) -> bool:
        """
        Delete a key from Redis.

        Args:
            key (str): The Redis key to delete.

        Returns:
            bool: True if key was deleted, False otherwise or on error.
        """
        if not cls.is_available():
            return False
        try:
            return bool(cls._client.delete(key))
        except Exception as e:
            logger.error(f"Error deleting Redis key {key}: {e}")
            return False

    @classmethod
    def set_auth_cache(cls, token_hash: str, user_id: str, ttl: int = DEFAULT_AUTH_TTL) -> bool:
        """
        Store authentication data in the cache using a hashed token as the key.

        Args:
            token_hash (str): The hashed authentication token.
            user_id (str): The identifier of the user associated with the token.
            ttl (int, optional): Time-to-live in seconds for the cache entry.
                Defaults to DEFAULT_AUTH_TTL.

        Returns:
            bool: True if the data was successfully cached, False otherwise.
        """
        key = f"{token_hash}"
        cache_data = {"user_id": user_id}
        return cls.set(key, cache_data, ttl)

    @classmethod
    def get_auth_cache(cls, token_hash: str) -> Any | None:
        """
        Retrieve authentication data from the cache.

        Args:
            token_hash (str): The hashed authentication token.

        Returns:
            Any: Cached user data if found, otherwise None.
        """
        key = f"{token_hash}"
        return cls.get(key)

    @classmethod
    def delete_auth_cache(cls, token_hash: str, user_id: str | None) -> bool:
        """
        Remove authentication data from the cache.

        Args:
            token_hash (str): The hashed authentication token.
            user_id (str, optional): The identifier of the user associated
                with the token. Defaults to None.

        Returns:
            bool: True if the cache entry was deleted successfully, False otherwise.

        Raises:
            Exception: If an error occurs while attempting to delete the cache entry.
        """
        try:
            key = f"{token_hash}"
            deleted_cache = cls.delete(key)
            logger.info(f"Deleted Cache for user {user_id}: token_cache={deleted_cache}")
            return True
        except Exception as e:
            logger.error(f"Error deleting user session {user_id}: {e}")
            raise


def get_redis_service() -> RedisService:
    """
    FastAPI dependency function to provide the RedisService singleton.

    Returns:
        RedisService: The RedisService class for Redis operations.
    """
    return RedisService()
