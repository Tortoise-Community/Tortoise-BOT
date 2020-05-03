import logging
import asyncio

import discord
from discord.ext import commands

from bot import constants
from bot.cogs.utils.embed_handler import success, failure, info, infraction_embed
from bot.cogs.utils.checks import check_if_it_is_tortoise_guild


logger = logging.getLogger(__name__)


class Admins(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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
        deterrence_log_channel = self.bot.get_channel(constants.deterrence_log_channel_id)
        await deterrence_log_channel.send(embed=deterrence_embed)

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
    async def ban(self, ctx, member: discord.Member, *, reason="Reason not stated."):
        """
        Bans  member from the guild.

        """
        await member.ban(reason=reason)
        await ctx.send(embed=success(f"{member.name} successfully banned."), delete_after=5)

        deterrence_embed = infraction_embed(ctx, member, constants.Infraction.kick, reason)
        deterrence_log_channel = self.bot.get_channel(constants.deterrence_log_channel_id)
        await deterrence_log_channel.send(embed=deterrence_embed)

        dm_embed = deterrence_embed
        dm_embed.add_field(
            name="Repeal",
            value="If this happened by a mistake contact moderators."
        )

        await member.send(embed=dm_embed)

    @commands.command()
    @commands.bot_has_permissions(manage_messages=True)
    @commands.has_permissions(manage_messages=True)
    @commands.check(check_if_it_is_tortoise_guild)
    async def warn(self, ctx, member: discord.Member, *, reason):
        """
        Warns a member.

        """
        deterrence_log_channel = self.bot.get_channel(constants.deterrence_log_channel_id)

        embed = infraction_embed(ctx, member, constants.Infraction.warning, reason)
        embed.add_field(
            name="**NOTE**",
            value=(
                "If you are planning to repeat this again, "
                "the mods may administer punishment for the action."
            )
        )

        await deterrence_log_channel.send(f"{member.mention}", delete_after=0.5)
        await deterrence_log_channel.send(embed=embed)

        await asyncio.sleep(5)
        await ctx.message.delete()

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
        Mutes the member by giving him the Mute role.

        """
        muted_role = ctx.guild.get_role(constants.muted_role_id)
        await member.add_roles(muted_role, reason=reason)
        await ctx.send(embed=success(f"{member} successfully muted."), delete_after=5)

    @commands.command()
    @commands.cooldown(1, 300, commands.BucketType.guild)
    @commands.has_permissions(administrator=True)
    @commands.check(check_if_it_is_tortoise_guild)
    async def dm_unverified(self, ctx):
        """
        Dms all unverified members reminder that they need to verify.
        Failed members are printed to log.

        """
        unverified_role = ctx.guild.get_role(constants.unverified_role_id)
        unverified_members = (member for member in unverified_role.members if member.status == discord.Status.online)
        failed = []
        count = 0

        for member in unverified_members:
            msg = (
                f"Hey {member.mention}!\n"
                f"You've been in our guild **{ctx.guild.name}** for some time..\n"
                f"We noticed you still didn't verify so please go to our channel "
                f"{constants.verification_url} and verify."
            )

            try:
                await member.send(msg)
            except discord.Forbidden:
                failed.append(str(member))
            else:
                count += 1

        await ctx.send(embed=success(f"Successfully notified {count} users.", ctx.me))

        if failed:
            logger.info(f"dm_unverified called but failed to dm: {failed}")

    @commands.command()
    @commands.cooldown(1, 300, commands.BucketType.guild)
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
            dm_embed = discord.Embed(title=f"Message for role {role}",
                                     description=message,
                                     color=role.color)
            dm_embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon_url)

            try:
                await member.send(embed=dm_embed)
            except discord.Forbidden:
                failed.append(str(member))
            else:
                count += 1

        await ctx.send(embed=success(f"Successfully notified {count} users.", ctx.me))

        if failed:
            logger.info(f"dm_unverified called but failed to dm: {failed}")

    @commands.command()
    async def paste(self, ctx):
        await ctx.send(f"{constants.tortoise_paste_service_link}")


def setup(bot):
    bot.add_cog(Admins(bot))
