import datetime

import discord
from discord.ext import commands, tasks
from discord import app_commands
from bot.api_client import AdventOfCodeAPI
from bot.utils.misc import format_timedelta
from bot.utils.embed_handler import info, failure


class AdventOfCode(commands.Cog):
    TORTOISE_LEADERBOARD_ID = "4922988"
    TORTOISE_LEADERBOARD_INVITE = "4922988-d5f6845a"

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.aoc_api = AdventOfCodeAPI(
            leaderboard_id=self.TORTOISE_LEADERBOARD_ID,
            year=2025,
        )
        self._leaderboard_cache = None
        self.update_leaderboard_cache.start()

    @tasks.loop(minutes=30)
    async def update_leaderboard_cache(self):
        self._leaderboard_cache = await self.aoc_api.get_leaderboard()

    @update_leaderboard_cache.before_loop
    async def before_update_leaderboard_cache(self):
        # Ensure bot is ready before the loop starts
        await self.bot.wait_until_ready()


    @app_commands.command(
        name="aoc_invite",
        description="Shows invite code to the Tortoise Advent of Code leaderboard."
    )
    async def invite(self, interaction: discord.Interaction):
        """Shows invite to our Tortoise Advent of Code leaderboard."""
        guild = interaction.guild
        member = guild.me if guild is not None else interaction.client.user

        invite_embed = info(
            (
                f"Use this code to join Tortoise AoC leaderboard: "
                f"**{self.TORTOISE_LEADERBOARD_INVITE}**\n\n"
                "To join you can go to the AoC website: "
                "https://adventofcode.com/2025/leaderboard/private"
            ),
            title="Tortoise AoC",
            member=member
        )
        await interaction.response.send_message(embed=invite_embed)

    @app_commands.command(
        name="aoc_leaderboard",
        description="Show the Tortoise Advent of Code leaderboard (cached)."
    )
    async def leaderboard(self, interaction: discord.Interaction):
        """
        Shows Tortoise leaderboard.

        Leaderboard is updated each 30 minutes.
        """
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message(
                embed=failure("This command can only be used in a server."),
                ephemeral=True,
            )
            return
        if self._leaderboard_cache is None:
            await interaction.response.send_message(
                embed=failure("Please try again in a few seconds, cache is not yet loaded."),
                ephemeral=True,
            )
            return

        sorted_members = {
            k: v for k, v in sorted(
                self._leaderboard_cache["members"].items(),
                key=lambda item: item[1]["local_score"],
                reverse=True
            )
        }

        leaderboard_lines = ["```py"]
        num_of_members = 10
        position_counter = 0

        for member_id, member_data in sorted_members.items():
            position_counter += 1
            if position_counter > num_of_members:
                break

            stars_pretty = f"{'★' + str(member_data['stars']):4}"
            leaderboard_lines.append(
                f"{position_counter}. {member_data['local_score']:4}p "
                f"{stars_pretty} {member_data['name']}"
            )

        leaderboard_lines.append("```")
        leaderboard_text = "\n".join(leaderboard_lines)

        embed = info(
            f"{leaderboard_text}\n\nThe leaderboard is refreshed every 30 minutes.",
            member=guild.me,
            title="Tortoise AoC leaderboard"
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="aoc_countdown",
        description="Time until the next Advent of Code challenge starts."
    )
    async def aoc_countdown(self, interaction: discord.Interaction):
        """Time until next challenge starts."""
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message(
                embed=failure("This command can only be used in a server."),
                ephemeral=True,
            )
            return

        utc_minus_5 = datetime.timezone(offset=datetime.timedelta(hours=-5))
        now = datetime.datetime.now(tz=utc_minus_5)

        if now.month != 12:
            await interaction.response.send_message(
                embed=failure("AoC is over!"),
                ephemeral=True,
            )
            return

        current_day = now.day
        end_date = datetime.datetime(
            year=2025,
            month=12,
            day=current_day + 1,
            tzinfo=utc_minus_5
        )

        difference = end_date - now
        ends_in = format_timedelta(difference)

        embed = info(
            f"Day {current_day} ends in {ends_in}",
            title="Countdown",
            member=guild.me,
        )
        await interaction.response.send_message(embed=embed)




async def setup(bot):
    await bot.add_cog(AdventOfCode(bot))
