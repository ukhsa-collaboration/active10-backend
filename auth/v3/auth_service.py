from datetime import datetime, timezone
from typing import Any

from fastapi import Depends, status
from pydantic import ValidationError
from redis import Redis, RedisError
from sqlalchemy.exc import IntegrityError

from auth.v3.keycloak import (
    KEYCLOAK_FLOW,
    KeycloakUnavailableError,
    TokenValidationError,
    fetch_userinfo,
    read_refresh_token_sid,
    revoke_refresh_token,
)
from auth.v3.session_store import (
    delete_session,
    delete_user_sessions,
    get_user_session_ids,
    save_session,
)
from crud.v3.user_crud import KeycloakUserCRUD
from db.redis_client import get_redis
from models.user import User, UserDeleteReason, UserStatus, UserToken
from schemas.user import KeycloakUserInfo, SessionUser
from service.open_telemetry_service import auth_step_span
from service.redis_service import RedisService
from utils.base_config import logger
from utils.custom_exceptions import CustomHTTPException, ErrorCode
from utils.masking import mask_nhs_number

STEP_SESSION_WRITE = "keycloak-session-write"

SERVICE_UNAVAILABLE = "Service temporarily unavailable"
INVALID_CREDENTIALS = "Invalid credentials"
INCOMPLETE_PROFILE = "Identity provider returned an incomplete profile"
INVALID_REFRESH_TOKEN = "Invalid refresh token"


def _error(status_code: int, error_code: ErrorCode, message: str) -> CustomHTTPException:
    return CustomHTTPException(
        status_code=status_code, error_code=error_code, error_message=message
    )


