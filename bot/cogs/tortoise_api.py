import logging

from discord import Member
from discord.ext import commands

from bot import constants
from bot.bot import Bot
from bot.api_client import ResponseCodeError
from bot.cogs.utils.converters import DatabaseMember
from bot.cogs.utils.embed_handler import failure, warning, success, goodbye, suggestion_embed
from bot.cogs.utils.checks import check_if_it_is_tortoise_guild, tortoise_bot_developer_only


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class TortoiseAPI(commands.Cog):
    """Commands using Tortoise API"""
    def __init__(self, bot: Bot):
        self.bot: Bot = bot
        self.system_log_channel = bot.get_channel(constants.system_log_channel_id)
        self.user_suggestions_channel = bot.get_channel(constants.suggestions_channel_id)

    @commands.command()
    @commands.has_permissions(administrator=True)
    @commands.check(check_if_it_is_tortoise_guild)
    async def is_verified(self, ctx, member: DatabaseMember):
        response = await self.bot.api_client.is_verified(member)
        await ctx.send(response)

    @commands.command()
    @commands.has_permissions(administrator=True)
    @commands.check(check_if_it_is_tortoise_guild)
    async def does_member_exist(self, ctx, member: DatabaseMember):
        response = await self.bot.api_client.does_member_exist(member)
        await ctx.send(response)

    @commands.command()
    @commands.check(tortoise_bot_developer_only)
    @commands.check(check_if_it_is_tortoise_guild)
    async def show_data(self, ctx, member: DatabaseMember):
        try:
            data = await self.bot.api_client.get_member_data(member)
        except ResponseCodeError as e:
            await ctx.send(embed=failure(f"Something went wrong, got response status {e.status}.\n"
                                         f"Does the member exist?"))
            return

        await ctx.send(f"{data}")

    @commands.command()
    @commands.check(tortoise_bot_developer_only)
    @commands.check(check_if_it_is_tortoise_guild)
    async def manually_add_database_member(self, ctx, member: Member):
        if await self.bot.api_client.does_member_exist(member.id):
            await ctx.send(embed=warning("Member already exists, aborting.."))
            return

        logger.info(f"{ctx.author} is manually adding member {member} {member.id} to database")
        await self.bot.api_client.insert_new_member(member)
        await ctx.send(embed=success(f"Member {member} successfully added to database."))

    @commands.Cog.listener()
    @commands.check(check_if_it_is_tortoise_guild)
    async def on_member_remove(self, member: Member):
        logger.debug(f"Member {member} left, updating database accordingly.")
        await self.bot.api_client.member_left(member)
        await self.system_log_channel.send(embed=goodbye(f"{member} has left the Tortoise Community."))

    @commands.command()
    @commands.check(tortoise_bot_developer_only)
    @commands.check(check_if_it_is_tortoise_guild)
    async def approve(self, ctx, message_id: int, *, reason: str = "No reason specified"):
        """Approve a suggestion"""
        msg = await self.user_suggestions_channel.fetch_message(message_id)
        if msg is None or not msg.embeds:
            await ctx.send(embed=failure("Suggestion message found."), delete_after=5)
            return

        msg_embed = msg.embeds[0]

        await self.bot.api_client.put_suggestion(message_id, constants.SuggestionStatus.approved, reason)
        await msg.update(
            embed=suggestion_embed(msg.author, constants.SuggestionStatus.approved, msg_embed.description)
        )
        await ctx.send(embed=success("Suggestion successfully approved."), delete_after=5)

    @commands.command()
    @commands.check(tortoise_bot_developer_only)
    @commands.check(check_if_it_is_tortoise_guild)
    async def deny(self, ctx, message_id: int, *, reason: str = "No reason specified"):
        """Deny a suggestion"""
        msg = await self.user_suggestions_channel.fetch_message(message_id)
        if msg is None or not msg.embeds:
            await ctx.send(embed=failure("Suggestion message found."), delete_after=5)
            return

        msg_embed = msg.embeds[0]

        await self.bot.api_client.put_suggestion(message_id, constants.SuggestionStatus.denied, reason)
        await msg.update(embed=suggestion_embed(msg.author, constants.SuggestionStatus.denied, msg_embed.description))
        await ctx.send(embed=success("Suggestion successfully denied."), delete_after=5)


def setup(bot):
    bot.add_cog(TortoiseAPI(bot))
