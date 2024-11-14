import pytest
from seleniumbase import BaseCase
from fastapi.testclient import TestClient
from utils.base_config import config as settings

from main import app

BaseCase.main(__name__, __file__)

NHS_LOGIN_API = settings.nhs_login_api
TEST_NHS_EMAIL = settings.test_nhs_email
TEST_NHS_PASSWORD = settings.test_nhs_password
TEST_NHS_OTP = settings.test_nhs_otp

token = None


class MyTestClass(BaseCase):

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

        self.wait(30)

        requests_lists = self.driver.requests or []

        global token

        with open("test_logs.txt", "w") as f:
            if requests_lists:
                f.write(f"Requests Count = {len(requests_lists)}\n")
            else:
                f.write("No requests captured\n")

            for request in requests_lists:
                self.wait_for_ready_state_complete(timeout=30)
                if "/callback" in request.url:  # Check if the request has a URL
                    f.write(f"url: {request.url}\n")
                    f.write(f"***  request headers: ***\n {request.headers}\n")
                    f.write(f"***  response: ***\n {request.response if request.response else 'No Response Content'}\n")
                    f.write(f"***  Status Code:   ***\n {request.response.status_code}")
                    f.write(f"***  Response Headers:  ***\n {request.response.headers}")
                    redirect_uri = request.response.headers.get('Location')
                    token = redirect_uri.split("=")[-1] if redirect_uri else "Redirect URI not extracted yet"
                    f.write(f"token = {token}")
                    break


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
