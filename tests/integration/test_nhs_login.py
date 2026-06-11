import base64
import hashlib
import os
import secrets
from typing import Any
from urllib.parse import urlencode

import pytest
import requests
from fastapi.testclient import TestClient
from seleniumbase import BaseCase

from main import app
from utils.base_config import config as settings

if os.environ.get("RUN_NHS_LOGIN_INTEGRATION") != "1":  # pragma: no cover - integration guard
    pytest.skip(
        "Skipping NHS Login integration tests; set RUN_NHS_LOGIN_INTEGRATION=1 to enable.",
        allow_module_level=True,
    )

BaseCase.main(__name__, __file__)

NHS_LOGIN_API = settings.test_nhs_login_api
TEST_NHS_EMAIL = settings.test_nhs_email
TEST_NHS_PASSWORD = settings.test_nhs_password
TEST_NHS_OTP = settings.test_nhs_otp

oauth_state: dict[str, str | None] = {"token": None, "code_verifier": None}


class MyTestClass(BaseCase):
    @classmethod
    def request_with_callback_response(cls, requests) -> Any | None | bool:
        for request in requests:
            if "/callback" in request.url:
                if request.response:
                    return request, True
                else:
                    return request, False

        return None, False

    def test_nhs_login_flow(self):
        oauth_state["code_verifier"] = secrets.token_urlsafe(64)
        challenge = self._create_code_challenge(oauth_state["code_verifier"])

        authorize_url = self._build_authorize_url(
            NHS_LOGIN_API,
            {
                "response_type": "code",
                "client_id": "active10_mobile",
                "redirect_uri": "active10dev://oauth_callback",
                "code_challenge": challenge,
                "code_challenge_method": "S256",
                "state": "client_state",
            },
        )

        self.open(authorize_url)
        self.assert_element("#user-email", timeout=25)
        self.type("#user-email", TEST_NHS_EMAIL)
        self.click('button[type="submit"]')

        self.assert_element("#password-input", timeout=25)
        self.type("#password-input", TEST_NHS_PASSWORD)
        self.click('button[type="submit"]')

        self.assert_element("#otp-input", timeout=25)
        self.type("#otp-input", TEST_NHS_OTP)
        self.click('button[type="submit"]')

        self.wait_for_ready_state_complete(timeout=30)

        max_retries = 30
        iteration = 0
        callback_request = None
        callback_request_found = False

        while not callback_request_found and iteration < max_retries:
            callback_request, callback_request_found = self.request_with_callback_response(
                self.driver.requests
            )
            if callback_request_found:
                break

            self.wait(1)
            iteration += 1

        if callback_request:
            response = callback_request.response
            redirect_uri = response.headers.get("Location") if response.headers else None
            if not redirect_uri:
                raise RuntimeError(f"Redirect URI not found in response: {response}")

            code = redirect_uri.split("code=")[-1].split("&")[0] if redirect_uri else None
            if not code:
                raise RuntimeError(f"Code not found in redirect URI: {redirect_uri}")

            oauth_state["token"] = self._exchange_code_for_token(code)

    def _exchange_code_for_token(self, code: str) -> str:
        code_verifier = oauth_state["code_verifier"]
        if code_verifier is None:
            raise RuntimeError("Code verifier not set")

        token_url = self._build_token_url(NHS_LOGIN_API)
        response = requests.post(
            token_url,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "code_verifier": code_verifier,
                "client_id": "active10_mobile",
                "redirect_uri": "active10dev://oauth_callback",
            },
            timeout=15,
        )
        data = response.json()
        if "access_token" not in data:
            raise RuntimeError(f"Token not found in response: {data}")
        return data["access_token"]

    @staticmethod
    def _create_code_challenge(verifier: str) -> str:
        digest = hashlib.sha256(verifier.encode("ascii")).digest()
        return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")

    @staticmethod
    def _build_authorize_url(base_url: str, params: dict[str, str]) -> str:
        sep = "&" if "?" in base_url else "?"
        return f"{base_url}{sep}{urlencode(params)}"

    @staticmethod
    def _build_token_url(base_url: str) -> str:
        if "/authorize" in base_url:
            return base_url.split("/authorize", maxsplit=1)[0].rstrip("/") + "/token"
        return base_url.rstrip("/") + "/token"


@pytest.fixture
def client():
    return TestClient(app)


class TestNHSLoginToken:
    @pytest.fixture(autouse=True)
    def setup(self, client: TestClient):
        self.client = client

    def test_nhs_login_token(self):
        token = oauth_state["token"]
        if token is None:
            raise RuntimeError("Token not captured during login flow")

        response = self.client.get(
            "/v1/users",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200  # noqa: PLR2004
        assert "email" in response.json()
