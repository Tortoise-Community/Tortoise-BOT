import os
import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Optional, List, Union

import aiohttp
from dotenv import load_dotenv
from discord import Member, User, Message

from bot.constants import SuggestionStatus, tortoise_guild_id, github_repo_stats_endpoint


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


class BaseAPIClient:
    def __init__(self, base_api_url: str, **kwargs):
        self.base_api_url = base_api_url
        self.session = aiohttp.ClientSession(**kwargs)

    def _url_for(self, endpoint: str) -> str:
        return f"{self.base_api_url}{endpoint}"

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


class GithubAPI(BaseAPIClient):
    def __init__(self):
        super().__init__(github_repo_stats_endpoint)

    async def get_project_commits(self, repository_name: str) -> int:
        """
        Github API does not support getting repository commit count.
        It can only get each commit information, which would be expensive.
        However if we tell API to get all commits and list only one commit information per page then
        we can just get number of pages with which we will know total number of commits.
        """
        async with self.session.get(
                url=f"{github_repo_stats_endpoint}{repository_name}/commits",
                params={"sha": "master", "per_page": 1}
        ) as response:
            await self.raise_for_status(response)
            last_page = response.links.get("last")
            if last_page:
                # we can get number of pages from url parameters
                url_parameters = last_page["url"].query
                # remember that number of commits = number of pages because 1 page = 1 commit
                return int(url_parameters["page"])
            else:
                return 1


class TortoiseAPI(BaseAPIClient):
    def __init__(self):
        auth_header = {
            "Authorization": f"Token {os.getenv('API_ACCESS_TOKEN')}",
            "Content-Type": "application/json"
        }
        super().__init__("https://api.tortoisecommunity.org/private/", headers=auth_header)

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
            "avatar": str(author.avatar.url),
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
        server_meta = await self.get_server_meta()
        return server_meta["suggestion_message_id"]

    async def edit_suggestion_message_id(self, new_id: int, guild_id: int = tortoise_guild_id) -> None:
        payload = {"suggestion_message_id": new_id}
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

    async def get_projects_data(self):
        return await self.get("projects/")

    async def put_project_data(self, project_id, data):
        await self.put(f"projects/{project_id}/", json=data)


class HataAPI(BaseAPIClient):
    HATA_API_URL = "https://huyanematsu.pythonanywhere.com/docs/api"
    HATA_API_VERSION = "v1"
    HATA_API_ENDPOINT = f"{HATA_API_URL}/{HATA_API_VERSION}/"

    def __init__(self):
        super().__init__(self.HATA_API_ENDPOINT)

    async def search(self, search_for: str) -> List[dict]:
        params = {"search_for": search_for}
        return await self.get("search", params=params)


class AdventOfCodeAPI(BaseAPIClient):
    AOC_REQUEST_HEADER = {"user-agent": "Tortoise Discord Community AoC event bot"}
    COOKIES = {"session": os.getenv("AOC_COOKIE")}
    AOC_API_URL = "https://adventofcode.com/{year}/leaderboard/private/view/{leaderboard_id}"

    def __init__(self, leaderboard_id: str, year: int = 2020):
        super().__init__(
            self.AOC_API_URL.format(year=year, leaderboard_id=leaderboard_id),
            headers=self.AOC_REQUEST_HEADER,
            cookies=self.COOKIES
        )

    async def get_leaderboard(self):
        return await self.get(endpoint=".json")


class StackAPI(BaseAPIClient):
    STACK_API_URL = "https://api.stackexchange.com"
    STACK_API_VERSION = "2.2"

    def __init__(self):
        super().__init__(f"{self.STACK_API_URL}/{self.STACK_API_VERSION}/")

    async def search(
            self,
            keyword: str,
            *,
            site: str,
            order: str = "desc",
            sort: str = "activity",
            limit: int = 10
    ) -> dict:
        params = {
            "title": keyword,
            "site": site,
            "order": order,
            "sort": sort,
            "pagesize": limit
        }
        if limit < 0 or limit > 100:
            raise ValueError("StackAPI pagesize has to be in 0-100 range.")
        return await self.get("search/advanced", params=params)
