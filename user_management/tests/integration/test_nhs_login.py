from typing import Union, Any

import pytest
from fastapi.testclient import TestClient
from seleniumbase import BaseCase

from app.main import app
from app.core.config import settings

BaseCase.main(__name__, __file__)

NHS_LOGIN_API = settings.TEST_NHS_LOGIN_API
TEST_NHS_EMAIL = settings.TEST_NHS_EMAIL
TEST_NHS_PASSWORD = settings.TEST_NHS_PASSWORD
TEST_NHS_OTP = settings.TEST_NHS_OTP

token = None


class MyTestClass(BaseCase):
    @classmethod
    def request_with_callback_response(cls, requests) -> Union[Union[Any, None], bool]:
        for request in requests:
            if "/callback" in request.url:
                if request.response:
                    return request, True
                else:
                    return request, False

        return None, False

    def test_nhs_login_flow(self):
        self.open(NHS_LOGIN_API)
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
            callback_request, callback_request_found = (
                self.request_with_callback_response(self.driver.requests)
            )
            if callback_request_found:
                break

            self.wait(1)
            iteration += 1

        global token

        if callback_request:
            response = callback_request.response
            redirect_uri = (
                response.headers.get("Location") if response.headers else None
            )
            if not redirect_uri:
                raise Exception(f"Redirect URI not found in response: {response}")

            token = redirect_uri.split("=")[-1] if redirect_uri else None
            if not token:
                raise Exception(f"Token not found in redirect URI: {redirect_uri}")


@pytest.fixture
def client():
    return TestClient(app)


class TestNHSLoginToken:
    @pytest.fixture(autouse=True)
    def setup(self, client: TestClient):
        self.client = client

    def test_nhs_login_token(self):
        global token

        if token is None:
            raise Exception("Token not captured during login flow")

        response = self.client.get(
            "/v1/users/",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        assert "email" in response.json()
