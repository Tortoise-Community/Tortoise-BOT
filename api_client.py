import os
import aiohttp
import logging
from datetime import datetime, timezone
from dotenv import load_dotenv
from discord import Member
from typing import Optional, List

load_dotenv()
logger = logging.getLogger(__name__)


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
        self.auth_header = {"Authorization": f"Token {os.getenv('API_ACCESS_TOKEN')}"}
        self.session = aiohttp.ClientSession(loop=loop, headers=self.auth_header)

    @staticmethod
    def _url_for(endpoint: str) -> str:
        return f"https://api.tortoisecommunity.ml/{endpoint}"
    
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


class TortoiseAPI(APIClient):
    def __init__(self, loop):
        super().__init__(loop)

    async def does_member_exist(self, member_id: int) -> bool:
        try:
            await self.is_verified(member_id, re_raise=True)
            return True
        except ResponseCodeError:
            return False

    async def is_verified(self, member_id: int, *, re_raise=False) -> bool:
        """
        "verify-confirmation/{member_id}/" endpoint return format {'verified': True} or 404 status
        :param member_id: int member id
        :param re_raise: bool whether to re-raise ResponseCodeError if member_id is not found.
        :return: bool
        """
        # Endpoint return format {'verified': True} or 404 status
        try:
            data = await self.get(f"verify-confirmation/{member_id}/")
        except ResponseCodeError as e:
            if re_raise:
                raise e
            else:
                return False

        return data["verified"]

    async def insert_new_member(self, member: Member):
        """For inserting new members in the database."""
        data = {"user_id": member.id,
                "guild_id": member.guild.id,
                "join_date": datetime.now(timezone.utc).isoformat(),
                "name": member.display_name,
                "tag": member.discriminator,
                "member": True}
        await self.post("members/", json=data)

    async def member_rejoined(self, member: Member):
        data = {"user_id": member.id, "guild_id": member.guild.id, "member": True, "leave_date": None}
        await self.put(f"members/edit/{member.id}/", json=data)

    async def member_left(self, member: Member):
        data = {"user_id": member.id,
                "guild_id": member.guild.id,
                "leave_date": datetime.now(timezone.utc).isoformat(),
                "member": False}
        await self.put(f"members/edit/{member.id}/", json=data)

    async def get_member_roles(self, member_id: int) -> List[int]:
        # Endpoint return format {'roles': [int...]} or 404 status
        data = await self.get(f"members/{member_id}/roles/")
        return data["roles"]

    async def edit_member_roles(self, member: Member, roles_ids: List[int]):
        # logger.debug(f"Roles from member {after} changed, changing db field to: {roles_ids}")
        await self.put(f"members/edit/{member.id}/", json={"user_id": member.id,
                                                           "guild_id": member.guild.id,
                                                           "roles": roles_ids})
