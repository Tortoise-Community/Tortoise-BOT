import logging

from discord.ext import commands
from discord import Member, Embed, Message, Color, Forbidden

from bot import constants
from bot.bot import Bot
from bot.api_client import ResponseCodeError
from bot.cogs.utils.converters import DatabaseMember
from bot.cogs.utils.embed_handler import failure, success, goodbye, info
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
        try:
            response = await self.bot.api_client.is_verified(member)
        except ResponseCodeError as e:
            msg = f"Something went wrong, got response status {e.status}.\nDoes the member exist?"
            await ctx.send(embed=failure(msg))
        else:
            await ctx.send(embed=info(f"{response}", ctx.me, f"{member}"))

    @commands.command()
    @commands.check(tortoise_bot_developer_only)
    @commands.check(check_if_it_is_tortoise_guild)
    async def show_data(self, ctx, member: DatabaseMember):
        try:
            data = await self.bot.api_client.get_member_data(member)
        except ResponseCodeError as e:
            msg = f"Something went wrong, got response status {e.status}.\nDoes the member exist?"
            await ctx.send(embed=failure(msg))
        else:
            pretty = "\n".join(f"{key}:{value}\n" for key, value in data.items())
            await ctx.send(embed=info(pretty, ctx.me, "Member data"))

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
        await self._suggestion_helper(ctx, message_id, reason, constants.SuggestionStatus.approved)
        await ctx.send(embed=success("Suggestion successfully approved."), delete_after=5)

    @commands.command()
    @commands.check(tortoise_bot_developer_only)
    @commands.check(check_if_it_is_tortoise_guild)
    async def deny(self, ctx, message_id: int, *, reason: str = "No reason specified"):
        """Deny a suggestion"""
        await self._suggestion_helper(ctx, message_id, reason, constants.SuggestionStatus.denied)
        await ctx.send(embed=success("Suggestion successfully denied."), delete_after=5)

    async def _suggestion_helper(
        self,
        ctx,
        message_id: int,
        reason: str,
        status: constants.SuggestionStatus
    ):
        """
        Helper for suggestion approve/deny.
        :param ctx: context where approve/deny command was called.
        :param message_id: suggestion message id
        :param reason: reason for approving/denying
        :param status: is the message being approved or denied
        :return:
        """
        msg: Message = await self.user_suggestions_channel.fetch_message(message_id)
        if msg is None or not msg.embeds:
            await ctx.send(embed=failure("Suggestion message found."), delete_after=5)
            return

        api_data = await self.bot.api_client.get_suggestion(message_id)

        msg_embed = msg.embeds[0]
        if status == constants.SuggestionStatus.denied:
            msg_embed.colour = Color.red()
        elif status == constants.SuggestionStatus.approved:
            msg_embed.colour = Color.green()

        if not msg_embed.fields:
            await ctx.send(embed=failure("Message is not in correct format."), delete_after=5)
            return

        msg_embed.set_field_at(0, name="Status", value=status.value)

        if len(msg_embed.fields) == 1:
            msg_embed.add_field(name="Reason", value=reason, inline=True)
        else:
            msg_embed.set_field_at(1, name="Reason", value=reason, inline=True)

        await self.bot.api_client.edit_suggestion(message_id, status, reason)
        await msg.edit(embed=msg_embed)
        await self._dm_member(api_data["author_id"], msg_embed)

    async def _dm_member(self, user_id, embed: Embed):
        try:
            user = self.bot.get_user(user_id)
            await user.send(embed=embed)
        except Forbidden:
            pass

    @commands.command()
    @commands.check(tortoise_bot_developer_only)
    @commands.check(check_if_it_is_tortoise_guild)
    async def delete_suggestion(self, ctx, message_id: int):
        """Delete a suggestion"""
        msg: Message = await self.user_suggestions_channel.fetch_message(message_id)
        if msg is not None:
            await msg.delete()

        await self.bot.api_client.delete_suggestion(message_id)
        await ctx.send(embed=success("Suggestion successfully deleted."), delete_after=5)


def setup(bot):
    bot.add_cog(TortoiseAPI(bot))
