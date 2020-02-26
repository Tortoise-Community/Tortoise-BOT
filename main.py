import os
import traceback
from dotenv import load_dotenv
import discord
from discord.ext import commands

startup_extensions = ["verification",
                      "security",
                      "bot_owner_commands",
                      "moderation",
                      "fun",
                      "tortoise_server",
                      "other",
                      "reddit",
                      "help",
                      "music",
                      "socket_comm",
                      "cmd_error_handler"]


class Bot(commands.Bot):
    DEFAULT_PREFIX = "."

    def __init__(self, *args, **kwargs):
        super(Bot, self).__init__(*args, command_prefix=Bot.DEFAULT_PREFIX, **kwargs)

    @staticmethod
    async def on_ready():
        print("Successfully logged in and booted...!")
        print(f"Logged in as {bot.user.name} with ID {bot.user.id} \t d.py version: {discord.__version__}")


if __name__ == "__main__":
    load_dotenv()
    bot = Bot()

    for extension in startup_extensions:
        cog_path = f"cogs.{extension}"
        try:
            bot.load_extension(cog_path)
            print(f"Loaded {cog_path}")
        except Exception as e:
            traceback_msg = traceback.format_exception(etype=type(e), value=e, tb=e.__traceback__)
            print(f"Failed to load cog {cog_path} - traceback:{traceback_msg}")

    bot.run(os.getenv("BOT_TOKEN"))
