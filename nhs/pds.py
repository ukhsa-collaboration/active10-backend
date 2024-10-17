import uuid
from time import time

import jwt
import requests

from utils.base_config import config as settings

PDS_API_PATH = "personal-demographics/FHIR/R4"
APP_KID = "better-health-app"


class PDSClient:
    def __init__(self, api_key, nhs_api_url) -> None:
        self.api_key = api_key
        self.nhs_api_url = nhs_api_url
        self.access_data = None

    def generate_and_sign_jwt(self):

        claims = {
            "sub": self.api_key,
            "iss": self.api_key,
            "jti": str(uuid.uuid4()),
            "aud": f"{self.nhs_api_url}/oauth2/token",
            "exp": int(time()) + 300,  # 5mins in the future
        }
        additional_headers = {"kid": APP_KID}

        return jwt.encode(
            claims,
            settings.nhs_pds_jwt_private_key,
            algorithm="RS512",
            headers=additional_headers,
        )

    def __get_pds_access_token(self):
        signed_token = self.generate_and_sign_jwt()
        url = f"{self.nhs_api_url}/oauth2/token"
        headers = {"content-type": "application/x-www-form-urlencoded"}
        post_data = {
            "grant_type": "client_credentials",
            "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
            "client_assertion": signed_token,
        }

        resp = requests.post(url, headers=headers, data=post_data)
        return resp.json()

    def __token_exchange(self, id_token_jwt):
        url = f"{self.nhs_api_url}/oauth2/token"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        post_data = {
            "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
            "subject_token_type": "urn:ietf:params:oauth:token-type:id_token",
            "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
            "subject_token": id_token_jwt,
            "client_assertion": self.generate_and_sign_jwt(),
        }
        resp = requests.post(url, headers=headers, data=post_data)

        if resp.status_code == 200:
            self.token_data = resp.json()
            return self.token_data
        else:
            print(f"!!! returned response ({resp.status_code}): {resp.json()}\n")

        return self.token_data

    def __get_user_details(self, token, id):
        url = f"{self.nhs_api_url}/{PDS_API_PATH}/Patient/{id}"
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Request-ID": str(uuid.uuid4()),
        }

        resp = requests.get(url, headers=headers)
        return resp.json()

    def __get_user_postcode(self, user_data):
        if user_data.get("address") and len(user_data["address"]) > 0:
            # sort addresses by period/start
            addresses = sorted(
                user_data["address"], key=lambda x: x.get("period", {}).get("start")
            )

            # return postcode of the most recent address
            return addresses[-1].get("postalCode") or ""

    def get_pds_data(self, id_token_jwt, patient_id):
        token = self.__token_exchange(id_token_jwt)
        # TODO: patient_info might contain error object instead of patient data, handle it
        # In case of getting error message the function will still return strings (empty),
        # wich will result in missing 'gender' and 'postcode' in user data
        patient_info = self.__get_user_details(token["access_token"], patient_id)

        return {
            "gender": patient_info.get("gender") or "",
            "postcode": self.__get_user_postcode(patient_info),
        }
