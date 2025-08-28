from datetime import datetime, timezone
from typing import Dict

from app.core.config import settings
from app.core.security import sign_jwt
from app.cruds.token_crud import TokenCRUD
from app.cruds.user_crud import UserCRUD
from app.models import User, UserStatus
from app.nhs.authenticator import Authenticator
from app.nhs.pds import PDSClient
from app.schemas.user import NHSUser
from fastapi import Depends
from pydantic import HttpUrl

auth_nhs = Authenticator(
    settings.NHS_LOGIN_CLIENT_ID,
    settings.NHS_LOGIN_AUTHORITY_URL,
    settings.NHS_LOGIN_SCOPES,
    settings.NHS_LOGIN_CALLBACK_URL,
)


class NHSLoginService:
    def __init__(
            self, user_crud: UserCRUD = Depends(), user_token_crud: TokenCRUD = Depends()
    ) -> None:
        self.userCRUD = user_crud
        self.token_crud = user_token_crud
        self.pds_client = PDSClient(settings.NHS_API_KEY, settings.NHS_API_URL)

    def get_nhs_login_url(self, app_name: str, app_internal_id: str) -> HttpUrl:
        """
        Generate a URL for NHS login service with app name and app internal ID.
        :param app_name: App name.
        :param app_internal_id: App internal ID.
        :return: A URL to redirect to NHS Login auth flow.
        """
        state = self.__create_state(app_name, app_internal_id)
        url = auth_nhs.get_authorization_url(state=state)
        return url

    @staticmethod
    def __create_state(app_name: str, app_internal_id: str) -> str:
        """
        Create a state for NHS Login Service using the app name and app internal ID.

        :param app_name: App name.
        :param app_internal_id: App internal ID.
        :return: A state string in the format "app_name_app_internal_id".
        """
        return f"{app_name}_{app_internal_id}"

    def process_callback(self, req_args: dict) -> str:
        """
        Process callback from NHS Login Service.It stores the user information
        in DB and return deeplink URL for mobile app.

        :param req_args: The request arguments from the NHS login callback.
        :return: A deeplink URL containing a signed JWT token.
        """

        error = req_args.get("error")
        if error:
            # if access denied return no consent deeplink and force user
            # to use app without NHS login
            if error == "access_denied":
                return f"{settings.APP_URI}nhs_noconsent"

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
            existing_user.status_updated_at = datetime.now(timezone.utc)
            result = self.userCRUD.update_user(existing_user)
        else:
            # Insert the new user
            result = self.userCRUD.create_user(user)

        # Generate and return new redirect URL for mobile app
        generated_data = self.generate_redirect_url(result)
        _ = self.token_crud.create_or_update_user_token(
            user_id=result.id, token=generated_data.get("token")
        )

        return generated_data.get("redirect_url")

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
        pds_data = self.pds_client.get_pds_data(
            data["id_token_jwt"], user_info["nhs_number"]
        )

        user_info["gender"] = pds_data["gender"]
        user_info["postcode"] = pds_data["postcode"]

        return user_info

    @staticmethod
    def generate_redirect_url(user_info: User) -> Dict[str, str]:
        """
        Generate a redirect URL for the user after successful login.
        This URL is consumed by the mobile app.

        :param user_info: An NHSUser instance with user information.
        :return: A dict of redirect URL containing a signed JWT token and token as string.
        """
        token = sign_jwt(str(user_info.id))
        redirect_url = f"{settings.APP_URI}nhs_user_logged_in?token={token}"
        return {"redirect_url": redirect_url, "token": token}
