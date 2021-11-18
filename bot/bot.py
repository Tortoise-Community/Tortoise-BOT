import sys
import logging
import asyncio
import traceback
import subprocess
from pathlib import Path
from typing import Generator

import discord
from discord.ext import commands

from bot.api_client import TortoiseAPI
from bot.constants import error_log_channel_id, bot_log_channel_id
from bot.utils.embed_handler import info


logger = logging.getLogger(__name__)
console_logger = logging.getLogger("console")


class Bot(commands.Bot):
    # If not empty then only these will be loaded. Good for local debugging. If empty all found are loaded.
    allowed_extensions = ()
    banned_extensions = ("advent_of_code", "tortoise_api", "socket_comm")

    def __init__(self, prefix="t.", *args, **kwargs):
        super(Bot, self).__init__(*args, command_prefix=prefix, intents=discord.Intents.all(), **kwargs)
        self.api_client: TortoiseAPI = TortoiseAPI(loop=self.loop)
        self._was_ready_once = False
        self.tortoise_meta_cache = {
            "event_submission": False,
            "mod_mail": False,
            "bug_report": False,
            "suggestions": False
        }

    async def on_ready(self):
        console_logger.info(
            f"Successfully logged in as {self.user.name} ID:{self.user.id} \t"
            f"d.py version: {discord.__version__} \t"
            "Further logging output will go to log file.."
        )

        if not self._was_ready_once:
            await self.on_first_ready()
            self._was_ready_once = True

    async def on_first_ready(self):
        self.load_extensions()
        await self.change_presence(activity=discord.Game(name="DM to Contact Staff"))
        await self.reload_tortoise_meta_cache()
        try:
            version = subprocess.check_output(["git", "describe", "--always"]).strip().decode("utf-8")
            bot_log_channel = self.get_channel(bot_log_channel_id)
            await bot_log_channel.send(embed=info(f"Bot restarted. Build version `{version}`", self.user, ""))
        except Exception as e:
            logger.info("Git image version not found", e)

    async def reload_tortoise_meta_cache(self):
        # For some reason it takes some time to propagate change in API database so if we fetch right away
        # we will get old data.
        await asyncio.sleep(3)
        self.tortoise_meta_cache = await self.api_client.get_server_meta()

    def load_extensions(self):
        for extension_path in Path("bot/cogs").glob("*.py"):
            extension_name = extension_path.stem

            if extension_name in self.banned_extensions:
                continue
            elif self.allowed_extensions and extension_name not in self.allowed_extensions:
                continue

            dotted_path = f"bot.cogs.{extension_name}"

            try:
                self.load_extension(dotted_path)
                console_logger.info(f"loaded {dotted_path}")
            except Exception as e:
                traceback_msg = traceback.format_exception(etype=type(e), value=e, tb=e.__traceback__)
                console_logger.info(f"Failed to load cog {dotted_path} - traceback:{traceback_msg}")

    @staticmethod
    async def on_connect():
        logger.info("Connection to Discord established.")

    @staticmethod
    async def on_disconnect():
        logger.info("Connection to Discord lost.")

    async def on_error(self, event: str, *args, **kwargs):
        exception_type, exception_value, exception_traceback = sys.exc_info()
        if issubclass(exception_type, discord.errors.Forbidden):
            return  # Ignore annoying messages (eg. if user disables DMs)

        msg = f"{event} event error exception!\n{traceback.format_exc()}"
        logger.critical(msg)
        await self.log_error(msg)

    async def log_error(self, message: str):
        if not self.is_ready() or self.is_closed():
            return

        error_log_channel = self.get_channel(error_log_channel_id)
        split_messages = list(Bot.split_string_into_chunks(message, 1900))

        for count, message in enumerate(split_messages):
            if count < 5:
                await error_log_channel.send(f"```Num {count+1}/{len(split_messages)}:\n{message}```")
            else:
                await error_log_channel.send("```Stopping spam, too many pages. See log for more info.```")
                break

    @staticmethod
    def split_string_into_chunks(string: str, chunk_size: int) -> Generator[str, None, None]:
        for i in range(0, len(string), chunk_size):
            yield string[i:i + chunk_size]
