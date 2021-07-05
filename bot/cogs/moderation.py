import logging
import asyncio
from typing import Union

import discord
from discord import User, Member
from discord.ext import commands

from bot import constants
from bot.utils.message_handler import ConfirmationMessage
from bot.utils.checks import check_if_it_is_tortoise_guild
from bot.utils.converters import GetFetchUser, DatetimeConverter
from bot.utils.embed_handler import success, warning, failure, info, infraction_embed, thumbnail


logger = logging.getLogger(__name__)


class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.tortoise_guild = bot.get_guild(constants.tortoise_guild_id)
        self.muted_role = self.tortoise_guild.get_role(constants.muted_role_id)
        self.verified_role = self.tortoise_guild.get_role(constants.verified_role_id)
        self.deterrence_log_channel = bot.get_channel(constants.deterrence_log_channel_id)

    @commands.command()
    @commands.bot_has_guild_permissions(kick_members=True)
    @commands.has_guild_permissions(kick_members=True)
    @commands.check(check_if_it_is_tortoise_guild)
    async def kick(self, ctx, member: discord.Member, *, reason="No specific reason"):
        """Kicks  member from the guild."""
        await member.kick(reason=reason)
        await ctx.send(embed=success(f"{member.name} successfully kicked."), delete_after=5)

        deterrence_embed = infraction_embed(ctx, member, constants.Infraction.kick, reason)
        await self.deterrence_log_channel.send(embed=deterrence_embed)

        dm_embed = deterrence_embed
        dm_embed.add_field(
            name="Repeal",
            value="If this happened by a mistake contact moderators."
        )

        await member.send(embed=dm_embed)

    @commands.command()
    @commands.bot_has_guild_permissions(administrator=True)
    @commands.has_guild_permissions(administrator=True)
    @commands.check(check_if_it_is_tortoise_guild)
    async def ban_timestamp(
            self,
            ctx,
            timestamp_start: DatetimeConverter,
            timestamp_end: DatetimeConverter,
            *,
            reason="Mass ban with timestamp."
    ):
        """Bans  member from the guild if he joined at specific time.

        Both arguments need to be in this specific format:
        %Y-%m-%d %H:%M

        Example:
        t.ban_timestamp "2020-09-15 13:00" "2020-10-15 13:00"

        All values need to be padded with 0.
        Timezones are not accounted for.
        """
        members_to_ban = []

        for member in self.tortoise_guild.members:
            if member.joined_at is None:
                continue

            if timestamp_start < member.joined_at < timestamp_end:
                members_to_ban.append(member)

        if not members_to_ban:
            return await ctx.send(embed=failure("Could not find any members, aborting.."))

        reaction_msg = await ctx.send(
            embed=warning(
                f"This will ban {len(members_to_ban)} members, "
                f"first one being {members_to_ban[0]} and last one being {members_to_ban[-1]}.\n"
                f"Are you sure you want to continue?"
            )
        )

        confirmation = await ConfirmationMessage.create_instance(self.bot, reaction_msg, ctx.author)
        if confirmation:
            logger.info(f"{ctx.author} is timestamp banning: {', '.join(member.id for member in members_to_ban)}")

            for member in members_to_ban:
                await self._ban_helper(ctx, member, reason)
            await ctx.send(embed=success(f"Successfully mass banned {len(members_to_ban)} members!"))
        else:
            await ctx.send(embed=info("Aborting mass ban.", ctx.me))

    @commands.command()
    @commands.bot_has_guild_permissions(ban_members=True)
    @commands.has_guild_permissions(ban_members=True)
    @commands.check(check_if_it_is_tortoise_guild)
    async def ban(self, ctx, user: GetFetchUser, *, reason="Reason not stated."):
        """Bans  member from the guild."""
        await self._ban_helper(ctx, user, reason)
        await ctx.send(embed=success(f"{user} successfully banned."), delete_after=10)

    async def _ban_helper(self, ctx: commands.Context, member: Union[GetFetchUser, User, Member], reason: str):
        await ctx.guild.ban(member, reason=reason)
        deterrence_embed = infraction_embed(ctx, member, constants.Infraction.ban, reason)
        await self.deterrence_log_channel.send(embed=deterrence_embed)
        dm_embed = deterrence_embed
        dm_embed.add_field(
            name="Repeal",
            value="If this happened by a mistake contact moderators."
        )
        try:
            await member.send(embed=dm_embed)
        except discord.Forbidden:
            pass  # ignore closed DMs

    @commands.command()
    @commands.bot_has_guild_permissions(ban_members=True)
    @commands.has_guild_permissions(ban_members=True)
    async def unban(self, ctx, user: GetFetchUser, *, reason="Reason not stated."):
        """Unbans  member from the guild."""
        await ctx.guild.unban(user=user, reason=reason)
        await ctx.send(embed=success(f"{user} successfully unbanned."), delete_after=5)

    @commands.command(aliases=["warning"])
    @commands.bot_has_guild_permissions(manage_messages=True)
    @commands.has_guild_permissions(manage_messages=True)
    @commands.check(check_if_it_is_tortoise_guild)
    async def warn(self, ctx, member: discord.Member, *, reason):
        """
        Warns a member.
        Reason length is maximum of 200 characters.
        """
        if len(reason) > 200:
            await ctx.send(embed=failure("Please shorten the reason to 200 characters."), delete_after=3)
            return

        embed = infraction_embed(ctx, member, constants.Infraction.warning, reason)
        embed.add_field(
            name="**NOTE**",
            value=(
                "If you are planning to repeat this again, "
                "the mods may administer punishment for the action."
            )
        )

        try:
            await self.bot.api_client.add_member_warning(ctx.author.id, member.id, reason)
        except Exception as e:
            msg = "Could not apply warning, problem with API."
            logger.info(f"{msg} {e}")
            await ctx.send(embed=failure(f"{msg}\nInfraction member should not think he got away."))
        else:
            await self.deterrence_log_channel.send(f"{member.mention}", delete_after=0.5)
            await self.deterrence_log_channel.send(embed=embed)
            await ctx.send(embed=success("Warning successfully applied.", ctx.me), delete_after=5)
            await asyncio.sleep(5)
            await ctx.message.delete()

    @commands.command()
    @commands.has_guild_permissions(manage_messages=True)
    @commands.check(check_if_it_is_tortoise_guild)
    async def show_warnings(self, ctx, member: discord.Member):
        """Shows all warnings of member."""
        warnings = await self.bot.api_client.get_member_warnings(member.id)

        if not warnings:
            await ctx.send(embed=info("No warnings.", ctx.me))

        for count, sub_dict in enumerate(warnings):
            formatted_warnings = [f"{key}:{value}" for key, value in sub_dict.items()]

            warnings_msg = "\n".join(formatted_warnings)
            # TODO temporal quick fix for possible too long message, to fix when embed navigation is done
            warnings_msg = warnings_msg[:1900]

            warnings_embed = thumbnail(warnings_msg, member, f"Warning #{count+1}")
            await ctx.send(embed=warnings_embed)

    @commands.command()
    @commands.check(check_if_it_is_tortoise_guild)
    async def warning_count(self, ctx, member: discord.Member):
        """Shows count of all warnings from member."""
        count = await self.bot.api_client.get_member_warnings_count(member.id)
        warnings_embed = thumbnail(f"Warnings: {count}", member, "Warning count")
        await ctx.send(embed=warnings_embed)

    @commands.command()
    @commands.bot_has_guild_permissions(manage_roles=True)
    @commands.has_guild_permissions(manage_roles=True, manage_messages=True)
    @commands.check(check_if_it_is_tortoise_guild)
    async def promote(self, ctx, member: discord.Member, role: discord.Role):
        """Promote member to role."""
        if role >= ctx.author.top_role:
            await ctx.send(embed=failure("Role needs to be below you in hierarchy."))
            return
        elif role in member.roles:
            await ctx.send(embed=failure(f"{member.mention} already has role {role.mention}!"))
            return

        await member.add_roles(role)

        await ctx.send(embed=success(f"{member.mention} is promoted to {role.mention}", ctx.me), delete_after=5)

        dm_embed = info(
            (
                f"You are now promoted to role **{role.name}** in our community.\n"
                f"`'With great power comes great responsibility'`\n"
                f"Be active and keep the community safe."
            ),
            ctx.me,
            "Congratulations!"
        )

        dm_embed.set_footer(text="Tortoise community")
        await member.send(embed=dm_embed)

    @commands.command()
    @commands.bot_has_guild_permissions(manage_messages=True)
    @commands.has_guild_permissions(manage_messages=True)
    @commands.guild_only()
    async def clear(self, ctx, amount: int, member: discord.Member = None):
        """
        Clears last X amount of messages.
        If member is passed it will clear last X messages from that member.
        """
        def check(msg):
            return member is None or msg.author == member

        await ctx.channel.purge(limit=amount + 1, check=check)
        await ctx.send(embed=success(f"{amount} messages cleared."), delete_after=3)

    @commands.command()
    @commands.bot_has_guild_permissions(manage_roles=True)
    @commands.has_guild_permissions(manage_messages=True)
    @commands.check(check_if_it_is_tortoise_guild)
    async def mute(self, ctx, member: discord.Member, *, reason="No reason stated."):
        """Mutes the member."""
        if self.muted_role in member.roles:
            await ctx.send(embed=failure("Cannot mute as member is already muted."))
            return

        reason = f"Muting member. {reason}"
        await member.add_roles(self.muted_role, reason=reason)
        await member.remove_roles(self.verified_role, reason=reason)
        await ctx.send(embed=success(f"{member} successfully muted."), delete_after=5)
        await self.bot.api_client.add_member_warning(ctx.author.id, member.id, reason)

    @commands.command()
    @commands.bot_has_guild_permissions(manage_roles=True)
    @commands.has_guild_permissions(manage_messages=True)
    @commands.check(check_if_it_is_tortoise_guild)
    async def unmute(self, ctx, member: discord.Member):
        """Unmutes the member."""
        if self.muted_role not in member.roles:
            await ctx.send(embed=failure("Cannot unmute as member is not muted."))
            return

        reason = f"Unmuted by {ctx.author.id}"

        await member.remove_roles(self.muted_role, reason=reason)
        await member.add_roles(self.verified_role, reason=reason)

        await ctx.send(embed=success(f"{member} successfully unmuted."), delete_after=5)

    @commands.command(aliases=["dm"])
    @commands.cooldown(1, 900, commands.BucketType.guild)
    @commands.has_guild_permissions(administrator=True)
    async def dm_members(self, ctx, role: discord.Role, *, message: str):
        """
        DMs all member that have a certain role.
        Failed members are printed to log.
        """
        members = (member for member in role.members if not member.bot)
        failed = []
        count = 0

        for member in members:
            dm_embed = discord.Embed(
                title=f"Message for role {role}",
                description=message,
                color=role.color
            )
            dm_embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon_url)

            try:
                await member.send(embed=dm_embed)
            except discord.HTTPException:
                failed.append(str(member))
            else:
                count += 1

        await ctx.send(embed=success(f"Successfully notified {count} users.", ctx.me))

        if failed:
            logger.info(f"dm_unverified called but failed to dm: {failed}")

    @commands.command(aliases=["message"])
    @commands.has_guild_permissions(manage_messages=True)
    async def send(self, ctx, channel: discord.TextChannel = None, *, message: str):
        """Send message to channel"""
        if channel is None:
            channel = ctx.channel

        await channel.send(message)


def setup(bot):
    bot.add_cog(Moderation(bot))
