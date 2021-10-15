import discord


class GuildInviteTracker:
    def __init__(self, guild):
        self.guild = guild
        self._cache = {}

    async def refresh_invite_cache(self):
        self._cache = await self.get_all_invites()

    async def get_inviter(self, code):
        return self._cache.get(code)["created_by"]

    async def add_new_invite(self, invite):
        if invite.code not in self._cache.keys():
            self._cache[invite.code] = {"created_by": invite.inviter, "uses": invite.uses}

    async def remove_invite(self, invite):
        self._cache.pop(invite.code, None)

    async def track_invite(self):
        new_invites = await self.get_all_invites()
        for code, data in new_invites.items():
            if data["uses"] > self._cache.get(code)["uses"]:
                self._cache = new_invites
                return await self.get_inviter(code)

    async def get_all_invites(self) -> dict:
        try:
            invites = await self.guild.invites()
            new_invites = {}
            for invite in invites:
                if invite.code not in new_invites.keys():
                    new_invites[invite.code] = {"created_by": invite.inviter, "uses": invite.uses}
            return new_invites
        except discord.errors.Forbidden:
            pass
