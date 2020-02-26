from discord.ext import commands

deterrence_log_channel_id = 597119801701433357


class BotOwnerCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(hidden=True)
    @commands.is_owner()
    async def load(self, ctx, extension_name):
        """
        Loads an extension.
        :param extension_name: extension name
        """
        extension_path = f"cogs.{extension_name}"
        self.bot.load_extension(extension_path)
        await ctx.send(f"{extension_path} loaded.")

    @commands.command(hidden=True)
    @commands.is_owner()
    async def unload(self, ctx, extension_name):
        """
        Unloads an extension.
        :param extension_name: extension name
        """
        extension_path = f"cogs.{extension_name}"
        if extension_path == __name__:
            await ctx.send("It is not allowed to unload this cog.")
            return
        self.bot.unload_extension(extension_path)
        await ctx.send(f"{extension_path} unloaded.")


def setup(bot):
    bot.add_cog(BotOwnerCommands(bot))
