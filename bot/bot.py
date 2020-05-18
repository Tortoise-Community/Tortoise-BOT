import sys
import logging
import traceback
from typing import Generator

import discord
from discord.ext import commands

from bot.api_client import TortoiseAPI
from bot.constants import error_log_channel_id


logger = logging.getLogger(__name__)
console_logger = logging.getLogger("console")


class Bot(commands.Bot):
    def __init__(self, prefix, *args, **kwargs):
        super(Bot, self).__init__(*args, command_prefix=prefix, **kwargs)
        self.api_client: TortoiseAPI = TortoiseAPI(self.loop)
        self._was_ready_once = False

    async def on_ready(self):
        console_logger.info(
            f"Successfully logged in as {self.user.name} ID:{self.user.id} \t"
            f"d.py version: {discord.__version__} \t"
            "Further logging output will go to log file.."
        )

        if not self._was_ready_once:
            await self.change_presence(activity=discord.Game(name="DM me!"))
            self._was_ready_once = True

    async def on_error(self, event: str, *args, **kwargs):
        exception_type, exception_value, exception_traceback = sys.exc_info()

        if isinstance(exception_type, discord.Forbidden):
            return  # Ignore annoying messages (eg. if user disables DMs)

        msg = f"{event} event error exception!\n{traceback.format_exc()}"
        logger.critical(msg)
        await self.log_error(msg)

    async def log_error(self, message: str):
        if not self.is_ready() or self.is_closed():
            return

        error_log_channel = self.get_channel(error_log_channel_id)
        split_messages = list(Bot.split_string_into_chunks(message, 1980))

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
