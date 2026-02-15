import logging
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import ExtensionAlreadyLoaded, ExtensionNotLoaded

from bot.utils.embed_handler import success, failure
from bot.utils.checks import tortoise_bot_developer_only


logger = logging.getLogger(__name__)


class BotOwnerCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def _ext(self, name: str) -> str:
        return f"bot.cogs.{name}"

    @app_commands.command(name="load")
    @app_commands.check(tortoise_bot_developer_only)
    async def load(self, interaction: discord.Interaction, extension_name: str):
        """
        Loads an extension.
        :param extension_name: cog name without suffix
        """
        await interaction.response.defer()
        ext = self._ext(extension_name)
        try:
            await self.bot.load_extension(ext)
            msg = f"{extension_name} loaded."
            logger.info(f"{msg} by {interaction.user.id}")
            await interaction.followup.send(embed=success(msg, interaction.client.user), ephemeral=True)

        except ExtensionAlreadyLoaded:
            logger.error(f"Extension already loaded {extension_name}")
            await interaction.followup.send(
                embed=failure("Extension already loaded. Did you mean reload?"),
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Failed to load extension {extension_name}: {e}")
            await interaction.followup.send(
                embed=failure(f"Failed to load extension {e}"),
                ephemeral=True
            )

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
                embed=failure("This cog is protected, cannot unload."),
                ephemeral=True
            )
            return

        ext = self._ext(extension_name)

        try:
            await self.bot.unload_extension(ext)
            msg = f"{extension_name} unloaded."
            logger.info(f"{msg} by {interaction.user.id}")
            await interaction.followup.send(
                embed=success(msg, interaction.client.user),
                ephemeral=True
            )

        except ExtensionNotLoaded:
            logger.error(f"Extension not loaded {extension_name}")
            await interaction.followup.send(
                embed=failure("Extension is not loaded."),
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Failed to unload extension {extension_name}: {e}")
            await interaction.followup.send(
                embed=failure(f"Failed to unload extension {e}"),
                ephemeral=True
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
                embed=failure("This cog is protected, cannot execute operation."),
                ephemeral=True
            )
            return

        ext = self._ext(extension_name)

        try:
            await self.bot.reload_extension(ext)
            msg = f"{extension_name} reloaded."
            logger.info(f"{msg} by {interaction.user.id}")
            await interaction.followup.send(
                embed=success(msg, interaction.client.user),
                ephemeral=True
            )

        except ExtensionNotLoaded:
            logger.error(f"Extension not loaded {extension_name}")
            await interaction.followup.send(
                embed=failure("Extension is not loaded. Use load instead."),
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Failed to reload extension {extension_name}: {e}")
            await interaction.followup.send(
                embed=failure(f"Failed to reload extension {e}"),
                ephemeral=True
            )


async def setup(bot):
    await bot.add_cog(BotOwnerCommands(bot))