from datetime import time as dtime, timezone
import random
import discord
import asyncio
from discord import Invite, Member, Message, app_commands
from discord.ext import commands, tasks

from bot.utils import invite_help, embed_handler
from bot import constants
from bot.utils.checks import tortoise_bot_developer_only
from bot.utils.embed_handler import success


class JoinManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.guild = None
        self.tracker = None
        self.log_channel = None
        self.welcome_role = None
        self.ban_appeal_guild = None
        self.introduction_channel = None
        self.retention = bot.retention_manager
        self.custom_welcome_content = None


    def get_unbanned_embed(self):
        return embed_handler.info(
            "You are not currently banned from Tortoise Community, "
            "or your ban has been lifted.\n\nYou can rejoin using the link below.\n\n"
            f"👉 [Invite Link]({constants.server_link}) ",
            self.bot.user,
            "Unban Notice!",
            "Welcome back to our server!"
        )


    @commands.Cog.listener()
    async def on_ready(self):
        self.guild = self.bot.get_guild(constants.tortoise_guild_id)
        self.ban_appeal_guild = self.bot.get_guild(constants.ban_appeal_server_id)
        self.tracker = invite_help.GuildInviteTracker(self.guild)
        self.log_channel = self.bot.get_channel(constants.system_log_channel_id)
        self.welcome_role = self.guild.get_role(constants.new_member_role_id)
        self.introduction_channel = self.guild.get_channel(constants.introduction_channel_id)

        self.bot.loop.create_task(self.tracker.refresh_invite_cache())
        if not self.daily_retention_report.is_running():
            self.daily_retention_report.start()

    @commands.Cog.listener()
    async def on_invite_create(self, invite: Invite):
        await self.tracker.add_new_invite(invite)

    @commands.Cog.listener()
    async def on_invite_delete(self, invite: Invite):
        await self.tracker.remove_invite(invite)

    @app_commands.command()
    @app_commands.check(tortoise_bot_developer_only)
    async def send_welcome(self, interaction: discord.Interaction):
        await self._send_dm_message(interaction.user)
        await interaction.response.send_message(embed=success("Sent."), ephemeral=True)

    async def _send_dm_message(self, member: discord.Member):
        if not member.bot:
            dm_msg = (
                f"Please introduce yourself [here]({self.introduction_channel.jump_url})\n\n"
                f"### <:leetcode:1504482678840361115> Leetcode discussion\n <#{constants.leetcode_channel_id}>\n\n"
                f"### <:leetcode:1504482678840361115> Leetcode challenges\n <#{constants.challenges_channel_id}>\n\n"
                f"### 🎓 Join our DSA Study Group\n <#{constants.join_a_team_channel_id}>"
            )
            # User could have DMs disabled
            try:
                await member.send(
                    content=self.custom_welcome_content,
                    embed=embed_handler.footer_embed(dm_msg, "Welcome to Tortoise Programming Community!")
                )
            except discord.Forbidden:
                pass

    @app_commands.command(description="Set custom welcome message content")
    @app_commands.check(tortoise_bot_developer_only)
    async def set_welcome_message_content(self, interaction: discord.Interaction, content: str):
        if content.lower() == "none":
            self.custom_welcome_content = None
        else:
            self.custom_welcome_content = content
        await interaction.response.send_message(embed=embed_handler.success("Custom welcome content set"))

    async def handle_ban_appeal_server_join(self, member: Member):
        try:
            await self.guild.fetch_ban(discord.Object(id=member.id))
            is_banned = True
        except discord.NotFound:
            is_banned = False
        except discord.Forbidden:
            return
        except discord.HTTPException:
            return

        if not is_banned:
            embed = self.get_unbanned_embed()
            try:
                await member.send(embed=embed)
            except discord.Forbidden:
                pass

            await member.kick(reason="Not banned from Tortoise Programming Community")
            await asyncio.sleep(3)

    @staticmethod
    def get_post_intro_message() -> str:
        messages = [
            f"Nice introduction! Now head over to <#{constants.general_channel_id}> and start chatting with everyone.",
            f"Great intro! Jump into <#{constants.general_channel_id}> and join the ongoing conversations.",
            f"Thanks for introducing yourself! Feel free to continue the conversation in <#{constants.general_channel_id}>.",
            f"Welcome! Now you can head to <#{constants.general_channel_id}> and start connecting with others.",
            f"Nice to meet you! Go ahead and say hi in <#{constants.general_channel_id}> to meet more people.",
            f"Good intro. Continue chatting and get involved in <#{constants.general_channel_id}>.",
            f"Welcome aboard! You can now join the discussion in <#{constants.general_channel_id}>.",
            f"Awesome intro! Head over to <#{constants.general_channel_id}> and start interacting.",
            f"Thanks for sharing! Now jump into <#{constants.general_channel_id}> and meet the community.",
            f"Nice introduction! Don’t stop here — continue the conversation in <#{constants.general_channel_id}>.",
        ]

        return random.choice(messages)

    @commands.Cog.listener()
    async def on_message(self, message: Message):

        if not message.guild or message.author.bot:
            return

        if message.guild.id != constants.tortoise_guild_id:
            return

        if message.channel.id != constants.introduction_channel_id:
            return

        if (message.author.get_role(constants.admin_role_id) or
                message.author.get_role(constants.moderator_role_id)):
            return

        try:
            await asyncio.sleep(0.3)
            await message.add_reaction(
                random.choice(
                    [
                        "👋", "🔥", "👍", "😄", "😸",
                        "🌟", "🫶", "🤝", "👌", "✌️",
                        "<:upvote:741202481090002994>"
                    ]
                )
            )
            embed = embed_handler.info(
                self.get_post_intro_message(),
                self.bot.user,
                ""
            )
            await asyncio.sleep(0.7)
            await message.channel.send(embed=embed, delete_after=30)

        except discord.Forbidden:
            pass
        except discord.HTTPException:
            pass

    @commands.Cog.listener()
    async def on_member_join(self, member: Member):
        # If user joins appeal server, check if they are banned in tortoise.
        if member.guild.id == constants.ban_appeal_server_id:
            await self.handle_ban_appeal_server_join(member)
            return

        if member.guild.id != constants.tortoise_guild_id:
            return

        # Instantly ban any bots joining when bot protection is enabled.
        if member.bot and self.bot.advanced_protection:
            await self.log_channel.send(embed=embed_handler.warning(f"{member.mention} bot was banned due to Advanced Protection™"))
            await member.ban(reason="Advanced Protection™ enabled. Bot joins are prohibited.")
            return

        await self.retention.add_join(member.guild.id)

        inviter, code = None, None

        if self.tracker:
            try:
                inviter, code = await self.tracker.track_inviter_and_code()
            except Exception:
                inviter, code = None, None

        created_at = f"<t:{int(member.created_at.timestamp())}:R>"

        if inviter:
            msg = (
                f"**Username:** {member}\n"
                f"**Invited by:** {inviter}\n"
                f"**Invite Code:** `{code}`\n"
                f"**Account created:** {created_at}"
            )
        else:
            msg = (
                f"**Username:** {member}\n"
                f"**Invited by:** Discord Discovery / Vanity\n"
                f"**Account created:** {created_at}"
            )

        await self._send_dm_message(member)
        await member.add_roles(self.welcome_role, reason="Welcome role added")
        await self.log_channel.send(embed=embed_handler.welcome(member, msg))
        await asyncio.sleep(60)
        await self.introduction_channel.send(
            content=f"Hi {member.mention}! Welcome to our server.\n"
                    f"Please introduce yourself here.\n\n"
                    f"📌Suggested Format (copy-paste)\n"
                    + constants.introduction_format
                    + "> **Recommended**: Helps like-minded members find you easily."
            ,
            delete_after=60,
        )

    @commands.Cog.listener()
    async def on_member_remove(self, member: Member):
        if member.guild.id != constants.tortoise_guild_id:
            return

        await self.retention.add_leave(member.guild.id)

        joined_at = (
            f"<t:{int(member.joined_at.timestamp())}:R>"
            if member.joined_at else "Unknown"
        )

        msg = (
            f"**Member:** {member}\n"
            f"**Joined at:** {joined_at}"
        )

        await self.log_channel.send(embed=embed_handler.goodbye(member, msg))


    @tasks.loop(time=dtime(hour=0, minute=0, tzinfo=timezone.utc))
    async def daily_retention_report(self):
        guild = self.bot.get_guild(constants.tortoise_guild_id)
        if not guild:
            return

        channel = guild.get_channel(constants.system_log_channel_id)
        if not channel:
            return

        joins, leaves = await self.retention.get_yesterday(guild.id)
        net_change = joins - leaves

        if net_change > 0:
            emoji = constants.stonks_emoji
            value = f"+{net_change}"
        elif net_change < 0:
            emoji = constants.sadcat_emoji
            value = str(net_change)
        else:
            emoji = constants.poker_face_emoji
            value = "0"

        try:
            await channel.send(
                content=(
                    f"{emoji} **Daily Member Retention**\n"
                    f"Joins: **{joins}**\n"
                    f"Leaves: **{leaves}**\n"
                    f"Net change: **{value}**"
                )
            )
        except discord.Forbidden:
            pass


async def setup(bot):
    await bot.add_cog(JoinManager(bot))
