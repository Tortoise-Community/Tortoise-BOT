from discord import app_commands
import discord
import logging
from bot.utils.embed_handler import failure
from bot.utils.exceptions import (TortoiseStaffCheckFailure,
                                  TortoiseGuildCheckFailure,
                                  TortoiseBotDeveloperCheckFailure)

class TortoiseCommandTree(app_commands.CommandTree):

    async def on_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            msg = "You don't have permission to use this command."

        elif isinstance(error, app_commands.BotMissingPermissions):
            msg = "I don't have the required permissions to run this command."

        elif isinstance(error, app_commands.CommandOnCooldown):
            msg = f"Command on cooldown. Try again in {error.retry_after:.1f}s."

        elif isinstance(error, app_commands.CheckFailure):
            msg = "You cannot use this command."

        elif isinstance(error, TortoiseStaffCheckFailure):
            msg = "This command can only be used by tortoise staff."

        elif isinstance(error, TortoiseGuildCheckFailure):
            msg = "This command can only be used in tortoise guild."

        elif isinstance(error, TortoiseBotDeveloperCheckFailure):
            msg = "This command can only be used by tortoise bot developer."

        elif isinstance(error, app_commands.CommandInvokeError):
            msg = "An unexpected error occurred while running the command."

        else:
            msg = "Unknown error occurred."

        try:
            if interaction.response.is_done():
                await interaction.followup.send(embed=failure(msg), ephemeral=True)
            else:
                await interaction.response.send_message(embed=failure(msg), ephemeral=True)
        except discord.HTTPException:
            pass
        logging.error(f"App command error: {error}", exc_info=error)
