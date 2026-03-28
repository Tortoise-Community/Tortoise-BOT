import logging
from typing import Union
from datetime import datetime, timedelta

import discord
from discord import User, Member, app_commands
from discord.ext import commands

from bot import constants
from bot.utils.message_handler import ConfirmationMessage
from bot.utils.checks import check_if_tortoise_staff
from bot.utils.converters import GetFetchUser, DatetimeConverter
from bot.utils.embed_handler import success, warning, failure, info, infraction_embed, thumbnail, authored


logger = logging.getLogger(__name__)

class DMModal(discord.ui.Modal, title="Send DM to Role"):
    def __init__(self, role: discord.Role, interaction: discord.Interaction):
        super().__init__()
        self.role = role
        self.interaction = interaction

    message = discord.ui.TextInput(
        label="Message",
        style=discord.TextStyle.paragraph,
        placeholder="Type your message here...",
        required=True,
        max_length=2000
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        members = (m for m in self.role.members if not m.bot)
        failed_logs = []
        failed_mentions = []
        count = 0

        for member in members:
            embed = discord.Embed(
                title=f"Message for {self.role.name}",
                description=self.message.value,
                color=self.role.color
            )

            if interaction.guild.icon:
                embed.set_author(
                    name=interaction.guild.name,
                    icon_url=interaction.guild.icon.url
                )

            try:
                await member.send(embed=embed)
                count += 1
            except discord.HTTPException:
                failed_mentions.append(member.mention)
                failed_logs.append(str(member))

        await interaction.followup.send(
            embed=success(f"Successfully notified {count} users.")
        )

        if failed_mentions:
            failed_str = "\n".join(failed_mentions)

            if len(failed_str) > 4000:
                failed_str = failed_str[:4000] + "..."

            fail_embed = warning("Failed to notify users:\n\n" + failed_str)

            await interaction.followup.send(
                embed=fail_embed,
                ephemeral=False
            )

            logger.info(f"Failed to DM: {failed_logs}")




class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._tortoise_guild = None
        self._muted_role = None
        self._verified_role = None
        self._deterrence_log_channel = None

    @property
    def tortoise_guild(self):
        if self._tortoise_guild is None:
            self._tortoise_guild = self.bot.get_guild(constants.tortoise_guild_id)
        return self._tortoise_guild

    @property
    def muted_role(self):
        if self._muted_role is None:
            self._muted_role = self.tortoise_guild.get_role(constants.muted_role_id)
        return self._muted_role

    @property
    def verified_role(self):
        if self._verified_role is None:
            self._verified_role = self.tortoise_guild.get_role(constants.verified_role_id)
        return self._verified_role

    @property
    def deterrence_log_channel(self):
        if self._deterrence_log_channel is None:
            self._deterrence_log_channel = self.bot.get_channel(constants.deterrence_log_channel_id)
        return self._deterrence_log_channel

    @app_commands.command()
    @app_commands.checks.bot_has_permissions(kick_members=True)
    @app_commands.check(check_if_tortoise_staff)
    async def kick(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No specific reason"):
        """Kicks  member from the guild."""

        await interaction.response.defer()

        deterrence_embed = infraction_embed(interaction, member, constants.Infraction.kick, reason)
        await self.deterrence_log_channel.send(embed=deterrence_embed)

        dm_embed = infraction_embed(interaction, member, constants.Infraction.kick, reason, True, True)
        await member.send(embed=dm_embed)

        await member.kick(reason=reason)
        await interaction.followup.send(embed=success(f"{member.name} successfully kicked."), ephemeral=True)


    # @app_commands.command()
    # @app_commands.checks.bot_has_permissions(administrator=True)
    # @app_commands.checks.has_permissions(administrator=True)
    # @app_commands.checks.cooldown(1, 120)
    # @app_commands.check(check_if_it_is_tortoise_guild)
    async def mass_ban(
            self,
            interaction: discord.Interaction,
            message_start: discord.Message,
            message_end: discord.Message,
            reason: str = "Mass ban with message timestamp."
    ):
        """Bans  member from the guild if they joined at specific time.

        This is the same thing as ban_timestamp except that instead of manualy passing
        timestamps you pass start and end message from which the timestamps will be taken
        """
        await self._mass_ban_timestamp_helper(interaction, message_start.created_at, message_end.created_at, reason)

    # @app_commands.command()
    # @app_commands.checks.bot_has_permissions(administrator=True)
    # @app_commands.checks.has_permissions(administrator=True)
    # @app_commands.checks.cooldown(1, 120)
    # @app_commands.check(check_if_it_is_tortoise_guild)
    async def ban_timestamp(
            self,
            interaction: discord.Interaction,
            timestamp_start: DatetimeConverter,
            timestamp_end: DatetimeConverter,
            reason: str = "Mass ban with timestamp."
    ):
        """Bans  member from the guild if they joined at specific time.

        Both arguments need to be in this specific format:
        %Y-%m-%d %H:%M

        Example:
        t.ban_timestamp "2020-09-15 13:00" "2020-10-15 13:00"

        All values need to be padded with 0.
        Timezones are not accounted for.
        """
        await self._mass_ban_timestamp_helper(interaction, timestamp_start, timestamp_end, reason)

    async def _mass_ban_timestamp_helper(self, interaction, timestamp_start: datetime, timestamp_end: datetime, reason: str):
        members_to_ban = []

        for member in self.tortoise_guild.members:
            if member.joined_at is None:
                continue

            if timestamp_start < member.joined_at < timestamp_end:
                members_to_ban.append(member)

        if not members_to_ban:
            return await interaction.response.send_message(embed=failure("Could not find any members, aborting.."), ephemeral=True)

        members_to_ban.sort(key=lambda m: m.joined_at)

        reaction_msg = await interaction.channel.send(
            embed=warning(
                f"This will ban {len(members_to_ban)} members, "
                f"first one being {members_to_ban[0]} and last one being {members_to_ban[-1]}.\n"
                f"Are you sure you want to continue?"
            )
        )

        confirmation = await ConfirmationMessage.create_instance(self.bot, reaction_msg, interaction.user)
        if confirmation:

            one_tenth = len(members_to_ban) // 10
            notify_interval = one_tenth if one_tenth > 50 else 50

            await interaction.followup.send(
                embed=info(
                    f"Starting the ban process, please be patient.\n"
                    f"You will be notified for each {notify_interval} banned members.",
                    interaction.user
                )
            )
            logger.info(f"{interaction.user} is timestamp banning: {', '.join(str(member.id) for member in members_to_ban)}")

            for count, member in enumerate(members_to_ban):
                if count != 0 and count % notify_interval == 0:
                    await interaction.followup.send(embed=info(f"Banned {count} members..", interaction.user))

                await interaction.guild.ban(member, reason=reason)

            message = f"Successfully mass banned {len(members_to_ban)} members!"
            await interaction.followup.send(embed=success(message))
            await self.deterrence_log_channel.send(embed=authored(message, author=interaction.user))
        else:
            await interaction.followup.send(embed=info("Aborting mass ban.", interaction.client.user))


    @app_commands.command()
    @app_commands.checks.bot_has_permissions(ban_members=True)
    @app_commands.check(check_if_tortoise_staff)
    @app_commands.checks.cooldown(1, 120)
    async def ban(self, interaction: discord.Interaction, user: discord.Member, reason: str = "Reason not stated."):
        """Bans  member from the guild."""
        await interaction.response.defer()
        await self._ban_helper(interaction, user, reason)
        await interaction.followup.send(embed=success(f"{user} successfully banned."), ephemeral=True)

    async def _ban_helper(
            self,
            interaction: discord.Interaction,
            user: Union[GetFetchUser, User, Member],
            reason: str,
            send_dm: bool = True,
            log_deterrence: bool = True,
    ):
        embed = infraction_embed(interaction, user, constants.Infraction.ban, reason)

        if log_deterrence:
            await self.deterrence_log_channel.send(embed=embed)

        if send_dm:
            embed = infraction_embed(interaction, user, constants.Infraction.ban, reason, True, True)
            try:
                await user.send(embed=embed)
            except discord.Forbidden:
                pass
            except discord.HTTPException:
                pass

        await interaction.guild.ban(user, reason=reason)

    @app_commands.command()
    @app_commands.checks.bot_has_permissions(ban_members=True)
    @app_commands.check(check_if_tortoise_staff)
    async def unban(self, interaction: discord.Interaction, user_id: int, reason: str = "Reason not stated."):
        """Unbans  member from the guild."""
        await interaction.response.defer()
        user = await self.bot.fetch_user(user_id)
        await interaction.guild.unban(user=user, reason=reason)
        await interaction.followup.send(embed=success(f"{user} successfully unbanned."), ephemeral=True)


    @app_commands.command(name="warn")
    @app_commands.checks.bot_has_permissions(manage_messages=True)
    @app_commands.check(check_if_tortoise_staff)
    async def warn(self, interaction: discord.Interaction, member: discord.Member, reason: str):
        """
        Warns a member.
        Reason length is maximum of 200 characters.
        """
        if len(reason) > 200:
            await interaction.response.send_message(
                embed=failure("Please shorten the reason to 200 characters."),
                ephemeral=True
            )
            return

        if member == interaction.user or member.bot:
            await interaction.response.send_message(
                embed=failure("Invalid member."),
                ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        try:
            dm_embed = infraction_embed(interaction, member, constants.Infraction.warning, reason, True)
            dm_embed.set_footer(
                text="If this behavior continues, moderators may take appropriate action."
            )
            await member.send(embed=dm_embed)
        except discord.Forbidden:
            pass

        # try:
        #     await self.bot.api_client.add_member_warning(interaction.user.id, member.id, reason)
        # except Exception as e:
        #     msg = "Could not apply warning, problem with API."
        #     logger.info(f"{msg} {e}")
        #     await interaction.response.send_message(embed=failure(f"{msg}\nInfraction member should not think he got away."), ephemeral=True)
        # else:

        await self.deterrence_log_channel.send(
            embed=infraction_embed(interaction, member, constants.Infraction.warning, reason, False)
        )

        await interaction.followup.send(
            embed=success("Warning successfully applied."),
            ephemeral=True
        )

    # @app_commands.command()
    # @app_commands.checks.has_permissions(manage_messages=True)
    # @app_commands.check(check_if_it_is_tortoise_guild)
    async def show_warnings(self, interaction: discord.Interaction, member: discord.Member):
        """Shows all warnings of member."""
        warnings = await self.bot.api_client.get_member_warnings(member.id)

        if not warnings:
            await interaction.response.send_message(embed=info("No warnings.", interaction.client.user), ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        for count, sub_dict in enumerate(warnings):
            formatted_warnings = [f"{key}:{value}" for key, value in sub_dict.items()]
            warnings_msg = "\n".join(formatted_warnings)
            warnings_msg = warnings_msg[:1900]

            warnings_embed = thumbnail(warnings_msg, member, f"Warning #{count+1}")
            await interaction.followup.send(embed=warnings_embed, ephemeral=True)

    # @app_commands.command()
    # @app_commands.check(check_if_it_is_tortoise_guild)
    async def warning_count(self, interaction: discord.Interaction, member: discord.Member):
        """Shows count of all warnings from member."""
        count = await self.bot.api_client.get_member_warnings_count(member.id)
        warnings_embed = thumbnail(f"Warnings: {count}", member, "Warning count")
        await interaction.response.send_message(embed=warnings_embed, ephemeral=True)


    @app_commands.command()
    @app_commands.checks.bot_has_permissions(manage_messages=True)
    @app_commands.check(check_if_tortoise_staff)
    @app_commands.checks.cooldown(3, 60)
    async def clear(self, interaction: discord.Interaction, amount: int, member: discord.Member = None):
        """
        Clears last X amount of messages.
        If member is passed it will clear last X messages from that member.
        """
        if amount < 1:
            await interaction.response.send_message(
                embed=failure("Amount should be greater than 1"),
                ephemeral=True
            )
            return
        if amount > 20:
            await interaction.response.send_message(
                embed=failure("Amount should be less than 20"),
                ephemeral=True
            )
            return

        def check(msg):
            return member is None or msg.author == member

        deleted = await interaction.channel.purge(limit=amount, check=check)

        await interaction.response.send_message(
            embed=success(f"Cleared {len(deleted)} messages."),
            ephemeral=True
        )


    @app_commands.command()
    @app_commands.checks.bot_has_permissions(moderate_members=True)
    @app_commands.checks.has_permissions(moderate_members=True)
    @app_commands.check(check_if_tortoise_staff)
    async def timeout(
            self,
            interaction: discord.Interaction,
            member: discord.Member,
            minutes: int,
            reason: str = "No reason stated."
    ):
        """Timeouts a member."""
        await interaction.response.defer()

        deterrence_embed = infraction_embed(
            interaction,
            member,
            constants.Infraction.timeout,
            reason
        )
        await self.deterrence_log_channel.send(embed=deterrence_embed)

        dm_embed = infraction_embed(
            interaction,
            member,
            constants.Infraction.timeout,
            reason,
            True
        )
        dm_embed.set_footer(text="If this happened by a mistake raise a Mod Mail.")

        try:
            await member.send(embed=dm_embed)
        except discord.Forbidden:
            pass
        except discord.HTTPException:
            pass

        until = discord.utils.utcnow() + timedelta(minutes=minutes)
        await member.timeout(until, reason=reason)

        await interaction.followup.send(
            embed=success(f"{member} successfully timed out.", interaction.guild.me),
            ephemeral=True
        )
        # await self.bot.api_client.add_member_warning(interaction.user.id, member.id, f"Timeout: {reason}")


    @app_commands.command(name="dm_members")
    @app_commands.checks.cooldown(1, 900)
    @app_commands.checks.has_permissions(administrator=True)
    async def dm_members(self, interaction: discord.Interaction, role: discord.Role):
        """Opens a modal to DM all members of a role"""
        await interaction.response.send_modal(DMModal(role, interaction))


    @app_commands.command(name="send")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def send(self, interaction: discord.Interaction, message: str, channel: discord.TextChannel = None):
        """Send message to channel"""
        await interaction.response.defer()
        if channel is None:
            channel = interaction.channel

        await channel.send(message)
        await interaction.followup.send(embed=success("Sent."), ephemeral=True)


async def setup(bot):
    await bot.add_cog(Moderation(bot))
