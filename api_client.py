import os
import aiohttp
from typing import Optional

api_url = "localhost"


class ResponseCodeError(ValueError):
    """Raised when a non-OK HTTP response is received."""

    def __init__(
        self,
        response: aiohttp.ClientResponse,
        response_json: Optional[dict] = None,
        response_text: str = ""
    ):
        self.status = response.status
        self.response_json = response_json or {}
        self.response_text = response_text
        self.response = response

    def __str__(self):
        response = self.response_json if self.response_json else self.response_text
        return f"Status: {self.status} Response: {response}"


class APIClient:
    def __init__(self, **kwargs):
        auth_headers = {
            "Authorization": f"Token {os.getenv('API_REFRESH_TOKEN')}"
        }

        if "headers" in kwargs:
            kwargs["headers"].update(auth_headers)
        else:
            kwargs["headers"] = auth_headers

        self.session = aiohttp.ClientSession()

    @staticmethod
    def _url_for(endpoint: str) -> str:
        return f"{api_url}/{endpoint}"
    
    @classmethod
    async def maybe_raise_for_status(cls, response: aiohttp.ClientResponse, should_raise: bool) -> None:
        """Raise ResponseCodeError for non-OK response if an exception should be raised."""
        if should_raise and response.status >= 400:
            try:
                response_json = await response.json()
                raise ResponseCodeError(response=response, response_json=response_json)
            except aiohttp.ContentTypeError:
                response_text = await response.text()
                raise ResponseCodeError(response=response, response_text=response_text)

    async def get(self, endpoint: str, *args, raise_for_status: bool = True, **kwargs) -> dict:
        async with self.session.get(self._url_for(endpoint), *args, **kwargs) as resp:
            await self.maybe_raise_for_status(resp, raise_for_status)
            return await resp.json()

    async def patch(self, endpoint: str, *args, raise_for_status: bool = True, **kwargs) -> dict:
        async with self.session.patch(self._url_for(endpoint), *args, **kwargs) as resp:
            await self.maybe_raise_for_status(resp, raise_for_status)
            return await resp.json()

    async def post(self, endpoint: str, *args, raise_for_status: bool = True, **kwargs) -> dict:
        async with self.session.post(self._url_for(endpoint), *args, **kwargs) as resp:
            await self.maybe_raise_for_status(resp, raise_for_status)
            return await resp.json()

    async def put(self, endpoint: str, *args, raise_for_status: bool = True, **kwargs) -> dict:
        async with self.session.put(self._url_for(endpoint), *args, **kwargs) as resp:
            await self.maybe_raise_for_status(resp, raise_for_status)
            return await resp.json()

    async def delete(self, endpoint: str, raise_for_status: bool = True, **kwargs) -> Optional[dict]:
        async with self.session.delete(self._url_for(endpoint), **kwargs) as resp:
            if resp.status == 204:
                return None

            await self.maybe_raise_for_status(resp, raise_for_status)
            return await resp.json()
