import logging
from discord.ext import commands
from .utils.embed_handler import success
from .utils.checks import tortoise_bot_developer_only

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
        self.bot.load_extension(f"cogs.{extension_name}")
        await ctx.send(embed=success(f"{extension_name} loaded.", ctx.me))

    @commands.command(hidden=True)
    @commands.check(tortoise_bot_developer_only)
    async def unload(self, ctx, extension_name):
        """
        Unloads an extension.
        :param extension_name: cog name without suffix
        """
        self.bot.unload_extension(f"cogs.{extension_name}")
        await ctx.send(embed=success(f"{extension_name} unloaded.", ctx.me))


def setup(bot):
    bot.add_cog(BotOwnerCommands(bot))
