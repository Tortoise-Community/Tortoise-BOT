import math
import logging
import traceback

import discord
from discord.ext import commands

from bot.cogs.utils.embed_handler import failure


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
            missing_perms = self._get_missing_permission(error)
            _message = f"I need the **{missing_perms}** permission(s) to run this command."
            await ctx.send(embed=failure(_message))

        elif isinstance(error, commands.MissingPermissions):
            missing_perms = self._get_missing_permission(error)
            _message = f"You need the **{missing_perms}** permission(s) to use this command."
            await ctx.send(embed=failure(_message))

        elif isinstance(error, commands.CommandOnCooldown):
            msg = f"This command is on cooldown, please retry in {math.ceil(error.retry_after)}s."
            await ctx.send(embed=failure(msg))

        elif isinstance(error, commands.UserInputError):
            await ctx.send(embed=failure(f"Invalid command input: {error}"))

        elif isinstance(error, commands.NoPrivateMessage):
            try:
                await ctx.author.send(embed=failure("This command cannot be used in direct messages."))
            except discord.Forbidden:
                pass

        elif isinstance(error, commands.CheckFailure):
            """-.- All arguments including error message are eaten and pushed to .args"""
            if error.args:
                await ctx.send(embed=failure(". ".join(error.args)))
            else:
                await ctx.send(embed=failure("You do not have permission to use this command."))

        elif isinstance(error, discord.Forbidden):
            if error.code == 50007:
                # Ignore this error if it's because user closed DMs
                pass
            else:
                await ctx.send(embed=failure(f"{error}"))

        else:
            error_type = type(error)
            feedback_message = f"Uncaught {error_type} exception in command '{ctx.command}'"
            traceback_message = traceback.format_exception(etype=error_type, value=error, tb=error.__traceback__)
            log_message = f"{feedback_message} {traceback_message}"
            logger.critical(log_message)
            await self.bot.log_error(log_message)

    @classmethod
    def _get_missing_permission(cls, error) -> str:
        missing_perms = [perm.replace("_", " ").replace("guild", "server").title() for perm in error.missing_perms]

        if len(missing_perms) > 2:
            message = f"{'**, **'.join(missing_perms[:-1])}, and {missing_perms[-1]}"
        else:
            message = " and ".join(missing_perms)

        return message


def setup(bot):
    bot.add_cog(CommandErrorHandler(bot))
