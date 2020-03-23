import os
import aiohttp
from dotenv import load_dotenv
from typing import Optional

# Don't put / at end
API_URL = "https://api.tortoisecommunity.ml"
load_dotenv()


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
    def __init__(self, loop):
        self.auth_header = {"Authorization": f"Token {os.getenv('API_REFRESH_TOKEN')}"}
        self.session = aiohttp.ClientSession(loop=loop, headers=self.auth_header)

    @staticmethod
    def _url_for(endpoint: str) -> str:
        return f"{API_URL}/{endpoint}"
    
    @classmethod
    async def raise_for_status(cls, response: aiohttp.ClientResponse) -> None:
        """Raise ResponseCodeError for non-OK response if an exception should be raised."""
        if response.status >= 400:
            try:
                response_json = await response.json()
                raise ResponseCodeError(response=response, response_json=response_json)
            except aiohttp.ContentTypeError:
                response_text = await response.text()
                raise ResponseCodeError(response=response, response_text=response_text)

    async def get(self, endpoint: str, **kwargs) -> dict:
        async with self.session.get(self._url_for(endpoint), **kwargs) as resp:
            await self.raise_for_status(resp)
            return await resp.json()

    async def patch(self, endpoint: str, **kwargs) -> dict:
        async with self.session.patch(self._url_for(endpoint), **kwargs) as resp:
            await self.raise_for_status(resp)
            return await resp.json()

    async def post(self, endpoint: str, **kwargs) -> dict:
        async with self.session.post(self._url_for(endpoint), **kwargs) as resp:
            await self.raise_for_status(resp)
            return await resp.json()

    async def put(self, endpoint: str, **kwargs) -> dict:
        async with self.session.put(self._url_for(endpoint), **kwargs) as resp:
            await self.raise_for_status(resp)
            return await resp.json()

    async def delete(self, endpoint: str, **kwargs) -> Optional[dict]:
        async with self.session.delete(self._url_for(endpoint), **kwargs) as resp:
            if resp.status == 204:
                return

            await self.raise_for_status(resp)
            return await resp.json()
