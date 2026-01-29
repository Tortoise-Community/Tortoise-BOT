import discord
from discord import Invite, Member
from discord.ext import commands

from bot.utils import invite_help, embed_handler
from bot import constants


class InviteTracker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.guild = None
        self.tracker = None
        self.log_channel = None

    @commands.Cog.listener()
    async def on_ready(self):
        self.guild = self.bot.get_guild(constants.tortoise_guild_id)
        self.tracker = invite_help.GuildInviteTracker(self.guild)
        self.log_channel = self.bot.get_channel(constants.system_log_channel_id)
        self.bot.loop.create_task(self.tracker.refresh_invite_cache())

    @commands.Cog.listener()
    async def on_invite_create(self, invite: Invite):
        await self.tracker.add_new_invite(invite)

    @commands.Cog.listener()
    async def on_invite_delete(self, invite: Invite):
        await self.tracker.remove_invite(invite)


    async def _send_dm_message(self, member: discord.Member):
        dm_msg = (
            f"Introduce yourself in <#{constants.general_channel_id}>\n\n"
            f"Leetcode discussion <#{constants.leetcode_channel_id}>\n\n"
            f"For **Leetcode challenges** checkout <#{constants.challenges_channel_id}>\n\n"
            f"We hope you enjoy your stay!"
        )
        try:
            await member.send(embed=embed_handler.footer_embed(dm_msg, "Welcome to Tortoise Community!"))
        except discord.Forbidden:
            pass

    @commands.Cog.listener()
    async def on_member_join(self, member: Member):
        if member.guild.id != constants.tortoise_guild_id:
            return
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
        await self.log_channel.send(embed=embed_handler.welcome(msg))


    @commands.Cog.listener()
    async def on_member_remove(self, member: Member):
        if member.guild.id != constants.tortoise_guild_id:
            return

        joined_at = (
            f"<t:{int(member.joined_at.timestamp())}:R>"
            if member.joined_at else "Unknown"
        )

        msg = (
            f"**Member:** {member} (`{member.id}`)\n"
            f"**Joined at:** {joined_at}"
        )

        await self.log_channel.send(embed=embed_handler.goodbye(msg))


async def setup(bot):
    await bot.add_cog(InviteTracker(bot))
