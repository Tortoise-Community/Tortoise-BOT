from __future__ import annotations

from typing import Optional
from datetime import datetime, timedelta, timezone

import discord
from discord.ext import commands, tasks
from discord import app_commands

from bot.utils.embed_handler import success, info, warning


class AFK(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.manager = bot.afk_manager
        self.cleanup_expired.start()

    def cog_unload(self):
        self.cleanup_expired.cancel()

    @app_commands.command(name="setafk", description="Set AFK status.")
    async def setafk(
        self,
        interaction: discord.Interaction,
        hours: Optional[int] = None,
        days: Optional[int] = None,
        reason: Optional[str] = None,
    ):
        if interaction.guild is None:
            await interaction.response.send_message(
                embed=warning("Server only command."),
                ephemeral=True
            )
            return

        if not hours and not days:
            await interaction.response.send_message(
                embed=warning("Provide hours or days."),
                ephemeral=True
            )
            return

        total = timedelta(hours=hours or 0, days=days or 0)
        until = datetime.now(timezone.utc) + total

        await self.manager.set_afk(
            interaction.guild.id,
            interaction.user.id,
            until,
            reason,
        )

        embed = success(f"You are AFK for {total}.")

        if reason:
            embed.add_field(name="Reason", value=reason, inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild or message.author.bot:
            return

        guild_id = message.guild.id
        user_id = message.author.id

        afk = self.manager.get_afk(guild_id, user_id)
        if afk:
            await self.manager.remove_afk(guild_id, user_id)
            await message.channel.send(
                embed=success("You are no longer AFK")
            )

        mentioned_users = set(message.mentions)

        if message.reference:
            ref = message.reference.resolved
            if isinstance(ref, discord.Message):
                mentioned_users.add(ref.author)

        now = datetime.now(timezone.utc)

        for member in mentioned_users:
            if member.bot:
                continue

            data = self.manager.get_afk(guild_id, member.id)
            if not data:
                continue

            remaining = data["until"] - now

            # expired → cleanup
            if remaining.total_seconds() <= 0:
                await self.manager.remove_afk(guild_id, member.id)
                continue

            # format time
            total_seconds = int(remaining.total_seconds())
            hours, rem = divmod(total_seconds, 3600)
            days, hours = divmod(hours, 24)

            parts = []
            if days:
                parts.append(f"{days}d")
            if hours:
                parts.append(f"{hours}h")

            embed = info(
                f"{member.mention} is AFK for {' '.join(parts)}.",
                member,
                title="",
                footer_text=f"Reason: {data['reason']}" if data.get("reason") else None,
            )
            await message.channel.send(embed=embed)

    @tasks.loop(minutes=10)
    async def cleanup_expired(self):
        expired = self.manager.get_expired()
        for guild_id, user_id in expired:
            await self.manager.remove_afk(guild_id, user_id)

    @cleanup_expired.before_loop
    async def before_cleanup(self):
        await self.bot.wait_until_ready()

async def setup(bot: commands.Bot):
    await bot.add_cog(AFK(bot))