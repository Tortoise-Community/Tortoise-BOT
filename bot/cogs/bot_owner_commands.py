import logging
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands

from bot.utils.embed_handler import success, failure
from bot.utils.checks import tortoise_bot_developer_only


logger = logging.getLogger(__name__)


class BotOwnerCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="load")
    @app_commands.check(tortoise_bot_developer_only)
    async def load(self, interaction: discord.Interaction, extension_name: str):
        """
        Loads an extension.
        :param extension_name: cog name without suffix
        """
        await interaction.response.defer()
        self.bot.load_extension(f"bot.cogs.{extension_name}")

        msg = f"{extension_name} loaded."
        logger.info(f"{msg} by {interaction.user.id}")

        await interaction.followup.send(embed=success(msg, interaction.client.user), ephemeral=True)

    @app_commands.command(name="unload")
    @app_commands.check(tortoise_bot_developer_only)
    async def unload(self, interaction: discord.Interaction, extension_name: str):
        """
        Unloads an extension.
        :param extension_name: cog name without suffix
        """
        await interaction.response.defer()
        if extension_name == Path(__file__).stem:
            await interaction.followup.send(
                embed=failure("This cog is protected, cannot unload.")
            )
            return

        self.bot.unload_extension(f"bot.cogs.{extension_name}")

        msg = f"{extension_name} unloaded."
        logger.info(f"{msg} by {interaction.user.id}")

        await interaction.followup.send(
            embed=success(f"{extension_name} unloaded.", interaction.client.user), ephemeral=True
        )

    @app_commands.command(name="reload")
    @app_commands.check(tortoise_bot_developer_only)
    async def reload(self, interaction: discord.Interaction, extension_name: str):
        """
        Reloads an extension.
        :param extension_name: cog name without suffix
        """
        await interaction.response.defer()
        if extension_name == Path(__file__).stem:
            await interaction.followup.send(
                embed=failure("This cog is protected, cannot execute operation.")
            )
            return

        self.bot.reload_extension(f"bot.cogs.{extension_name}")
        await interaction.followup.send(
            embed=success(f"{extension_name} reloaded.", interaction.client.user)
        )


async def setup(bot):
    await bot.add_cog(BotOwnerCommands(bot))
