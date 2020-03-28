import traceback
import logging
import math
import discord
from discord.ext import commands

logger = logging.getLogger(__name__)


class CommandErrorHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_command_error(self, ctx, error_):
        # If command has local error handler, return
        if hasattr(ctx.command, "on_error"):
            return

        # Get the original exception
        error = getattr(error_, "original", error_)

        if isinstance(error, commands.CommandNotFound):
            return

        if isinstance(error, commands.BotMissingPermissions):
            missing = [perm.replace("_", " ").replace("guild", "server").title() for perm in error.missing_perms]
            if len(missing) > 2:
                fmt = "{}, and {}".format("**, **".join(missing[:-1]), missing[-1])
            else:
                fmt = " and ".join(missing)
            _message = "I need the **{}** permission(s) to run this command.".format(fmt)
            await ctx.send(_message)
            return

        if isinstance(error, commands.DisabledCommand):
            await ctx.send("This command has been disabled.")
            return

        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send("This command is on cooldown, please retry in {}s.".format(math.ceil(error.retry_after)))
            return

        if isinstance(error, commands.MissingPermissions):
            missing = [perm.replace("_", " ").replace("guild", "server").title() for perm in error.missing_perms]
            if len(missing) > 2:
                fmt = "{}, and {}".format("**, **".join(missing[:-1]), missing[-1])
            else:
                fmt = " and ".join(missing)
            _message = "You need the **{}** permission(s) to use this command.".format(fmt)
            await ctx.send(_message)
            return

        if isinstance(error, commands.UserInputError):
            await ctx.send(f"Invalid command input: {error}")
            return

        if isinstance(error, commands.NoPrivateMessage):
            try:
                await ctx.author.send("This command cannot be used in direct messages.")
            except discord.Forbidden:
                pass
            return

        if isinstance(error, commands.CheckFailure):
            """-.- All arguments including error message are eaten and pushed to .args"""
            if error.args:
                await ctx.send(". ".join(error.args))
            else:
                await ctx.send("You do not have permission to use this command.")
            return

        """if isinstance(error, TortoiseGuildCheckFailure):
            await ctx.send("Can only be used in Tortoise guild.")
            return

        if isinstance(error, TortoiseBotDeveloperCheckFailure):
            await ctx.send("Can only be used by Tortoise developers.")
            return"""

        exception_msg = f"Ignoring exception in command {ctx.command} error: {traceback.format_exc()}"
        logger.warning(exception_msg)
        await self.bot.log_error(exception_msg)
                

def setup(bot):
    bot.add_cog(CommandErrorHandler(bot))
