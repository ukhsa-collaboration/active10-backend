import json
import time
from datetime import datetime, timedelta
from enum import Enum

import jwt
import requests
from fastapi import HTTPException
from requests.exceptions import HTTPError, RequestException

from utils.base_config import logger

ALGORITHM = "ES256"
GOJAUNTLY_BASE_URL = "https://connect.gojauntly.com"
TOKEN_EXPIRATION_MINUTES = 15


class HttpMethod(Enum):
    GET = "GET"
    POST = "POST"


class GoJauntlyApi:
    """Client for interacting with the GoJauntly API."""

    def __init__(self, key_id: str, secret_key: str, issuer_id: str):
        """
        Initialize the GoJauntlyApi client.

        Args:
            key_id (str): The Key ID for JWT.
            secret_key (str): The secret key for JWT.
            issuer_id (str): The Issuer ID for JWT.
        """
        self._token: str | None = None
        self.token_gen_date: datetime | None = None
        self.key_id = key_id
        self.secret_key = secret_key
        self.issuer_id = issuer_id
        self._debug: bool = False
        self._initialize_token()

    def _initialize_token(self):
        """Generate the initial token."""
        _ = self.token

    def _generate_token(self) -> str:
        """Generate a new JWT token."""

        self.token_gen_date = datetime.now()
        exp = int(
            time.mktime(
                (self.token_gen_date + timedelta(minutes=TOKEN_EXPIRATION_MINUTES)).timetuple()
            )
        )
        payload = {"iss": self.issuer_id, "exp": exp, "aud": "gojauntly-api-v1"}
        headers = {"kid": self.key_id, "typ": "JWT"}
        token = jwt.encode(
            payload=payload, key=self.secret_key, headers=headers, algorithm=ALGORITHM
        )
        logger.info("Generated new token.")

        return token

    def _api_call(
        self, url: str, method: HttpMethod, data: dict | None = None
    ) -> dict | requests.Response:
        """
        Make an API call to the specified endpoint.

        Args:
            url (str): The endpoint URL.
            method (HttpMethod): The HTTP method to use.
            data (Optional[Dict]): Data to be sent in the request body.

        Returns:
            Union[Dict, requests.Response]: The response from the API call.
        """
        url = f"{GOJAUNTLY_BASE_URL}{url}"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json" if method == HttpMethod.POST else None,
        }

        if self._debug:
            logger.info(f"Making {method.value} request to {url}")

        try:
            response = requests.request(
                method.value,
                url,
                headers=headers,
                data=json.dumps(data) if data else None,
            )
            response.raise_for_status()

            content_type = response.headers.get("content-type", "")

            if content_type in ["application/json", "application/vnd.api+json"]:
                data = response.json()

                if "errors" in data:
                    error_message = data.get("errors", [])[0].get("detail", "Unknown error")
                    logger.error(f"API error: {error_message}")
                    raise HTTPException(status_code=500, detail=error_message)

                return data

            logger.error(f"Unexpected content type: {content_type}")
            raise HTTPException(status_code=500, detail="Unexpected content type")

        except HTTPError as http_err:
            logger.error(f"HTTP error occurred: {http_err}")
            raise HTTPException(  # noqa: B904
                status_code=http_err.response.status_code,
                detail=http_err.response.json(),
            )

        except RequestException as req_err:
            logger.error(f"Request error occurred: {req_err}")
            raise HTTPException(status_code=500, detail="Internal server error")  # noqa: B904

    @property
    def token(self) -> str:
        """Return the current token, generating a new one if needed."""
        if not self._token or (
            self.token_gen_date + timedelta(minutes=TOKEN_EXPIRATION_MINUTES) < datetime.now()
        ):
            self._token = self._generate_token()

        return self._token

    def curated_walk_search(self, data: dict) -> dict:
        """Search for curated walks.

        Args:
            data (Dict): The search parameters.

        Returns:
            Dict: The search results.
        """
        return self._api_call(url="/curated-walks/search", method=HttpMethod.POST, data=data)

    def curated_walk_retrieve(self, id: str, data: dict) -> dict:
        """Retrieve a specific curated walk by ID.

        Args:
            id (str): The ID of the curated walk.
            data (Dict): Additional data for the request.

        Returns:
            Dict: The details of the curated walk.
        """
        return self._api_call(url=f"/curated-walks/{id}", method=HttpMethod.POST, data=data)

    def dynamic_routes_route(self, data: dict) -> dict:
        """Get dynamic route.

        Args:
            data (Dict): Route parameters.

        Returns:
            Dict: The route details.
        """
        return self._api_call(url="/routing/route", method=HttpMethod.POST, data=data)

    def dynamic_routes_circular(self, data: dict) -> dict:
        """Get dynamic circular route.

        Args:
            data (Dict): Circular route parameters.

        Returns:
            Dict: The circular route details.
        """
        return self._api_call(url="/routing/circular", method=HttpMethod.POST, data=data)

    def dynamic_routes_circular_collection(self, data: dict) -> dict:
        """Get dynamic circular collection route.

        Args:
            data (Dict): Circular collection route parameters.

        Returns:
            Dict: The circular collection route details.
        """
        return self._api_call(url="/routing/circular/collection", method=HttpMethod.POST, data=data)
