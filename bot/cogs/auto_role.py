from __future__ import annotations

import discord
from discord.ext import commands
from discord import app_commands

from bot.constants import challenger_role


class NotifyButton(discord.ui.View):
    """Persistent button view for challenge notifications."""

    def __init__(self):
        super().__init__(timeout=None)  # persistent

    @discord.ui.button(
        label="Notify me",
        style=discord.ButtonStyle.primary,
        emoji="🔔",
        custom_id="challenge_notify_button",
    )
    async def notify_me(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        if interaction.guild is None:
            await interaction.response.send_message(
                "This button can only be used in a server.",
                ephemeral=True,
            )
            return

        role = interaction.guild.get_role(challenger_role)
        if role is None:
            await interaction.response.send_message(
                "Notification role is not configured correctly.",
                ephemeral=True,
            )
            return

        member = interaction.user
        assert isinstance(member, discord.Member)

        if role in member.roles:
            try:
                await member.remove_roles(role, reason="Challenge notifications opt-out")
            except discord.Forbidden:
                await interaction.response.send_message("No permission | Contact Administrator", ephemeral=True)
            await interaction.response.send_message(
                "🔕 You will no longer receive challenge notifications.",
                ephemeral=True,
            )
        else:
            try:
                await member.add_roles(role, reason="Challenge notifications opt-in")
            except discord.Forbidden:
                await interaction.response.send_message("No permission | Contact Administrator", ephemeral=True)
            await interaction.response.send_message(
                "🔔 You will now receive challenge notifications!",
                ephemeral=True,
            )


class AutoRole(commands.Cog):
    """Cog for posting challenge notification opt-in messages."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

        # Register persistent view on startup
        self.bot.add_view(NotifyButton())

    @app_commands.command(
        name="post_challenge_notification",
        description="Post the challenge notification opt-in message.",
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def post_challenge_notification(
        self,
        interaction: discord.Interaction,
    ):
        embed = discord.Embed(
            title="Challenge Notifications",
            description=(
                "Click here to get notified whenever a new challenge is posted."
            ),
            color=discord.Color.blurple(),
        )

        embed.set_footer(text="You can opt out anytime by clicking the button again.")

        await interaction.response.send_message(
            embed=embed,
            view=NotifyButton(),
        )

    @post_challenge_notification.error
    async def post_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "You don’t have permission to use this command.",
                ephemeral=True,
            )
            return
        raise error


async def setup(bot: commands.Bot):
    await bot.add_cog(AutoRole(bot))
