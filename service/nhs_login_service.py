import base64
import hashlib
import secrets
from datetime import datetime
from typing import Annotated
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from fastapi import Depends, HTTPException
from pydantic import HttpUrl

from auth.jwt_handler import TOKEN_EXPIRY_30_DAY_AS_SEC, sign_jwt
from crud.token_crud import TokenCRUD
from crud.user_crud import UserCRUD
from models import UserStatus
from models.user import User
from nhs.authenticator import Authenticator
from nhs.pds import PDSClient
from schemas.user import NHSUser
from service.redis_service import RedisService, get_redis_service
from utils.base_config import config

auth_nhs = Authenticator(
    config.nhs_login_client_id,
    config.nhs_login_authority_url,
    config.nhs_login_scopes,
    config.nhs_login_callback_url,
)

REDIS_UNAVAILABLE_DETAIL = "Redis unavailable"


class NHSLoginService:
    def __init__(
        self,
        user_crud: Annotated[UserCRUD, Depends()],
        user_token_crud: Annotated[TokenCRUD, Depends()],
        redis_service: Annotated[RedisService, Depends(get_redis_service)],
    ) -> None:
        self.userCRUD = user_crud
        self.token_crud = user_token_crud
        self.redis_service = redis_service
        self.pds_client = PDSClient(config.nhs_api_key, config.nhs_api_url)

    STATE_TTL_SECONDS = 600
    AUTH_CODE_TTL_SECONDS = 600

    def start_authorization(  # noqa: PLR0913
        self,
        response_type: str,
        client_id: str,
        redirect_uri: str,
        code_challenge: str,
        code_challenge_method: str,
        client_state: str | None,
        scope: str | None,
    ) -> HttpUrl:
        """
        Start OAuth authorization with NHS Login and store PKCE data.

        Returns NHS Login authorization URL.
        """
        if response_type != "code":
            raise HTTPException(status_code=400, detail="Unsupported response_type")
        if not code_challenge:
            raise HTTPException(status_code=400, detail="Missing code_challenge")
        if code_challenge_method not in {"S256"}:
            raise HTTPException(status_code=400, detail="Unsupported code_challenge_method")
        if not self.redis_service.is_available():
            raise HTTPException(status_code=503, detail=REDIS_UNAVAILABLE_DETAIL)

        state = secrets.token_urlsafe(32)
        state_data = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "code_challenge": code_challenge,
            "code_challenge_method": code_challenge_method,
            "client_state": client_state,
            "scope": scope,
        }

        stored = self.redis_service.set_json(
            self._state_key(state), state_data, ttl=self.STATE_TTL_SECONDS
        )
        if not stored:
            raise HTTPException(status_code=500, detail="Failed to store OAuth state")

        url = auth_nhs.get_authorization_url(state=state, vtr=config.nhs_vectors)
        return url

    def process_callback(self, req_args: dict) -> str:
        """
        Process callback from NHS Login Service, create local user, and issue auth code.

        :param req_args: The request arguments from the NHS login callback.
        :return: A redirect URL back to the client with auth code.
        """

        error = req_args.get("error")
        state = req_args.get("state")
        if not state:
            raise HTTPException(status_code=400, detail="Missing state")
        if not self.redis_service.is_available():
            raise HTTPException(status_code=503, detail=REDIS_UNAVAILABLE_DETAIL)

        state_data = self.redis_service.get_json(self._state_key(state))
        if not state_data:
            raise HTTPException(status_code=400, detail="Invalid or expired state")
        redirect_uri = state_data["redirect_uri"]

        if error:
            self.redis_service.delete(self._state_key(state))
            return self._build_redirect_url(
                redirect_uri, {"error": error, "state": state_data.get("client_state")}
            )

        # Extract logged-in user information from NHS
        user_info = self.get_user_info(req_args)

        if not user_info:
            raise ValueError("Failed to retrieve user information from NHS Login.")

        user = User(
            unique_id=user_info["sub"],
            nhs_number=user_info["nhs_number"],
            first_name=user_info["given_name"],
            email=user_info["email"],
            date_of_birth=user_info["birthdate"],
            gender=user_info["gender"],
            postcode=user_info["postcode"],
            identity_level=user_info["identity_proofing_level"],
        )

        # Check if the user already exists
        existing_user = self.userCRUD.get_user_by_sub(user.unique_id)

        if existing_user:
            # Update the existing user's information
            existing_user.first_name = user.first_name
            existing_user.email = user.email
            existing_user.date_of_birth = user.date_of_birth
            existing_user.gender = user.gender
            existing_user.postcode = user.postcode
            existing_user.identity_level = user.identity_level
            existing_user.status = UserStatus.LOGIN.value
            existing_user.status_updated_at = datetime.utcnow()
            result = self.userCRUD.update_user(existing_user)
        else:
            # Insert the new user
            result = self.userCRUD.create_user(user)

        auth_code = secrets.token_urlsafe(32)
        code_data = {
            "user_id": str(result.id),
            "code_challenge": state_data["code_challenge"],
            "code_challenge_method": state_data["code_challenge_method"],
            "client_id": state_data["client_id"],
            "redirect_uri": redirect_uri,
        }
        stored = self.redis_service.set_json(
            self._code_key(auth_code), code_data, ttl=self.AUTH_CODE_TTL_SECONDS
        )
        if not stored:
            raise HTTPException(status_code=500, detail="Failed to store authorization code")

        self.redis_service.delete(self._state_key(state))

        return self._build_redirect_url(
            redirect_uri,
            {"code": auth_code, "state": state_data.get("client_state")},
        )

    def exchange_code_for_token(
        self,
        code: str,
        code_verifier: str,
        client_id: str | None,
        redirect_uri: str | None,
    ) -> dict[str, object]:
        if not self.redis_service.is_available():
            raise HTTPException(status_code=503, detail=REDIS_UNAVAILABLE_DETAIL)

        code_key = self._code_key(code)
        code_data = self.redis_service.getdel_json(code_key)
        if not code_data:
            raise HTTPException(status_code=400, detail="Invalid or expired code")

        if client_id and client_id != code_data["client_id"]:
            raise HTTPException(status_code=400, detail="Invalid client_id")
        if redirect_uri and redirect_uri != code_data["redirect_uri"]:
            raise HTTPException(status_code=400, detail="Invalid redirect_uri")

        if not self._verify_pkce(
            code_verifier,
            code_data["code_challenge"],
            code_data["code_challenge_method"],
        ):
            raise HTTPException(status_code=400, detail="Invalid code_verifier")

        user = self.userCRUD.get_user_by_id(code_data["user_id"])
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        token = sign_jwt(str(user.id), extra_claims=self._user_claims(user))
        _ = self.token_crud.create_or_update_user_token(user_id=user.id, token=token)

        return {
            "access_token": token,
            "token_type": "Bearer",
            "expires_in": TOKEN_EXPIRY_30_DAY_AS_SEC,
            "user": self._serialize_user(user),
        }

    def get_user_info(self, req_args: dict) -> NHSUser:
        """
        Retrieve user info from NHS Login Service and get user gender and
        postcode by making second call to PDS API.

        :param req_args: The request arguments from the NHS login callback.
        :return: A NHSUser instance with user information.
        """
        auth_resp = auth_nhs.get_authorization_response(req_args)
        data = auth_nhs.get_access_token(auth_resp)
        user_info = auth_nhs.get_userinfo(data["access_token"])
        # TODO: gender and postcode needs to come from Mobile App now.
        user_info["gender"] = "na"
        user_info["postcode"] = "na"

        return user_info

    @staticmethod
    def _state_key(state: str) -> str:
        return f"oauth_state:{state}"

    @staticmethod
    def _code_key(code: str) -> str:
        return f"oauth_code:{code}"

    @staticmethod
    def _build_redirect_url(base_url: str, params: dict[str, str | None]) -> str:
        url_parts = urlsplit(base_url)
        query = dict(parse_qsl(url_parts.query, keep_blank_values=True))
        for key, value in params.items():
            if value is not None:
                query[key] = value
        new_query = urlencode(query)
        return urlunsplit(
            (url_parts.scheme, url_parts.netloc, url_parts.path, new_query, url_parts.fragment)
        )

    @staticmethod
    def _create_code_challenge(verifier: str) -> str:
        digest = hashlib.sha256(verifier.encode("ascii")).digest()
        return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")

    def _verify_pkce(self, verifier: str, challenge: str, method: str) -> bool:
        if method == "S256":
            return self._create_code_challenge(verifier) == challenge
        return False

    @staticmethod
    def _serialize_user(user: User) -> dict[str, object]:
        return {
            "id": str(user.id),
            "unique_id": user.unique_id,
            "nhs_number": user.nhs_number,
            "first_name": user.first_name,
            "email": user.email,
            "date_of_birth": user.date_of_birth.isoformat() if user.date_of_birth else None,
            "gender": user.gender,
            "postcode": user.postcode,
            "identity_level": user.identity_level,
        }

    @staticmethod
    def _user_claims(user: User) -> dict[str, object]:
        return {
            "email": user.email,
            "nhs_number": user.nhs_number,
            "first_name": user.first_name,
            "identity_level": user.identity_level,
        }
