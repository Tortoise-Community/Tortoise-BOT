import math
import logging
import traceback

import discord
from discord.ext import commands


logger = logging.getLogger(__name__)


class CommandErrorHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error_):
        # Get the original exception
        error = getattr(error_, "original", error_)

        # If command has local error handler, ignore
        if hasattr(ctx.command, "on_error"):
            pass

        elif isinstance(error, commands.CommandNotFound):
            pass

        elif isinstance(error, commands.BotMissingPermissions):
            fmt = self._get_missing_permission(error)
            _message = f"I need the **{fmt}** permission(s) to run this command."
            await ctx.send(_message)

        elif isinstance(error, commands.DisabledCommand):
            await ctx.send("This command has been disabled.")

        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"This command is on cooldown, please retry in {math.ceil(error.retry_after)}s.")

        elif isinstance(error, commands.MissingPermissions):
            fmt = self._get_missing_permission(error)
            _message = f"You need the **{fmt}** permission(s) to use this command."
            await ctx.send(_message)

        elif isinstance(error, commands.UserInputError):
            await ctx.send(f"Invalid command input: {error}")

        elif isinstance(error, commands.NoPrivateMessage):
            try:
                await ctx.author.send("This command cannot be used in direct messages.")
            except discord.Forbidden:
                pass

        elif isinstance(error, commands.CheckFailure):
            """-.- All arguments including error message are eaten and pushed to .args"""
            if error.args:
                await ctx.send(". ".join(error.args))
            else:
                await ctx.send("You do not have permission to use this command.")

        elif isinstance(error, discord.Forbidden):
            # Conditional to check if it is a closed DM that raised Forbidden
            if error.code == 50007:
                pass

        else:
            exception_msg = f"Ignoring exception in command {ctx.command} error: {traceback.format_exc()}"
            logger.warning(exception_msg)
            await self.bot.log_error(exception_msg)

    @classmethod
    def _get_missing_permission(cls, error) -> str:
        missing = [perm.replace("_", " ").replace("guild", "server").title() for perm in error.missing_perms]

        if len(missing) > 2:
            fmt = f"{'**, **'.join(missing[:-1])}, and {missing[-1]}"
        else:
            fmt = " and ".join(missing)

        return fmt


def setup(bot):
    bot.add_cog(CommandErrorHandler(bot))
