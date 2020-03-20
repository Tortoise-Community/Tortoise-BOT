import discord
from discord.ext import commands


class Bot(commands.Bot):
    error_log_channel_id = 690650346665803777

    def __init__(self, *args, **kwargs):
        super(Bot, self).__init__(*args, command_prefix="t.", **kwargs)

    async def on_ready(self):
        print("Successfully logged in and booted...!")
        print(f"Logged in as {self.user.name} with ID {self.user.id} \t d.py version: {discord.__version__}")

    async def log_error(self, message: str):
        if not self.is_ready() or self.is_closed():
            return

        error_log_channel = self.get_channel(Bot.error_log_channel_id)
        await error_log_channel.send(message)
