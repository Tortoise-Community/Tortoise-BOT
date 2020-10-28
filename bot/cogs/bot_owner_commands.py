import logging
from pathlib import Path

from discord.ext import commands

from bot.utils.embed_handler import success, failure
from bot.utils.checks import tortoise_bot_developer_only


logger = logging.getLogger(__name__)


class BotOwnerCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(hidden=True)
    @commands.check(tortoise_bot_developer_only)
    async def load(self, ctx, extension_name):
        """
        Loads an extension.
        :param extension_name: cog name without suffix
        """
        self.bot.load_extension(f"bot.cogs.{extension_name}")

        msg = f"{extension_name} loaded."
        logger.info(f"{msg} by {ctx.author.id}")

        await ctx.send(embed=success(msg, ctx.me))

    @commands.command(hidden=True)
    @commands.check(tortoise_bot_developer_only)
    async def unload(self, ctx, extension_name):
        """
        Unloads an extension.
        :param extension_name: cog name without suffix
        """
        if extension_name == Path(__file__).stem:
            await ctx.send(embed=failure("This cog is protected, cannot unload."))
            return

        self.bot.unload_extension(f"bot.cogs.{extension_name}")

        msg = f"{extension_name} unloaded."
        logger.info(f"{msg} by {ctx.author.id}")

        await ctx.send(embed=success(f"{extension_name} unloaded.", ctx.me))

    @commands.command(hidden=True)
    @commands.check(tortoise_bot_developer_only)
    async def reload(self, ctx, extension_name):
        """
        Reloads an extension.
        :param extension_name: cog name without suffix
        """
        if extension_name == Path(__file__).stem:
            await ctx.send(embed=failure("This cog is protected, cannot execute operation."))
            return

        self.bot.reload_extension(f"bot.cogs.{extension_name}")
        await ctx.send(embed=success(f"{extension_name} reloaded.", ctx.me))


def setup(bot):
    bot.add_cog(BotOwnerCommands(bot))
