import logging
import asyncio
from typing import Union
from datetime import datetime

import discord
from discord.ext import commands, tasks

from bot import constants
from bot.cogs.utils.checks import check_if_it_is_tortoise_guild
from bot.cogs.utils.embed_handler import success, failure, info, infraction_embed, thumbnail


logger = logging.getLogger(__name__)


class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.tortoise_guild = bot.get_guild(constants.tortoise_guild_id)
        self.muted_role = self.tortoise_guild.get_role(constants.muted_role_id)
        self.verified_role = self.tortoise_guild.get_role(constants.verified_role_id)
        self.unverified_role = self.tortoise_guild.get_role(constants.unverified_role_id)
        self.deterrence_log_channel = bot.get_channel(constants.deterrence_log_channel_id)

    @commands.command()
    @commands.bot_has_permissions(kick_members=True)
    @commands.has_permissions(kick_members=True)
    @commands.check(check_if_it_is_tortoise_guild)
    async def kick(self, ctx, member: discord.Member, *, reason="No specific reason"):
        """
        Kicks  member from the guild.

        """
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
    @commands.bot_has_permissions(ban_members=True)
    @commands.has_permissions(ban_members=True)
    @commands.check(check_if_it_is_tortoise_guild)
    async def ban(self, ctx, member: Union[discord.Member, discord.abc.Snowflake], *, reason="Reason not stated."):
        """Bans  member from the guild."""
        await ctx.guild.ban(reason=reason)
        await ctx.send(embed=success(f"{member} successfully banned."), delete_after=5)

        deterrence_embed = infraction_embed(ctx, member, constants.Infraction.ban, reason)
        await self.deterrence_log_channel.send(embed=deterrence_embed)

        dm_embed = deterrence_embed
        dm_embed.add_field(
            name="Repeal",
            value="If this happened by a mistake contact moderators."
        )

        await member.send(embed=dm_embed)

    @commands.command()
    @commands.bot_has_permissions(ban_members=True)
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx, user: discord.abc.Snowflake, *, reason="Reason not stated."):
        """Unbans  member from the guild."""
        await ctx.guild.unban(reason=reason)
        await ctx.send(embed=success(f"{user} successfully unbanned."), delete_after=5)

    @commands.command(aliases=["warning"])
    @commands.bot_has_permissions(manage_messages=True)
    @commands.has_permissions(manage_messages=True)
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
    @commands.has_permissions(manage_messages=True)
    @commands.check(check_if_it_is_tortoise_guild)
    async def show_warnings(self, ctx, member: discord.Member):
        """
        Shows all warnings of member.

        """
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

    @commands.command(aliases=["warnings_count"])
    @commands.has_permissions(manage_messages=True)
    @commands.check(check_if_it_is_tortoise_guild)
    async def warning_count(self, ctx, member: discord.Member):
        """
        Shows count of all warnings from member.

        """
        count = await self.bot.api_client.get_member_warnings_count(member.id)
        warnings_embed = thumbnail(f"Warnings: {count}", member, "Warning count")
        await ctx.send(embed=warnings_embed)

    @commands.command()
    @commands.bot_has_permissions(manage_roles=True)
    @commands.has_permissions(manage_roles=True, manage_messages=True)
    @commands.check(check_if_it_is_tortoise_guild)
    async def promote(self, ctx, member: discord.Member, role: discord.Role):
        """
        Promote member to role.

        """
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
    @commands.bot_has_permissions(manage_messages=True)
    @commands.has_permissions(manage_messages=True)
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
    @commands.bot_has_permissions(manage_roles=True)
    @commands.has_permissions(manage_messages=True)
    @commands.check(check_if_it_is_tortoise_guild)
    async def mute(self, ctx, member: discord.Member, *, reason="No reason stated."):
        """
        Mutes the member.
        """
        if self.muted_role in member.roles:
            await ctx.send(embed=failure("Cannot mute as member is already muted."))
            return

        reason = f"Muting member. {reason}"

        await member.add_roles(self.muted_role, reason=reason)
        await member.remove_roles(self.verified_role, reason=reason)

        await ctx.send(embed=success(f"{member} successfully muted."), delete_after=5)

        await self.bot.api_client.add_member_warning(ctx.author.id, member.id, reason)

    @commands.command()
    @commands.bot_has_permissions(manage_roles=True)
    @commands.has_permissions(manage_messages=True)
    @commands.check(check_if_it_is_tortoise_guild)
    async def unmute(self, ctx, member: discord.Member):
        """
        Unmutes the member.
        """
        if self.muted_role not in member.roles:
            await ctx.send(embed=failure("Cannot unmute as member is not muted."))
            return

        reason = f"Unmuted by {ctx.author.id}"

        await member.remove_roles(self.muted_role, reason=reason)
        await member.add_roles(self.verified_role, reason=reason)

        await ctx.send(embed=success(f"{member} successfully unmuted."), delete_after=5)

    @tasks.loop(hours=24)
    async def scheduled_dm_unverified(self):
        """
        Dms all unverified members reminder that they need to verify.
        Failed members are printed to log.
        """
        # TODO
        return
        """
        date_joined = datetime.strptime(user['join_date'].split('T')[0], '%Y-%m-%d')
        AttributeError: 'NoneType' object has no attribute 'split'
        """
        members = await self.bot.api_client.get_all_members()
        failed = []
        count = 0

        # TODO filter is only temporary until API endpoint added
        for user in filter(lambda m: not m['verified'], members):
            date_joined = datetime.strptime(user['join_date'].split('T')[0], '%Y-%m-%d')
            days_since_joined = (datetime.today() - date_joined).days

            member = self.tortoise_guild.get_member(user['user_id'])

            if not user['member']:
                # Column is not deleted if member has left the guild, we just change field 'member' to False
                # Also, VERY IMPORTANT, we have members in database from previous system that didn't verify but were
                # let of the hook! Do not kick!
                continue
            elif member is None:
                # If bot was offline for a moment and leave event was not registered
                logger.warning(f"Member {member} found in database as member but not found in guild.")
                continue

            if days_since_joined % 5 == 0:
                msg = (
                    f"Hey {member.mention}!\n"
                    f"You've been in our guild **{self.tortoise_guild.name}** for the past {days_since_joined} days.\n"
                    f"We noticed you still haven't verified so please go to "
                    f"{constants.verification_url} and verify.\n\n"
                )

                try:
                    await member.send(msg)
                except discord.Forbidden:
                    failed.append(member.name)
                else:
                    count += 1

        logger.info(f"Successfully messaged {count} unverified users.")
        if failed:
            logger.info(f"dm_unverified called but failed to dm: {failed}")

    @commands.command(aliases=["dm"])
    @commands.cooldown(1, 900, commands.BucketType.guild)
    @commands.has_permissions(administrator=True)
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

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def send(self, ctx, channel: discord.TextChannel = None, *, message: str):
        """Send message to channel"""
        if channel is None:
            channel = ctx.channel

        await channel.send(message)


def setup(bot):
    bot.add_cog(Moderation(bot))
