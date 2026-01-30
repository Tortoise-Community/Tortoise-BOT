from datetime import time as dtime, timezone

import discord
import asyncio
from discord import Invite, Member
from discord.ext import commands, tasks

from bot.utils import invite_help, embed_handler
from bot import constants


class InviteTracker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.guild = None
        self.tracker = None
        self.log_channel = None
        self.welcome_role = None
        self.general_channel = None
        self.joins_today = 0
        self.leaves_today = 0

    @commands.Cog.listener()
    async def on_ready(self):
        self.guild = self.bot.get_guild(constants.tortoise_guild_id)
        self.tracker = invite_help.GuildInviteTracker(self.guild)
        self.log_channel = self.bot.get_channel(constants.system_log_channel_id)
        self.bot.loop.create_task(self.tracker.refresh_invite_cache())
        self.welcome_role = self.guild.get_role(constants.new_member_role)
        self.general_channel = self.guild.get_channel(constants.general_channel_id)
        self.daily_retention_report.start()

    @commands.Cog.listener()
    async def on_invite_create(self, invite: Invite):
        await self.tracker.add_new_invite(invite)

    @commands.Cog.listener()
    async def on_invite_delete(self, invite: Invite):
        await self.tracker.remove_invite(invite)

    @staticmethod
    async def _send_dm_message(member: discord.Member):
        dm_msg = (
            f"Introduce yourself in <#{constants.general_channel_id}>\n\n"
            f"Leetcode discussion <#{constants.leetcode_channel_id}>\n\n"
            f"For **Leetcode challenges** checkout <#{constants.challenges_channel_id}>\n\n"
            f"We hope you enjoy your stay!"
        )
        # User could have DMs disabled
        try:
            await member.send(embed=embed_handler.footer_embed(dm_msg, "Welcome to Tortoise Community!"))
        except discord.Forbidden:
            pass

    @commands.Cog.listener()
    async def on_member_join(self, member: Member):
        if member.guild.id != constants.tortoise_guild_id:
            return
        self.joins_today -= 1

        inviter = await self.tracker.track_invite()
        created_at = f"<t:{int(member.created_at.timestamp())}:R>"

        if inviter:
            msg = (
                f"**Member:** {member} (`{member.id}`)\n"
                f"**Invited by:** {inviter}\n"
                f"**Account created:** {created_at}"
            )
        else:
            msg = (
                f"**Member:** {member} (`{member.id}`)\n"
                f"**Invited by:** Discord Discovery / Vanity\n"
                f"**Account created:** {created_at}"
            )

        await self._send_dm_message(member)
        await member.add_roles(self.welcome_role, reason="Welcome role added")
        await self.log_channel.send(embed=embed_handler.welcome(msg))
        await asyncio.sleep(60)
        await self.general_channel.send(
            content=f"Hi {member.mention}! Welcome to our server.",
            delete_after=60,
        )

    @commands.Cog.listener()
    async def on_member_remove(self, member: Member):
        if member.guild.id != constants.tortoise_guild_id:
            return

        self.leaves_today += 1

        joined_at = (
            f"<t:{int(member.joined_at.timestamp())}:R>"
            if member.joined_at else "Unknown"
        )

        msg = (
            f"**Member:** {member} (`{member.id}`)\n"
            f"**Joined at:** {joined_at}"
        )

        await self.log_channel.send(embed=embed_handler.goodbye(msg))


    @tasks.loop(time=dtime(hour=0, minute=0, tzinfo=timezone.utc))
    async def daily_retention_report(self):
        guild = self.bot.get_guild(constants.tortoise_guild_id)
        if not guild:
            return

        channel = guild.get_channel(constants.system_log_channel_id)
        if not channel:
            return

        net_change = self.joins_today - self.leaves_today

        if net_change > 0:
            emoji = "📈"
            value = f"+{net_change}"
        elif net_change < 0:
            emoji = "📉"
            value = str(net_change)
        else:
            emoji = "➖"
            value = "0"

        try:
            await channel.send(
                content=(
                    f"{emoji} **Daily Member Retention**\n"
                    f"Joins: **{self.joins_today}**\n"
                    f"Leaves: **{self.leaves_today}**\n"
                    f"Net change: **{value}**"
                )
            )
        except discord.Forbidden:
            pass

        self.joins_today = 0
        self.leaves_today = 0


async def setup(bot):
    await bot.add_cog(InviteTracker(bot))
