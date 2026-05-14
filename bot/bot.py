import itertools
import asyncio
import logging
import os
import subprocess
import sys
import traceback
from pathlib import Path
from typing import Generator

import aiohttp.client_exceptions
import discord
from discord.ext import commands, tasks

from bot.api_client import TortoiseAPI
from bot.constants import error_log_channel_id, system_log_channel_id, github_repo_link
from bot.manager import (
    Database, ProgressionManager, AFKManager, PointsManager, RetentionManager, TeamManager, GiveawayManager, DutyManager
)
from bot.utils.embed_handler import simple_embed
from bot.utils.error_handler import TortoiseCommandTree

logger = logging.getLogger(__name__)
console_logger = logging.getLogger("console")

DB_URL = os.getenv("DATABASE_URL")


class Bot(commands.Bot):
    # If not empty then only these will be loaded. Good for local debugging. If empty all found are loaded.
    allowed_extensions = ()
    banned_extensions = (
        "advent_of_code",
        "documentation",
        "help",
        "piston",
        "reddit",
        "tortoise_api",
        "utility",
        "health"
    )
    build_version = "mystery-build"
    advanced_protection: bool = True

    def __init__(self, prefix="t.", *args, **kwargs):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True

        super(Bot, self).__init__(
            *args,
            command_prefix=prefix,
            intents=intents,
            tree_cls=TortoiseCommandTree,
            **kwargs
        )
        self.api_client: TortoiseAPI = None
        self.tortoise_meta_cache = {
            "event_submission": False,
            "mod_mail": True,
            "bug_report": False,
            "suggestions": False,
            "staff_application": False,
        }
        self.suppressed_deletes = set()
        self._status_cycle = itertools.cycle([
                "DM to Contact Staff ⛉",
                "DM reports!",
                "DM for Mod Mail ⛉",
        ])
        self.advanced_protection = True
        self.db = None
        self.progression_manager = None
        self.points_manager = None
        self.afk_manager = None
        self.retention_manager = None
        self.team_manager = None
        self.giveaway_manager = None
        self.duty_manager = None
        self._sys_log_channel = None

    @property
    def sys_log_channel(self) -> discord.TextChannel:
        if self._sys_log_channel is None:
            self._sys_log_channel = self.get_channel(system_log_channel_id)
        return self._sys_log_channel

    @tasks.loop(minutes=1)
    async def rotate_status(self):
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.listening,
                name=next(self._status_cycle),
            )
        )

    async def on_ready(self):
        console_logger.info(
            f"Successfully logged in as {self.user.name} ID:{self.user.id} \t"
            f"d.py version: {discord.__version__} \t"
            "Further logging output will go to log file.."
        )
        await self.send_restart_message()
        if not self.rotate_status.is_running():
            self.rotate_status.start()

    async def send_restart_message(self: commands.Bot):
        try:
            commit_hash = subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"],
                stderr=subprocess.DEVNULL,
            ).decode().strip()
            commit_message = subprocess.check_output(
                ["git", "log", "-1", "--pretty=%s"],
                stderr=subprocess.DEVNULL,
            ).decode().strip()
        except Exception:
            commit_hash = os.getenv("BOT_BUILD_VERSION", "mystery-build")
            commit_message = ""

        self.build_version = commit_hash

        try:
            embed = simple_embed(message=f"Build version: [{commit_hash}]({github_repo_link}/commit/{commit_hash})",
                                 title="")
            embed.set_footer(text=commit_message)
            await self.sys_log_channel.send(
                embed=embed,
            )
        except discord.Forbidden:
            pass

    async def setup_hook(self):
        self.api_client: TortoiseAPI = TortoiseAPI()

        self.db = Database(DB_URL)
        await self.db.connect()

        self.progression_manager = ProgressionManager(self.db)
        self.afk_manager = AFKManager(self.db)
        self.points_manager = PointsManager(self.db)
        self.retention_manager = RetentionManager(self.db)
        self.team_manager = TeamManager(self.db)
        self.giveaway_manager = GiveawayManager(self.db)
        self.duty_manager = DutyManager(self.db)

        await self.progression_manager.setup()
        await self.afk_manager.setup()
        await self.points_manager.setup()
        await self.retention_manager.setup()
        await self.team_manager.setup()
        await self.giveaway_manager.setup()
        await self.duty_manager.setup()

        await self.load_extensions()
        # await self.reload_tortoise_meta_cache()
        await self.tree.sync()
        print("✅ Synced application commands")

    async def reload_tortoise_meta_cache(self):
        try:
            # For some reason it takes some time to propagate change in API database so if we fetch right away
            # we will get old data.
            await asyncio.sleep(3)
            self.tortoise_meta_cache = await self.api_client.get_server_meta()
        except aiohttp.client_exceptions.ClientConnectorDNSError as e:
            logging.error(f"DNS resolution failed for server meta: {e}")
            self.tortoise_meta_cache = {}  # Set empty cache as fallback
        except Exception as e:
            logging.error(f"Unexpected error loading server meta: {e}")
            self.tortoise_meta_cache = {}  # Set empty cache as fallback

    async def load_extensions(self):
        for extension_path in Path("bot/cogs").glob("*.py"):
            extension_name = extension_path.stem

            if extension_name in self.banned_extensions:
                continue
            elif (
                self.allowed_extensions
                and extension_name not in self.allowed_extensions
            ):
                continue

            dotted_path = f"bot.cogs.{extension_name}"

            try:
                await self.load_extension(dotted_path)
                console_logger.info(f"loaded {dotted_path}")
            except Exception as e:
                traceback_msg = traceback.format_exception(type(e), e, e.__traceback__)
                console_logger.info(
                    f"Failed to load cog {dotted_path} - traceback:{traceback_msg}"
                )

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
                await error_log_channel.send(
                    f"```Num {count+1}/{len(split_messages)}:\n{message}```"
                )
            else:
                await error_log_channel.send(
                    "```Stopping spam, too many pages. See log for more info.```"
                )
                break

    @staticmethod
    def split_string_into_chunks(
        string: str, chunk_size: int
    ) -> Generator[str, None, None]:
        for i in range(0, len(string), chunk_size):
            yield string[i : i + chunk_size]
