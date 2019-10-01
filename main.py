import os
import traceback
import discord
from discord.ext import commands

startup_extensions = ["verification",
                      "security",
                      "admins",
                      "fun",
                      "tortoise_server",
                      "other",
                      "reddit",
                      "help",
                      "cmd_error_handler"]

bot = commands.Bot(command_prefix="!")


@bot.command(hidden=True)
@commands.is_owner()
async def load(ctx, extension_path):
    """
    Loads an extension.
    :param extension_path: full path, dotted access, example:
                           cogs.admin

    """
    bot.load_extension(extension_path)
    await ctx.send(f"{extension_path} loaded.")


@bot.command(hidden=True)
@commands.is_owner()
async def unload(ctx, extension_path):
    """
    Unloads an extension.
    :param extension_path: full path, dotted access, example:
                           cogs.admin

    """
    bot.unload_extension(extension_path)
    await ctx.send(f"{extension_path} unloaded.")


@bot.event
async def on_ready():
    print("Successfully logged in and booted...!")
    print(f"Logged in as {bot.user.name} with ID {bot.user.id} \t d.py version: {discord.__version__}")

if __name__ == "__main__":
    for extension in startup_extensions:
        cog_path = f"cogs.{extension}"
        try:
            bot.load_extension(cog_path)
            print(f"Loaded {cog_path}")
        except Exception as e:
            traceback_msg = traceback.format_exception(etype=type(e), value=e, tb=e.__traceback__)
            print(f"Failed to load cog {cog_path} - traceback:{traceback_msg}")
    TOKEN = os.environ.get("Tok")
    bot.run(TOKEN)
