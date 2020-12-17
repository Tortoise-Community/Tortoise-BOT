import discord
from discord.ext import commands
from bot.utils import invite_help

class invite_tracker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.tracker = invite_help.TRACKER(bot)

    @commands.Cog.listener()
    async def on_ready(self):
        await self.tracker.ALL_INVITES()

    @commands.Cog.listener()
    async def on_invite_create(self, invite):
        await self.tracker.UPDATE_INVITE(invite)

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        await self.tracker.CREATE_GUILD_INVITES(guild)

    @commands.Cog.listener()
    async def on_invite_delete(self, invite):
        await self.tracker.DELETE_GUILD_INVITES(invite)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        await self.tracker.REMOVE_INVITES(guild)

    @bot.event
    async def on_member_join(member):
        inviter = await self.tracker.GET_INVITER(member).id
        '''
        Do your stuff below here.
        '''
