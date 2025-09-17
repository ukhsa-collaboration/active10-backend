import hashlib
import pickle
from typing import Any

import redis

from utils.base_config import config, logger


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
                cls._client = redis.Redis(connection_pool=cls._pool)
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
    def set(cls, key: str, value: Any, ttl: int | None = None) -> bool:
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
    def delete_pattern(cls, pattern: str) -> int:
        """
        Delete all keys matching the given pattern.

        Args:
            pattern (str): The Redis key pattern (e.g. 'user:*').

        Returns:
            int: Number of keys deleted.
        """
        if not cls.is_available():
            return 0
        try:
            keys = cls._client.keys(pattern)
            if keys:
                return cls._client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Error deleting keys with pattern {pattern}: {e}")
            return 0

    @classmethod
    def set_user_cache(cls, user_id: str, user_data: Any, ttl: int = 3600) -> bool:
        """
        Cache user data with a standardized cache key.

        Args:
            user_id (str): The user identifier.
            user_data (Any): The data to cache.
            ttl (int): Time-to-live in seconds (default 3600).

        Returns:
            bool: True if cached successfully, False otherwise.
        """
        key = f"user:{user_id}"
        return cls.set(key, user_data, ttl)

    @classmethod
    def get_user_cache(cls, user_id: str) -> Any | None:
        """
        Retrieve cached user data by user ID.

        Args:
            user_id (str): The user identifier.

        Returns:
            Any: Cached user data or None if not found.
        """
        key = f"user:{user_id}"
        return cls.get(key)

    @classmethod
    def delete_user_cache(cls, user_id: str) -> bool:
        """
        Delete cached user data for the given user ID.

        Args:
            user_id (str): The user identifier.

        Returns:
            bool: True if deleted successfully, False otherwise.
        """
        key = f"user:{user_id}"
        return cls.delete(key)

    @classmethod
    def set_token_cache(cls, token_hash: str, user_id: str, ttl: int = 3600) -> bool:
        """
        Cache token validation info using a composite key.

        Args:
            token_hash (str): The hashed token.
            user_id (str): The user identifier.
            ttl (int): Time-to-live in seconds (default 3600).

        Returns:
            bool: True if cached successfully, False otherwise.
        """
        key = f"token:{user_id}:{token_hash}"
        return cls.set(key, user_id, ttl)

    @classmethod
    def get_token_cache(cls, token_hash: str, user_id: str) -> str | None:
        """
        Retrieve cached token validation info.

        Args:
            token_hash (str): The hashed token.
            user_id (str): The user identifier.

        Returns:
            str: User ID if token valid, None if not found.
        """
        key = f"token:{user_id}:{token_hash}"
        return cls.get(key)

    @classmethod
    def delete_token_cache(cls, token_hash: str, user_id: str) -> bool:
        """
        Delete cached token validation info.

        Args:
            token_hash (str): The hashed token.
            user_id (str): The user identifier.

        Returns:
            bool: True if deleted successfully, False otherwise.
        """
        key = f"token:{user_id}:{token_hash}"
        return cls.delete(key)

    @classmethod
    def invalidate_user_session(cls, user_id: str) -> bool:
        """
        Invalidate all cached data for a user, including tokens.

        Args:
            user_id (str): The user identifier.

        Returns:
            bool: True if invalidation succeeded, False otherwise.
        """
        try:
            user_deleted = cls.delete_user_cache(user_id)
            tokens_deleted = cls.delete_pattern(f"token:{user_id}:*")
            logger.info(
                f"Invalidated session for user {user_id}:"
                f"user_cache={user_deleted}, tokens_cleared={tokens_deleted}"
            )
            return True
        except Exception as e:
            logger.error(f"Error invalidating user session {user_id}: {e}")
            return False


def get_redis_service() -> RedisService:
    """
    FastAPI dependency function to provide the RedisService singleton.

    Returns:
        RedisService: The RedisService class for Redis operations.
    """
    return RedisService()
