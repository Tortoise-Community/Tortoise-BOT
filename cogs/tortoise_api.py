import logging
from discord import Member
from discord.ext import commands
from .utils.checks import check_if_it_is_tortoise_guild, tortoise_bot_developer_only
from .utils.converters import DatabaseMember
from bot import Bot


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class TortoiseAPI(commands.Cog):
    """Commands using Tortoise API"""
    def __init__(self, bot: Bot):
        self.bot: Bot = bot

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    @commands.check(check_if_it_is_tortoise_guild)
    async def is_verified(self, ctx, member: DatabaseMember):
        response = await self.bot.api_client.is_verified(member)
        await ctx.send(response)

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    @commands.check(check_if_it_is_tortoise_guild)
    async def does_member_exist(self, ctx, member: DatabaseMember):
        response = await self.bot.api_client.does_member_exist(member)
        await ctx.send(response)

    @commands.command()
    @commands.has_permissions(administrator=True)
    @commands.check(tortoise_bot_developer_only)
    async def show_data(self, ctx, member: DatabaseMember):
        data = await self.bot.api_client.get_member_data(member)
        await ctx.send(f"{data}")

    @commands.Cog.listener()
    @commands.check(check_if_it_is_tortoise_guild)
    async def on_member_remove(self, member: Member):
        logger.debug(f"Member {member} left, updating database accordingly.")
        await self.bot.api_client.member_left(member)


def setup(bot):
    bot.add_cog(TortoiseAPI(bot))
