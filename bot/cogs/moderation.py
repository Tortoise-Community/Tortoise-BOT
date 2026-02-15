import asyncio
import copy
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

        dm_embed = deterrence_embed
        dm_embed.add_field(
            name="Comment",
            value="Rethink what you did before joining back."
        )
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
        deterrence_embed = infraction_embed(interaction, user, constants.Infraction.ban, reason)

        if send_dm:
            dm_embed = copy.copy(deterrence_embed)
            dm_embed.add_field(name="Repeal", value="If this happened by a mistake join our Appeal Server")
            dm_embed.add_field(name="Ban Appeal Server", value=f"[Click Here to Join]({constants.appeal_server_link})")
            try:
                await user.send(embed=dm_embed)
            except discord.Forbidden:
                pass

        await interaction.guild.ban(user, reason=reason)

        if log_deterrence:
            await self.deterrence_log_channel.send(embed=deterrence_embed)

    @app_commands.command()
    @app_commands.checks.bot_has_permissions(ban_members=True)
    @app_commands.check(check_if_tortoise_staff)
    async def unban(self, interaction: discord.Interaction, user_id: int, reason: str = "Reason not stated."):
        """Unbans  member from the guild."""
        await interaction.response.defer()
        user = await self.bot.fetch_user(user_id)
        await interaction.guild.unban(user=user, reason=reason)
        await interaction.followup.send(embed=success(f"{user} successfully unbanned."), ephemeral=True)


    # @app_commands.command(name="warn")
    # @app_commands.checks.bot_has_permissions(manage_messages=True)
    # @app_commands.checks.has_permissions(manage_messages=True)
    # @app_commands.check(check_if_it_is_tortoise_guild)
    async def warn(self, interaction: discord.Interaction, member: discord.Member, reason: str):
        """
        Warns a member.
        Reason length is maximum of 200 characters.
        """
        if len(reason) > 200:
            await interaction.response.send_message(embed=failure("Please shorten the reason to 200 characters."), ephemeral=True)
            return

        embed = infraction_embed(interaction, member, constants.Infraction.warning, reason)
        embed.add_field(
            name="**NOTE**",
            value=(
                "If you are planning to repeat this again, "
                "the mods may administer punishment for the action."
            )
        )

        try:
            await self.bot.api_client.add_member_warning(interaction.user.id, member.id, reason)
        except Exception as e:
            msg = "Could not apply warning, problem with API."
            logger.info(f"{msg} {e}")
            await interaction.response.send_message(embed=failure(f"{msg}\nInfraction member should not think he got away."), ephemeral=True)
        else:
            await self.deterrence_log_channel.send(f"{member.mention}", delete_after=0.5)
            await self.deterrence_log_channel.send(embed=embed)
            await interaction.response.send_message(embed=success("Warning successfully applied.", interaction.client.user), ephemeral=True)

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
    @app_commands.checks.bot_has_permissions(manage_roles=True)
    @app_commands.checks.has_permissions(manage_roles=True, manage_messages=True)
    @app_commands.check(check_if_tortoise_staff)
    async def promote(self, interaction: discord.Interaction, member: discord.Member, role: discord.Role):
        """Promote member to role."""
        await interaction.response.defer()
        if role >= interaction.user.top_role:
            await interaction.followup.send(embed=failure("Role needs to be below you in hierarchy."), ephemeral=True)
            return
        elif role in member.roles:
            await interaction.followup.send(embed=failure(f"{member.mention} already has role {role.mention}!"), ephemeral=True)
            return

        await member.add_roles(role)

        dm_embed = info(
            (
                f"You’ve been promoted to **{role.name}** role.\n"
                f"Thanks for staying active and contributing to the server — keep it up."
            ),
            interaction.client.user,
            "Congratulations!",
        )

        dm_embed.set_footer(text="Tortoise Programming Community")
        await member.send(embed=dm_embed)
        await interaction.followup.send(embed=success(f"{member.mention} is promoted to {role.mention}", interaction.client.user), ephemeral=True)


    @app_commands.command()
    @app_commands.checks.bot_has_permissions(manage_messages=True)
    @app_commands.checks.has_permissions(manage_messages=True)
    @app_commands.checks.cooldown(1, 60)
    async def clear(self, interaction: discord.Interaction, amount: int, member: discord.Member = None):
        """
        Clears last X amount of messages.
        If member is passed it will clear last X messages from that member.
        """
        await interaction.response.send_message(
            embed=success(f"Clearing {amount} messages..."),
            ephemeral=True
        )
        await asyncio.sleep(3)
        def check(msg):
            return member is None or msg.author == member
        await interaction.channel.purge(limit=amount + 1, check=check)


    @app_commands.command()
    @app_commands.checks.bot_has_permissions(moderate_members=True)
    @app_commands.checks.has_permissions(moderate_members=True)
    @app_commands.check(check_if_tortoise_staff)
    async def timeout(self, interaction: discord.Interaction, member: discord.Member, minutes: int, reason: str = "No reason stated."):
        """Mutes the member."""
        await interaction.response.defer()
        until = discord.utils.utcnow() + timedelta(minutes=minutes)
        await member.timeout(until, reason=reason)
        await interaction.followup.send(embed=success(f"{member} successfully timed out."), ephemeral=True)
        # await self.bot.api_client.add_member_warning(interaction.user.id, member.id, f"Timeout: {reason}")


    @app_commands.command(name="dm_members")
    @app_commands.checks.cooldown(1, 900)
    @app_commands.checks.has_permissions(administrator=True)
    async def dm_members(self, interaction: discord.Interaction, role: discord.Role, message: str):
        """
        DMs all member that have a certain role.
        Failed members are printed to log.
        """
        await interaction.response.defer()
        members = (member for member in role.members if not member.bot)
        failed = []
        count = 0

        for member in members:
            dm_embed = discord.Embed(
                title=f"Message for role {role}",
                description=message,
                color=role.color
            )
            dm_embed.set_author(name=interaction.guild.name, icon_url=interaction.guild.icon.url)

            try:
                await member.send(embed=dm_embed)
            except discord.HTTPException:
                failed.append(str(member))
            else:
                count += 1

        await interaction.followup.send(embed=success(f"Successfully notified {count} users.", interaction.client.user), ephemeral=True)

        if failed:
            logger.info(f"dm_unverified called but failed to dm: {failed}")

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
