from __future__ import annotations

import discord
from discord.ext import commands
from discord import app_commands

from bot.constants import challenger_role
from bot.utils.checks import tortoise_bot_developer_only
from bot.utils.embed_handler import info, failure


class ModMailStartView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Create Ticket",
        style=discord.ButtonStyle.premium,
        emoji="📩",
        custom_id="tortoise_modmail_panel",
    )
    async def start_modmail(self, interaction: discord.Interaction, button: discord.ui.Button):

        bot = interaction.client
        cog: "TortoiseDM" = bot.get_cog("TortoiseDM")
        user = interaction.user

        if cog.is_any_session_active(user.id):
            await interaction.response.send_message(
                "You already have an active session.",
                ephemeral=True
            )
            return

        if cog.cool_down.is_on_cool_down(user.id):
            msg = f"You are on cooldown. Retry after {cog.cool_down.retry_after(user.id)}s."
            await interaction.response.send_message(embed=failure(msg), ephemeral=True)
            return

        cog.cool_down.add_to_cool_down(user.id)

        await interaction.response.send_message(
            "📩 Opening mod mail in your DMs...",
            ephemeral=True,
            delete_after=5,
        )

        try:
            await user.send(embed=info(
                "Your ticket is created.\n"
                "Please wait for moderator response.",
                user
            ))
        except discord.HTTPException:
            await interaction.followup.send(
                "I couldn't DM you. Please enable DMs.",
                ephemeral=True
            )
            return

        await cog.create_mod_mail(user, source="panel")


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


class ButtonUtility(commands.Cog):
    """Cog for posting challenge notification opt-in messages."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

        # Register persistent view on startup
        self.bot.add_view(NotifyButton())
        self.bot.add_view(ModMailStartView())


    @app_commands.command(
        name="post_challenge_notification",
        description="Post the challenge notification opt-in message.",
    )
    @app_commands.check(tortoise_bot_developer_only)
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

    @app_commands.command(
        name="post_modmail_panel",
        description="Post the mod mail contact panel."
    )
    @app_commands.check(tortoise_bot_developer_only)
    async def post_panel(self, interaction: discord.Interaction):

        embed = discord.Embed(
            title="Ban appeal",
            description="Press the button below to create a ticket.",
            color=discord.Color.green()
        )

        embed.set_footer(text="This conversation will be logged.")

        await interaction.response.send_message(
            embed=embed,
            view=ModMailStartView()
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(ButtonUtility(bot))
