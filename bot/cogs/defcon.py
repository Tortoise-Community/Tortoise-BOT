import logging
import asyncio
import json
from datetime import datetime, timezone, timedelta
from collections import deque
from typing import Deque, Tuple, Set, Dict

import discord
from discord.ext import commands, tasks

from bot import constants
from bot.utils.embed_handler import success, failure
from bot.utils.checks import check_if_it_is_tortoise_guild

logger = logging.getLogger(__name__)

STATE_FILE = "defcon_state.json"


class Defcon(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

        self.defcon_active: bool = False
        self.defcon_since: datetime | None = None
        self.cooldown_until: datetime | None = None

        self._kicked_while_defcon_was_active: int = 0
        self.joins_per_min_trigger = 7

        self._joins: Deque[Tuple[datetime, int]] = deque()
        self._lock = asyncio.Lock()

        # smoothing
        self.window_seconds = 60
        self.burst_window = 10
        self.burst_threshold = 5

        # auto disable
        self.max_defcon_duration = timedelta(minutes=15)
        self.cooldown_duration = timedelta(minutes=5)

        # safety
        self.whitelist_roles: Set[int] = {constants.trusted_role_id}

        # channels
        self.staff_channel: discord.TextChannel | None = None
        self.lockable_channels: Set[int] = set(constants.defcon_lockable_channels)

        # embed state only [# channel_id -> message_id]
        self.lockdown_embed_messages: Dict[int, int] = {}

        self.mass_join_check.start()
        self.defcon_decay.start()


    def _now(self):
        return datetime.now(timezone.utc)

    def _has_bypass(self, member: discord.Member) -> bool:
        return any(r.id in self.whitelist_roles for r in member.roles)

    async def _ensure_staff_channel(self):
        if not self.staff_channel:
            self.staff_channel = self.bot.get_channel(constants.staff_channel_id)

    async def _load_state(self):
        try:
            with open(STATE_FILE, "r") as f:
                data = json.load(f)

            self.defcon_active = data.get("active", False)

            ts = data.get("since")
            if ts:
                self.defcon_since = datetime.fromisoformat(ts)

            self.lockdown_embed_messages = {
                int(k): int(v) for k, v in data.get("embeds", {}).items()
            }

        except Exception:
            pass

    async def _save_state(self):
        try:
            with open(STATE_FILE, "w") as f:
                json.dump({
                    "active": self.defcon_active,
                    "since": self.defcon_since.isoformat() if self.defcon_since else None,
                    "embeds": self.lockdown_embed_messages
                }, f)
        except Exception:
            pass

    async def _lock_channels(self, guild: discord.Guild):
        embed = discord.Embed(
            title="🚨 DEFCON ACTIVE",
            description="Server is temporarily locked due to raid detection.\nAccess will be restored automatically.",
            color=discord.Color.red(),
        )

        for channel_id in self.lockable_channels:
            channel = guild.get_channel(channel_id)

            if not channel or not isinstance(channel, discord.TextChannel):
                continue

            try:
                overwrite = channel.overwrites_for(guild.default_role)
                overwrite.send_messages = False

                await channel.set_permissions(
                    guild.default_role,
                    overwrite=overwrite,
                    reason="DEFCON lockdown"
                )

                msg = await channel.send(embed=embed)
                self.lockdown_embed_messages[channel.id] = msg.id

            except Exception as e:
                logger.warning("Lockdown failed for %s: %s", channel_id, e)

        await self._save_state()

    async def _unlock_channels(self, guild: discord.Guild):
        for channel_id in self.lockable_channels:
            channel = guild.get_channel(channel_id)

            if not channel or not isinstance(channel, discord.TextChannel):
                continue

            try:
                overwrite = channel.overwrites_for(guild.default_role)
                overwrite.send_messages = True

                await channel.set_permissions(
                    guild.default_role,
                    overwrite=overwrite,
                    reason="DEFCON unlock"
                )

                # delete embed from stored state
                if channel.id in self.lockdown_embed_messages:
                    try:
                        msg = await channel.fetch_message(
                            self.lockdown_embed_messages[channel.id]
                        )
                        await msg.delete()
                    except Exception:
                        pass

            except Exception as e:
                logger.warning("Unlock failed for %s: %s", channel_id, e)

        self.lockdown_embed_messages.clear()
        await self._save_state()


    @commands.Cog.listener()
    async def on_ready(self):
        await self._load_state()
        await self._ensure_staff_channel()

    @commands.Cog.listener()
    @commands.check(check_if_it_is_tortoise_guild)
    async def on_member_join(self, member: discord.Member):
        if member.guild.id != constants.tortoise_guild_id:
            return

        if self._has_bypass(member):
            return

        async with self._lock:
            self._joins.append((self._now(), member.id))

        if not self.defcon_active:
            return

        if not member.guild.me.guild_permissions.kick_members:
            return

        if member.top_role >= member.guild.me.top_role:
            return

        try:
            await member.kick(reason="DEFCON: automated raid mitigation")
            self._kicked_while_defcon_was_active += 1

            await self._ensure_staff_channel()
            if self.staff_channel:
                await self.staff_channel.send(
                    f"[DEFCON] Kicked {member} ({member.id})"
                )

        except discord.Forbidden:
            logger.warning("Kick forbidden: %s", member.id)
        except discord.HTTPException as e:
            logger.error("Kick failed: %s", e)


    @tasks.loop(seconds=5)
    async def mass_join_check(self):
        now = self._now()

        async with self._lock:
            while self._joins and (now - self._joins[0][0]).total_seconds() > self.window_seconds:
                self._joins.popleft()

            burst_count = sum(
                1 for t, _ in self._joins
                if (now - t).total_seconds() <= self.burst_window
            )
            window_count = len(self._joins)

        if self.cooldown_until and now < self.cooldown_until:
            return

        trigger = (
            window_count >= self.joins_per_min_trigger
            and burst_count >= self.burst_threshold
        )

        if trigger and not self.defcon_active:
            await self._activate_defcon(
                self.bot.get_guild(constants.tortoise_guild_id),
                reason="auto-detection"
            )

    @tasks.loop(seconds=30)
    async def defcon_decay(self):
        if not self.defcon_active or not self.defcon_since:
            return

        if self._now() - self.defcon_since >= self.max_defcon_duration:
            await self._deactivate_defcon(
                self.bot.get_guild(constants.tortoise_guild_id),
                auto=True
            )


    async def _activate_defcon(self, guild: discord.Guild, reason: str):
        if self.defcon_active:
            return

        self.defcon_active = True
        self.defcon_since = self._now()
        await self._save_state()

        await self._lock_channels(guild)

        await self._ensure_staff_channel()
        if self.staff_channel:
            await self.staff_channel.send(f"@here DEFCON ACTIVATED ({reason})")

    async def _deactivate_defcon(self, guild: discord.Guild, auto: bool = False):
        if not self.defcon_active:
            return

        self.defcon_active = False
        self.cooldown_until = self._now() + self.cooldown_duration
        self.defcon_since = None
        await self._save_state()

        await self._unlock_channels(guild)

        await self._ensure_staff_channel()
        if self.staff_channel:
            msg = "DEFCON AUTO-DEACTIVATED" if auto else "DEFCON MANUALLY DEACTIVATED"
            await self.staff_channel.send(f"{msg} | Cooldown active")


    @commands.command(name="enable_defcon")
    @commands.has_guild_permissions(administrator=True)
    @commands.check(check_if_it_is_tortoise_guild)
    async def enable_defcon(self, ctx):
        await self._activate_defcon(ctx.guild, reason=f"manual by {ctx.author}")
        await ctx.send(embed=success("DEFCON manually activated."))

    @commands.command(name="disable_defcon")
    @commands.has_guild_permissions(administrator=True)
    @commands.check(check_if_it_is_tortoise_guild)
    async def disable_defcon(self, ctx):
        await self._deactivate_defcon(ctx.guild, auto=False)
        await ctx.send(embed=success(
            f"DEFCON disabled. Kicked: {self._kicked_while_defcon_was_active}. Cooldown active."
        ))
        self._kicked_while_defcon_was_active = 0

    @commands.command()
    @commands.has_guild_permissions(administrator=True)
    @commands.check(check_if_it_is_tortoise_guild)
    async def set_defcon_trigger(self, ctx, trigger: int):
        if not 7 <= trigger <= 100:
            return await ctx.send(embed=failure("Trigger must be 7–100."))

        self.joins_per_min_trigger = trigger
        await ctx.send(embed=success(f"DEFCON trigger set to {trigger}/min."))


async def setup(bot: commands.Bot):
    await bot.add_cog(Defcon(bot))
