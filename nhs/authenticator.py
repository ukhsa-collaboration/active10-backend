import uuid
import jwt
from oic import rndstr
from oic.oauth2 import AuthorizationResponse
from oic.oic import Client
from oic.oic.message import Claims, ClaimsRequest
from oic.utils.authn.client import CLIENT_AUTHN_METHOD
from oic.utils.time_util import utc_time_sans_frac
from utils.base_config import config as settings


class Authenticator:
    def __init__(
        self, client_id: str, authority_url: str, scopes: str, redirect_uri: str
    ):
        self.client = self._get_client(client_id, authority_url)
        self.callback_url = redirect_uri
        self.scopes = scopes

    def _get_client(self, client_id, authority_url):
        client = Client(client_id=client_id, client_authn_method=CLIENT_AUTHN_METHOD)
        client.provider_config(authority_url)
        return client

        # vtr='["P0.Cp.Cd", "P0.Cp.Ck", "P0.Cm"]'

    def get_authorization_url(self, state, vtr='["P9.Cp.Cd", "P9.Cp.Ck", "P9.Cm"]'):
        claims_request = ClaimsRequest(
            id_token=Claims(email={"essential": None}, phone_number=None),
            userinfo=Claims(
                given_name={"essential": True},
                family_name={"essential": True},
                nickname=None,
            ),
        )
        args = {
            "client_id": self.client.client_id,
            "response_type": "code",
            "scope": self.scopes,
            "nonce": rndstr(),
            "redirect_uri": self.callback_url,
            "state": state,
            "vtr": vtr,
            "claims": claims_request,
        }

        auth_req = self.client.construct_AuthorizationRequest(request_args=args)
        return auth_req.request(self.client.authorization_endpoint)

    def get_access_token(self, args):
        request_args = {
            "code": args["code"],
            "client_id": self.client.client_id,
            "redirect_uri": self.callback_url,
        }

        kwargs = {
            "algorithm": "RS512",
            "authn_endpoint": "token",
            "authn_method": "private_key_jwt",
            "client_assertion": self._create_assertion(),
            "request_args": request_args,
            "scope": self.scopes,
        }
        if "state" in args:
            kwargs["state"] = args["state"]

        return self.client.do_access_token_request(**kwargs)

    def _create_assertion(self, lifetime=60):
        _now = utc_time_sans_frac()
        client_id = self.client.client_id

        payload = {
            "iss": client_id,
            "sub": client_id,
            "aud": self.client.token_endpoint,
            "jti": str(uuid.uuid4()),
            "exp": _now + lifetime,
        }

        token = jwt.encode(
            payload, key=settings.nhs_pds_jwt_private_key, algorithm="RS512"
        )

        return token

    def get_userinfo(self, access_token):
        user_info = self.client.do_user_info_request(token=access_token, method="GET")
        return user_info.to_dict()

    def get_authorization_response(self, args):
        return self.client.parse_response(
            AuthorizationResponse, info=args, sformat="dict"
        )
