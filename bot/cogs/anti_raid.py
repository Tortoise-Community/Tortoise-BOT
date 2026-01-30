from __future__ import annotations

import time
from collections import defaultdict, deque

import discord
from discord.ext import commands

from bot.constants import (
    system_log_channel_id, bait_channel_id, new_member_role, tortoise_guild_id, here_mention,
    everyone_mention, infraction_img_url
)
from bot.utils.embed_handler import simple_embed


class AntiRaidSpam(commands.Cog):
    """
    Bans users who spam messages across multiple channels.

    Trust model:
    - Users with the new member role are treated as untrusted.
    - Protection automatically expires when the role is removed.
    """

    BAN_REASON = "Raid protection: multi-channel spam"
    APPEAL_SERVER_URL = "https://discord.gg/YxEzEqMNY8"

    SPAM_WINDOW = 20
    CHANNEL_THRESHOLD = 3
    MAX_LOG_SIZE = 100


    def __init__(self, bot):
        self.bot = bot
        # guild_id -> member_id -> deque[(ts, channel_id, content, message_id)]
        self.message_log = defaultdict(lambda: defaultdict(deque))


    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or message.guild is None or message.guild.id != tortoise_guild_id:
            return

        member = message.author
        guild = message.guild
        now = time.time()

        if member.guild_permissions.manage_messages:
            return

        #MENTIONED EVERYONE/HERE: IMMEDIATE BAN
        if everyone_mention in message.clean_content or here_mention in message.clean_content:
            await self.handle_raid(
                member,
                [(now, message.channel.id, "[Mentioned @everyone]", message.id)],
            )
            self.message_log[guild.id].pop(member.id, None)
            return

        #BAIT CHANNEL: IMMEDIATE BAN
        if message.channel.id == bait_channel_id:
            await self.handle_raid(
                member,
                [(now, bait_channel_id, message.content, message.id)],
            )
            self.message_log[guild.id].pop(member.id, None)
            return


        has_new_role = any(r.id == new_member_role for r in member.roles)

        if not has_new_role:
            return

        logs = self.message_log[guild.id][member.id]
        content = self._extract_message_content(message)

        logs.append((now, message.channel.id, content, message.id))

        # Bound memory
        if len(logs) > self.MAX_LOG_SIZE:
            logs.popleft()

        # Remove expired entries
        while logs and now - logs[0][0] > self.SPAM_WINDOW:
            logs.popleft()

        unique_channels = {cid for _, cid, _, _ in logs}
        contents = [c for _, _, c, _ in logs]
        repetitive = len(set(contents)) <= 2

        if len(unique_channels) >= self.CHANNEL_THRESHOLD and repetitive:
            await self.handle_raid(member, list(logs))
            self.message_log[guild.id].pop(member.id, None)


    def _extract_message_content(self, message: discord.Message) -> str:
        parts: list[str] = []

        if message.clean_content:
            parts.append(message.clean_content.strip())

        for attachment in message.attachments:
            parts.append(f"[Attachment] {attachment.url}")

        for embed in message.embeds:
            if embed.url:
                parts.append(f"[Embed URL] {embed.url}")
            elif embed.title or embed.description:
                preview = (embed.title or embed.description or "").strip()
                if preview:
                    parts.append(f"[Embed] {preview[:200]}")

        if message.stickers:
            parts.append("[Sticker]")

        if not parts:
            return "[Empty message payload]"

        return " | ".join(parts)[:500]


    async def handle_raid(
        self,
        member: discord.Member,
        logs: list[tuple[float, int, str, int]],
    ):
        guild = member.guild

        try:
            for _, _, _, msg_id in logs:
                self.bot.suppressed_deletes.add(msg_id)
        except Exception:
            pass

        await self.send_dm_notice(member, guild)

        try:
            await guild.ban(
                member,
                reason=self.BAN_REASON,
                delete_message_days=1,
            )
        except discord.Forbidden:
            return

        await self.log_to_mod_channel(guild, member, logs)


    async def send_dm_notice(self, member: discord.Member, guild: discord.Guild):
        embed = simple_embed(
            title="This action was performed automatically",
            message=(
                f"\nYou were banned from **{guild.name}**\n\n"
                "Our **automated raid protection** system detected spam-like behavior across multiple channels.\n\n"
                "**If this was a mistake**, you may appeal below.\n\n"
                f"Click 👉 [APPEAL HERE]({self.APPEAL_SERVER_URL}) 👈\n"
            ),
            color=discord.Color.red()
        )
        embed.set_image(url=infraction_img_url)
        try:
            await member.send(embed=embed)
        except discord.Forbidden:
            pass


    async def log_to_mod_channel(
        self,
        guild: discord.Guild,
        member: discord.Member,
        logs: list[tuple[float, int, str, int]],
    ):
        channel = guild.get_channel(system_log_channel_id)
        if channel is None:
            return

        lines = []
        for _, channel_id, content, _ in logs:
            ch = guild.get_channel(channel_id)
            name = f"#{ch.name}" if ch else f"#{channel_id}"
            lines.append(f"**{name}:** {content}")

        embed = discord.Embed(
            title="Raid Ban Triggered",
            color=discord.Color.orange(),
        )
        embed.add_field(
            name="User",
            value=f"{member} (`{member.id}`)",
            inline=False,
        )
        embed.add_field(
            name="Joined",
            value=(
                f"<t:{int(member.joined_at.timestamp())}:R>"
                if member.joined_at else "Unknown"
            ),
            inline=False,
        )
        embed.add_field(
            name="Messages",
            value="\n".join(lines),
            inline=False,
        )
        embed.set_footer(text=self.BAN_REASON)

        try:
            await channel.send(embed=embed)
        except discord.Forbidden:
            pass


async def setup(bot: commands.Bot):
    await bot.add_cog(AntiRaidSpam(bot))
