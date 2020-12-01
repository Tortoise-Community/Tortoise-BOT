import datetime

from discord.ext import commands, tasks

from bot.api_client import AdventOfCodeAPI
from bot.utils.misc import format_timedelta
from bot.utils.embed_handler import info, failure


class AdventOfCode(commands.Cog):
    TORTOISE_LEADERBOARD_ID = "432225"
    TORTOISE_LEADERBOARD_INVITE = "432225-ab5dcfc1"

    def __init__(self, bot):
        self.bot = bot
        self.aoc_api = AdventOfCodeAPI(self.TORTOISE_LEADERBOARD_ID, loop=self.bot.loop)
        self._leaderboard_cache = None
        self.update_leaderboard_cache.start()

    @tasks.loop(minutes=30)
    async def update_leaderboard_cache(self):
        self._leaderboard_cache = await self.aoc_api.get_leaderboard()

    @commands.command()
    async def invite(self, ctx):
        invite_embed = info(
            f"Use this code to join Tortoise AoC leaderboard: **{self.TORTOISE_LEADERBOARD_INVITE}**\n\n"
            "To join you can go to the AoC website: https://adventofcode.com/2020/leaderboard",
            title="Tortoise AoC",
            member=ctx.guild.me
        )
        await ctx.send(embed=invite_embed)

    @commands.command()
    async def leaderboard(self, ctx):
        """
        Shows Tortoise leaderboard.

        Leaderboard is updated each 30 minutes.
        """
        if self._leaderboard_cache is None:
            return await ctx.send(embed=failure("Please try again in few seconds as cache is not yet loaded."))

        sorted_members = {
            k: v for k, v in sorted(self._leaderboard_cache["members"].items(), key=lambda item: item[1]["local_score"])
        }

        leaderboard = []
        top_members = 10
        flag_counter = 0

        for member_id, member_data in sorted_members.items():
            flag_counter += 1
            if flag_counter > top_members:
                break

            leaderboard.append(f"{flag_counter}. {member_data['name']} {member_data['local_score']}")

        embed = info("\n".join(leaderboard), member=ctx.guild.me, title="Tortoise AoC leaderboard")
        await ctx.send(embed=embed)

    @commands.command()
    async def aoc_countdown(self, ctx):
        """Time until next challenge starts."""
        utc_minus_5 = datetime.timezone(offset=datetime.timedelta(hours=-5))
        now = datetime.datetime.now(tz=utc_minus_5)
        if now.month != 12:
            return await ctx.send(embed=failure("AoC is over!"))

        current_day = now.day
        end_date = datetime.datetime(year=2020, month=12, day=current_day+1, tzinfo=utc_minus_5)

        difference = end_date - now
        if difference.total_seconds() <= 0:
            return await ctx.send(embed=failure("BrainDead did not code this well :pomf:"))
        else:
            ends_in = format_timedelta(difference)
            await ctx.send(embed=info(f"Day {current_day} ends in {ends_in}", title="Countdown", member=ctx.guild.me))


def setup(bot):
    bot.add_cog(AdventOfCode(bot))
