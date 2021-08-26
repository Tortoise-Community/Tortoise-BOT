from discord.ext import commands

from bot.utils import invite_help


class InviteTracker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.tracker = invite_help.TRACKER(bot)

    @commands.Cog.listener()
    async def on_ready(self):
        await self.tracker.all_invites()

    @commands.Cog.listener()
    async def on_invite_create(self, invite):
        await self.tracker.update_invite(invite)

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        await self.tracker.create_guild_invites(guild)

    @commands.Cog.listener()
    async def on_invite_delete(self, invite):
        await self.tracker.delete_guild_invites(invite)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        await self.tracker.remove_invites(guild)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        # TODO
        # inviter = await self.tracker.get_inviter(member).id
        pass
