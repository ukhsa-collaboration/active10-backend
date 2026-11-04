from pydantic import ValidationError
from redis import Redis

from schemas.user import SessionUser
from utils.base_config import config, logger

SESSION_KEY_PREFIX = "active10"


def session_key(sid: str) -> str:
    return f"{SESSION_KEY_PREFIX}:{sid}"


def user_sessions_key(keycloak_sub: str) -> str:
    return f"{SESSION_KEY_PREFIX}:user:{keycloak_sub}"


def save_session(redis: Redis, sid: str, session: SessionUser) -> None:
    """Stores an active session and indexes it against the Keycloak subject."""
    ttl = config.session_ttl_seconds
    index_key = user_sessions_key(session.keycloak_sub)

    with redis.pipeline() as pipe:
        pipe.set(session_key(sid), session.model_dump_json(), ex=ttl)
        pipe.sadd(index_key, sid)
        pipe.expire(index_key, ttl)
        pipe.execute()


def get_session(redis: Redis, sid: str) -> SessionUser | None:
    """Returns the active session for a session id, or None when it has gone."""
    stored = redis.get(session_key(sid))
    if not stored:
        return None

    try:
        return SessionUser.model_validate_json(stored)
    except ValidationError as e:
        logger.warning(f"Discarding malformed session entry for sid {sid}: {e}")
        redis.delete(session_key(sid))
        return None


def delete_session(redis: Redis, sid: str) -> SessionUser | None:
    """Removes a session and its index entry, returning whatever it removed."""
    session = get_session(redis, sid)

    with redis.pipeline() as pipe:
        pipe.delete(session_key(sid))
        if session:
            pipe.srem(user_sessions_key(session.keycloak_sub), sid)
        pipe.execute()

    return session


def delete_user_sessions(redis: Redis, keycloak_sub: str) -> int:
    """Removes every session held for a Keycloak subject and returns how many there were."""
    index_key = user_sessions_key(keycloak_sub)
    sids = redis.smembers(index_key)

    with redis.pipeline() as pipe:
        for sid in sids:
            pipe.delete(session_key(sid))
        pipe.delete(index_key)
        pipe.execute()

    return len(sids)


def get_user_session_ids(redis: Redis, keycloak_sub: str) -> set[str]:
    """
    Returns the live session ids for a Keycloak subject. Index members whose session has
    already expired are pruned, since only the session keys carry a TTL.
    """
    index_key = user_sessions_key(keycloak_sub)
    sids = list(redis.smembers(index_key))
    if not sids:
        return set()

    with redis.pipeline() as pipe:
        for sid in sids:
            pipe.exists(session_key(sid))
        found = pipe.execute()

    live = {sid for sid, exists in zip(sids, found, strict=True) if exists}
    stale = set(sids) - live
    if stale:
        redis.srem(index_key, *stale)

    return live
