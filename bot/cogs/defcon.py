import logging
from datetime import datetime
from typing import Set, Tuple

import discord
from discord.ext import commands, tasks

from bot import constants
from bot.utils.embed_handler import success, failure
from bot.utils.checks import check_if_it_is_tortoise_guild


logger = logging.getLogger(__name__)


class Defcon(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.defcon_active = False
        self._kicked_while_defcon_was_active: int = 0
        self.joins_per_min_trigger = 7
        self._joins: Set[Tuple[datetime, int]] = set()
        self.staff_channel = bot.get_channel(constants.staff_channel_id)

    @commands.Cog.listener()
    @commands.check(check_if_it_is_tortoise_guild)
    async def on_member_join(self, member: discord.Member):
        # Mitigate latency by using server time
        self._joins.add((datetime.now(), member.id))

        if self.defcon_active:
            await member.kick(
                reason=(
                    "Bot detected mass member join (raid), kicking all new joins for a while.\n"
                    "If you're just a regular user you can wait a bit and try to join later."
                )
            )
            self._kicked_while_defcon_was_active += 1

    @tasks.loop(minutes=1)
    async def mass_join_check(self):
        current_time = datetime.now()

        for join in self._joins.copy():
            if (current_time - join[0]).seconds >= 60:
                self._joins.remove(join)

        if len(self._joins) >= self.joins_per_min_trigger:
            if self.defcon_active:
                return

            self.defcon_active = True
            await self.staff_channel.send(
                f"@here DEFCON activated, detected {len(self._joins)} joins in the last minute!\n"
                f"I'll kick any new joins as long as DEFCON is active, you need to manually disable it with:\n"
                f"t.disable_defcon"
            )

    @commands.command()
    @commands.has_guild_permissions(administrator=True)
    @commands.check(check_if_it_is_tortoise_guild)
    async def disable_defcon(self, ctx):
        self.defcon_active = False
        await ctx.send(embed=success(
                f"Successfully deactivated DEFCON.\n"
                f"Kicked user count: {self._kicked_while_defcon_was_active}"
            )
        )
        self._kicked_while_defcon_was_active = 0

    @commands.command()
    @commands.has_guild_permissions(administrator=True)
    @commands.check(check_if_it_is_tortoise_guild)
    async def set_defcon_trigger(self, ctx, trigger: int):
        if not 7 <= trigger <= 100:
            return await ctx.send(embed=failure("Please use integer from 7 to 100."))

        self.joins_per_min_trigger = trigger
        await ctx.send(embed=success(f"Successfully changed DEFCON trigger to {trigger} users/min."))


def setup(bot):
    bot.add_cog(Defcon(bot))
