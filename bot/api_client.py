import os
import json
import logging
from typing import Optional, List, Union
from datetime import datetime, timezone

import aiohttp
from dotenv import load_dotenv
from discord import Member, User, Message

from bot.constants import SuggestionStatus, tortoise_guild_id


load_dotenv()  # TODO why here also? in main too
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
        self.auth_header = {
            "Authorization": f"Token {os.getenv('API_ACCESS_TOKEN')}",
            "Content-Type": "application/json"
        }
        self.session = aiohttp.ClientSession(loop=loop, headers=self.auth_header)

    @staticmethod
    def _url_for(endpoint: str) -> str:
        return f"https://api.tortoisecommunity.com/private/{endpoint}"

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

    async def get(self, endpoint: str, **kwargs) -> Union[dict, List[dict]]:
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

    async def get_suggestions_under_review(self) -> List[dict]:
        # Gets all suggestion that are under-review
        return await self.get("suggestions/")

    async def get_suggestion_reaction_message_id(self, guild_id) -> int:
        # Returns the suggestion message id of the suggestion channel
        server_meta = await self.get_server_meta(guild_id=guild_id)
        return server_meta.get("suggestion_message_id")

    async def get_suggestion(self, suggestion_id: int) -> dict:
        # Return format
        # (message_id, author_id, author_name, default, brief, status, reason, avatar, link, date)
        return await self.get(f"suggestions/{suggestion_id}/")

    async def post_suggestion(self, author: User, message: Message, suggestion: str):
        # Creates new suggestion with default under-review status.
        data = {
            "message_id": message.id,
            "author_id": author.id,
            "author_name": author.display_name,
            "brief": suggestion,
            "avatar": str(author.avatar_url),
            "link": message.jump_url,
            "date": datetime.now(timezone.utc).isoformat()
        }
        await self.post("suggestions/", json=data)

    async def edit_suggestion(self, suggestion_id: int, status: SuggestionStatus, reason: str):
        data = {"status": status.value, "reason": reason}
        await self.put(f"suggestions/{suggestion_id}/", json=data)

    async def delete_suggestion(self, suggestion_id: int):
        await self.delete(f"suggestions/{suggestion_id}/")

    async def get_all_rules(self) -> List[dict]:
        # Return is list of dicts in format  ('number', 'name', alias', 'statement'):
        return await self.get("rules/")

    async def get_server_meta(self, guild_id: int = tortoise_guild_id) -> dict:
        # Return ('event_submission', 'mod_mail', 'bug_report', 'suggestions', 'suggestion_message_id', 'bot_status')
        return await self.get(f"server/meta/{guild_id}/")

    async def get_suggestion_message_id(self) -> int:
        return await self.get_server_meta()["suggestion_message_id"]

    async def edit_suggestion_message_id(self, new_id: int, guild_id: int = tortoise_guild_id) -> None:
        payload = {"suggestion_message_id" : new_id}
        await self.put(f"server/meta/{guild_id}/", json=payload)

    async def get_all_members(self) -> List[dict]:
        # Gets all members with all data except email
        return await self.get("members/")

    async def get_member_data(self, member_id: int) -> dict:
        # Gets all member data excluding email.
        return await self.get(f"members/{member_id}/")

    async def edit_member_roles(self, member: Member, roles_ids: List[int]):
        payload = {
            "user_id": member.id,
            "guild_id": member.guild.id,
            "roles": roles_ids
        }
        await self.put(f"members/{member.id}/", json=payload)

    async def insert_new_member(self, member: Member):
        """For inserting new members in the database."""
        data = {
            "name": member.display_name,
            "tag": member.discriminator,
            "user_id": member.id,
            "guild_id": member.guild.id,
            "join_date": datetime.now(timezone.utc).isoformat(),
            "member": True
        }
        await self.post("members/", json=data)

    async def member_rejoined(self, member: Member):
        data = {
            "user_id": member.id,
            "guild_id": member.guild.id,
            "leave_date": None,
            "member": True
        }
        await self.put(f"members/{member.id}/", json=data)

    async def member_left(self, member: Member):
        data = {
            "user_id": member.id,
            "guild_id": member.guild.id,
            "leave_date": datetime.now(timezone.utc).isoformat(),
            "member": False
        }
        await self.put(f"members/{member.id}/", json=data)

    async def get_top_members(self) -> List[dict]:
        # Returns top 20 members based on perks
        # Return is a list of dicts with ('user_id', 'name', 'tag', 'perks')
        return await self.get("members/top/")

    async def get_member_meta(self, member_id: int) -> dict:
        # Return ('join_date', 'leave_date', 'mod_mail', 'verified', 'member', 'roles')
        return await self.get(f"members/meta/{member_id}/")

    async def get_member_roles(self, member_id: int) -> List[int]:
        member_meta = await self.get_member_meta(member_id)
        return member_meta["roles"]

    async def get_member_leave_date(self, member_id: int) -> datetime:
        member_meta = await self.get_member_meta(member_id)
        return member_meta["leave_date"]

    async def is_verified(self, member_id: int) -> bool:
        """
        Returns bool whether the member is verified or not.
        If member does not exist in database raises ResponseCodeError
        """
        member_meta = await self.get_member_meta(member_id)
        return member_meta["verified"]

    async def get_member_moderation(self, member_id: int) -> dict:
        # Return ('warnings', 'muted_until', 'strikes', 'perks')
        return await self.get(f"members/moderation/{member_id}/")

    async def get_member_warnings(self, member_id: int) -> List[dict]:
        """
        API returns a list of str (which are stringed dicts) so need to deserialize that.
        Example return from API:
        [
            '{"date": "2020-05-04T21:36:43.045204+00:00",
            "reason": "test",
            "mod": 197918569894379520}'
        ]
        """
        member_moderation = await self.get_member_moderation(member_id)
        warnings = member_moderation["warnings"]
        deserialized_warnings = [json.loads(warning) for warning in warnings]
        return deserialized_warnings

    async def get_member_warnings_count(self, member_id: int) -> int:
        return len(await self.get_member_warnings(member_id))

    async def add_member_warning(self, mod_id: int, member_id: int, reason: str):
        new_warning = {
            "mod": mod_id,
            "reason": reason,
            "date": datetime.now(timezone.utc).isoformat()
        }

        current_warnings = await self.get_member_warnings(member_id)
        current_warnings.append(new_warning)
        serialized_warnings = [json.dumps(warning_dict) for warning_dict in current_warnings]
        warnings_payload = {"warnings": serialized_warnings}
        await self.put(f"members/moderation/{member_id}/", json=warnings_payload)
