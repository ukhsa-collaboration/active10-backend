from fastapi import Depends
from pydantic import HttpUrl

from auth.jwt_handler import sign_jwt
from crud.user_crud import UserCRUD
from models.user import User
from nhs.authenticator import Authenticator
from nhs.pds import PDSClient
from schemas.user import NHSUser
from utils.base_config import config

auth_nhs = Authenticator(
    config.nhs_login_client_id,
    config.nhs_login_authority_url,
    config.nhs_login_scopes,
    config.nhs_login_callback_url,
)


class NHSLoginService:
    def __init__(self, user_crud: UserCRUD = Depends()) -> None:
        self.userCRUD = user_crud
        self.pds_client = PDSClient(config.nhs_api_key, config.nhs_api_url)

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

    def __create_state(self, app_name: str, app_internal_id: str) -> str:
        """
        Create a state for NHS Login Service using the app name and app internal ID.

        :param app_name: App name.
        :param app_internal_id: App internal ID.
        :return: A state string in the format "app_name_app_internal_id".
        """
        return f"{app_name}_{app_internal_id}"

    def process_callback(self, req_args: dict) -> str:
        """
        Process callback from NHS Login Service.It stores the user information in DB and return deeplink URL for mobile app.

        :param req_args: The request arguments from the NHS login callback.
        :return: A deeplink URL containing a signed JWT token.
        """

        error = req_args.get("error")
        if error:
            # if access denied return no consent deeplink and force user
            # to use app without NHS login
            if error == "access_denied":
                return f"{config.app_uri}nhs_noconsent"
        # Extract logged-in user information from NHS
        user_info = self.get_user_info(req_args)
        # Store user information to database
        # TODO: Check if the user is None
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

        self.userCRUD.upsert_user(user)
        redirect_url = self.generate_redirect_url(user_info)

        return redirect_url

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

    def generate_redirect_url(self, user_info: NHSUser) -> str:
        """
        Generate a redirect URL for the user after successful login.
        This URL is consumed by the mobile app.

        :param user_info: An NHSUser instance with user information.
        :return: A redirect URL containing a signed JWT token.
        """
        token = sign_jwt(user_info["sub"])
        redirect_url = f"{config.app_uri}nhs_user_logged_in?token={token}"
        return redirect_url