class AuthService:
    def __init__(
        self,
        user_crud: KeycloakUserCRUD = Depends(),  # noqa: B008
        redis: Redis = Depends(get_redis),  # noqa: B008
    ) -> None:
        self.user_crud = user_crud
        self.redis = redis

    def sync_user(self, token: str, claims: dict[str, Any]) -> User:
        """
        Links or creates the user behind a Keycloak sign-in and opens a session for its sid.
        Any legacy token the user holds is removed, so the legacy app can no longer be used.
        One device per user: sessions the subject already holds are closed first.
        """
        user_info = self.__get_user_info(token)
        if user_info.sub != claims["sub"]:
            logger.warning("Userinfo subject does not match the access token subject")
            raise _error(status.HTTP_401_UNAUTHORIZED, ErrorCode.TOKEN_INVALID, INVALID_CREDENTIALS)

        try:
            user, previous_sub = self.__link_or_create(user_info)
        except IntegrityError:
            logger.warning("User changed during sync, resolving it again")
            try:
                user, previous_sub = self.__link_or_create(user_info)
            except IntegrityError as e:
                logger.error(
                    f"Unable to link NHS number {mask_nhs_number(user_info.nhs_number)}: "
                    f"{type(e).__name__}"
                )
                raise _error(
                    status.HTTP_409_CONFLICT,
                    ErrorCode.ACCOUNT_CONFLICT,
                    "Account could not be linked",
                ) from e

        self.__open_session(user, user_info.sub, previous_sub, claims["sid"])
        return user

    def logout(self, user: User, sid: str, refresh_token: str) -> None:
        """
        Revokes the refresh token, then closes the session. Status becomes Logout unless
        another session is live. If revoke fails, nothing changes. If closing the session
        fails after a successful revoke, the refresh token is already dead, so a retry needs a
        new sign-in; the session expires on its own.
        """
        self.__ensure_same_session(refresh_token, sid)
        self.__revoke(refresh_token)

        try:
            delete_session(self.redis, sid)
            remaining = get_user_session_ids(self.redis, user.keycloak_sub)
        except RedisError as e:
            logger.error(f"Session removal failed: {e}")
            raise _error(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                ErrorCode.SERVICE_UNAVAILABLE,
                SERVICE_UNAVAILABLE,
            ) from e

        if not remaining:
            self.user_crud.update_status(user, UserStatus.LOGOUT.value)

    def disconnect(self, user: User, sid: str, refresh_token: str) -> None:
        """
        Revokes the refresh token, deletes the account with an audit row, then closes every
        session. If revoke fails, nothing changes. If the delete fails after a successful
        revoke, the account and sessions remain but the refresh token is dead, so a retry needs
        a new sign-in. A session left behind after the delete is dropped on its next use, as
        its user no longer exists.
        """
        self.__ensure_same_session(refresh_token, sid)
        self.__revoke(refresh_token)

        keycloak_sub = user.keycloak_sub
        self.user_crud.delete_user_with_audit(user, UserDeleteReason.DISCONNECTED.value)

        try:
            delete_user_sessions(self.redis, keycloak_sub)
        except RedisError as e:
            logger.error(f"Session removal after account deletion failed: {e}")

    @staticmethod
    def __ensure_same_session(refresh_token: str, sid: str) -> None:
        """
        Rejects a refresh token from another sign-in, so the token revoked is the one behind
        this access token rather than any valid token for the app client.
        """
        try:
            refresh_sid = read_refresh_token_sid(refresh_token)
        except TokenValidationError as e:
            logger.warning(f"Refresh token unreadable: {e}")
            raise _error(
                status.HTTP_400_BAD_REQUEST, ErrorCode.REFRESH_TOKEN_INVALID, INVALID_REFRESH_TOKEN
            ) from e

        if refresh_sid != sid:
            logger.warning("Refresh token belongs to a different session than the access token")
            raise _error(
                status.HTTP_400_BAD_REQUEST, ErrorCode.REFRESH_TOKEN_INVALID, INVALID_REFRESH_TOKEN
            )

    @staticmethod
    def __revoke(refresh_token: str) -> None:
        try:
            revoke_refresh_token(refresh_token)
        except KeycloakUnavailableError as e:
            logger.error(f"Refresh token revocation failed: {e}")
            raise _error(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                ErrorCode.SERVICE_UNAVAILABLE,
                SERVICE_UNAVAILABLE,
            ) from e
        except TokenValidationError as e:
            logger.warning(f"Refresh token rejected: {e}")
            raise _error(
                status.HTTP_400_BAD_REQUEST, ErrorCode.REFRESH_TOKEN_INVALID, INVALID_REFRESH_TOKEN
            ) from e

    def __get_user_info(self, token: str) -> KeycloakUserInfo:
        try:
            profile = fetch_userinfo(token)
        except KeycloakUnavailableError as e:
            raise _error(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                ErrorCode.SERVICE_UNAVAILABLE,
                SERVICE_UNAVAILABLE,
            ) from e
        except TokenValidationError as e:
            logger.warning(f"Userinfo request rejected: {e}")
            raise _error(
                status.HTTP_401_UNAUTHORIZED, ErrorCode.TOKEN_INVALID, INVALID_CREDENTIALS
            ) from e

        if not isinstance(profile, dict):
            logger.error("Keycloak userinfo profile is not an object")
            raise _error(
                status.HTTP_502_BAD_GATEWAY,
                ErrorCode.UPSTREAM_PROFILE_INCOMPLETE,
                INCOMPLETE_PROFILE,
            )

        if not profile.get("nhs_number"):
            logger.error("Keycloak userinfo profile has no NHS number")
            raise _error(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                ErrorCode.NHS_NUMBER_MISSING,
                "NHS number missing from the identity provider profile",
            )

        try:
            return KeycloakUserInfo.model_validate(profile)
        except ValidationError as e:
            # Field names only: the error text would include profile values.
            fields = sorted({".".join(str(part) for part in err["loc"]) for err in e.errors()})
            logger.error(f"Keycloak userinfo profile is missing or invalid: {fields}")
            raise _error(
                status.HTTP_502_BAD_GATEWAY,
                ErrorCode.UPSTREAM_PROFILE_INCOMPLETE,
                INCOMPLETE_PROFILE,
            ) from e

    def __link_or_create(self, user_info: KeycloakUserInfo) -> tuple[User, str | None]:
        """
        Finds the user by Keycloak subject, then by NHS number, or creates one, and returns it
        with the subject it was previously linked to, if that differs. unique_id becomes the
        NHS Login subject from Keycloak; nhs_number is never changed on an existing user.
        """
        user = self.user_crud.get_user_by_keycloak_sub(user_info.sub)
        if user is None:
            matches = self.user_crud.get_users_by_nhs_number(user_info.nhs_number)
            if len(matches) > 1:
                logger.warning(
                    f"NHS number {mask_nhs_number(user_info.nhs_number)} matches "
                    f"{len(matches)} accounts: {[str(match.id) for match in matches]}"
                )
                raise _error(
                    status.HTTP_409_CONFLICT,
                    ErrorCode.ACCOUNT_CONFLICT,
                    "More than one account matches this NHS number",
                )
            user = matches[0] if matches else None

        previous_sub = None
        replaced_unique_id = None
        legacy_tokens: list[UserToken] = []
        if user is None:
            user = User(nhs_number=user_info.nhs_number)
        else:
            if user.keycloak_sub and user.keycloak_sub != user_info.sub:
                previous_sub = user.keycloak_sub
                logger.warning(
                    f"Relinking user {user.id} from Keycloak subject {previous_sub} "
                    f"to {user_info.sub}"
                )
            if user.unique_id != user_info.idp_sub:
                replaced_unique_id = user.unique_id
            legacy_tokens = self.user_crud.get_legacy_tokens(user.id)
            # Before any database change, so a Redis failure leaves the sync safe to retry.
            self.__clear_legacy_cache(legacy_tokens)

        profile = {
            "unique_id": user_info.idp_sub,
            "keycloak_sub": user_info.sub,
            "first_name": user_info.given_name,
            "email": user_info.email,
            "date_of_birth": user_info.birthdate,
            "gender": user_info.gender,
            "postcode": user_info.postcode,
            "identity_level": user_info.identity_proofing_level,
            "status": UserStatus.LOGIN.value,
            "status_updated_at": datetime.now(timezone.utc).replace(tzinfo=None),  # noqa: UP017 Not supported in Python 3.10
        }
        saved = self.user_crud.save_synced_user(user, profile, legacy_tokens)
        if replaced_unique_id:
            # The previous value is what a manual re-link to the legacy app would need.
            logger.info(
                f"Linked user {saved.id}: unique_id {replaced_unique_id} "
                f"replaced by {saved.unique_id}"
            )
        if legacy_tokens:
            # Again after the commit, in case a legacy request re-cached a token in between.
            self.__clear_legacy_cache(legacy_tokens, best_effort=True)
        return saved, previous_sub

    def __clear_legacy_cache(self, legacy_tokens: list[UserToken], best_effort: bool = False):
        """Removes the legacy auth cache entries, keyed by token hash, for the given tokens."""
        if not legacy_tokens:
            return
        try:
            self.redis.delete(*[RedisService.hash_token(t.token) for t in legacy_tokens])
        except RedisError as e:
            if best_effort:
                logger.warning(f"Legacy auth cache clear after commit failed: {e}")
                return
            logger.error(f"Legacy auth cache clear failed: {e}")
            raise _error(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                ErrorCode.SERVICE_UNAVAILABLE,
                SERVICE_UNAVAILABLE,
            ) from e

    def __open_session(self, user: User, sub: str, previous_sub: str | None, sid: str) -> None:
        try:
            with auth_step_span(STEP_SESSION_WRITE, flow=KEYCLOAK_FLOW):
                delete_user_sessions(self.redis, sub)
                if previous_sub:
                    delete_user_sessions(self.redis, previous_sub)
                save_session(
                    self.redis,
                    sid,
                    SessionUser(user_id=user.id, keycloak_sub=sub, user_email=user.email),
                )
        except RedisError as e:
            logger.error(f"Session write failed: {e}")
            raise _error(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                ErrorCode.SERVICE_UNAVAILABLE,
                SERVICE_UNAVAILABLE,
            ) from e
