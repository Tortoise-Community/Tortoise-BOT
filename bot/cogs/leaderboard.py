from __future__ import annotations
from typing import Optional

import discord
from discord.ext import commands
from discord import app_commands
from bot.constants import system_log_channel_id
from bot.utils.embed_handler import info, warning, success
from bot.utils.checks import check_if_tortoise_staff

class Leaderboard(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.manager = bot.points_manager
        self._log_channel = None

    @property
    def log_channel(self):
        if self._log_channel is None:
            self._log_channel = self.bot.get_channel(system_log_channel_id)
        return self._log_channel

    @staticmethod
    def build_challenge_embed(user):
        return info((
                "Participants who submit a valid working solution will be awarded points "
                "and featured on the leaderboard.\n\n"

                "**Guidelines:**\n"
                "- Start with a brute force approach if needed, then optimize for time and space complexity.\n"
                "- Do not use AI assistance.\n"
                "- Discussions are allowed in <#781129674860003336>, but do not share full solutions.\n"
                "- Any programming language is allowed.\n\n"

                "**Complexity Target:**\n"
                "- Aim for O(N) time and O(N) space or the best achievable complexity.\n"
                "- All valid submissions receive 100 points.\n"
                "- Optimal solutions receive an additional 50 points.\n"
                "- Special challenges award 150 points, with 50 bonus points for optimal solutions (200 total).\n\n"

                "**Submission Rules:**\n"
                "- Post solutions in <#780842875901575228>\n"
                "- Use spoiler tags to hide your code when submitting.\n"
                "- You may use <@712323581828136971> to validate your solution.\n"
                "- Use `/run` followed by properly formatted code blocks in <#781129674860003336>.\n"
                "- Delete your code after execution to avoid spoiling solutions.\n"
                "- Use `/run_help` for more information."
            ),
             user,
            "Challenge Guidelines",
        )


    @app_commands.command(name="challenge_rules", description="Show challenge guidelines")
    async def rules(self, interaction: discord.Interaction):
        await interaction.response.send_message(embed=self.build_challenge_embed(self.bot.user))


    @app_commands.command(name="rmpoints", description="Remove points from a user (mods only).")
    @app_commands.check(check_if_tortoise_staff)
    async def rmpoints(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        amount: app_commands.Range[int, 1, 10_000],
        silent: bool = True,
    ):

        await interaction.response.defer(ephemeral=True)

        new_total = await self.manager.remove_points(
            interaction.guild.id, member.id, amount
        )

        embed = info((
                f"**{amount}** points removed from {member.mention}\n"
                f"New total: **{new_total}** points."
            ),
            self.bot.user,
            "Points Removed",
            f"Removed by: {interaction.user.display_name}",
        )

        if not silent:
            dm_embed = info((
                f"**{amount}** points removed\n"
                f"New total: **{new_total}** points."
            ),
                self.bot.user,
                "Points Removed ;(",
            )
            try:
                await member.send(embed=dm_embed)
            except discord.Forbidden:
                pass

        await self.log_channel.send(embed=embed)

        await interaction.followup.send(
            embed=success(f"{amount} points removed. New total: {new_total}"),
            ephemeral=True
        )


    @app_commands.command(name="addpoints", description="Give points to a user (mods only).")
    @app_commands.check(check_if_tortoise_staff)
    async def addpoints(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        amount: app_commands.Range[int, 1, 10_000],
        reason: Optional[str] = None,
        silent: bool = False,
    ):

        await interaction.response.defer(ephemeral=True)

        new_total = await self.manager.add_points(
            interaction.guild.id, member.id, amount
        )

        desc = (
            f"{member.mention} received **{amount}** points.\n"
            f"New total: **{new_total}** points."
        )

        dm_desc = (
            f"You were awarded **{amount}** points.\n"
            f"New total: **{new_total}** points."
        )

        if reason:
            desc += f"\n\n**Reason:** {reason}"
            dm_desc += f"\n\n**Comment:** {reason}"

        embed = info(
            desc,
            self.bot.user,
            "Points Awarded",
            f"Given by {interaction.user.display_name}"
        )

        await self.log_channel.send(embed=embed)

        if not silent:
            dm_embed = info(
                dm_desc,
                self.bot.user,
                "Congratulations 🌟"
            )
            try:
                await member.send(
                    embed=dm_embed,
                )
            except discord.Forbidden:
                pass

        await interaction.followup.send(
            embed=success(f"{amount} points awarded. New total: {new_total}"),
            ephemeral=True
        )

    @app_commands.command(name="leaderboard", description="Show the points leaderboard.")
    async def leaderboard(self, interaction: discord.Interaction):

        await interaction.response.defer()

        entries = await self.manager.get_leaderboard(
            interaction.guild.id, min_points=1, limit=10
        )

        if not entries:
            await interaction.followup.send(
                embed=warning("No one has any points yet."), ephemeral=True
            )
            return

        embed = discord.Embed(
            title=f"🏆 {interaction.guild.name} Leaderboard",
            color=discord.Color.gold(),
        )

        medals = ["🥇", "🥈", "🥉"]

        for idx, (user_id, points) in enumerate(entries, start=1):
            member = interaction.guild.get_member(user_id)
            name = member.mention if member else f"<@{user_id}>"
            rank = medals[idx - 1] if idx <= 3 else f"#{idx}"
            embed.add_field(
                name=f"**{points}** points",
                value=f"{rank} {name}",
                inline=False,
            )

        await interaction.followup.send(embed=embed)


    @app_commands.command(name="points", description="Check points.")
    async def points(
        self,
        interaction: discord.Interaction,
        member: Optional[discord.Member] = None,
    ):

        target = member or interaction.user
        pts = await self.manager.get_points(interaction.guild.id, target.id)

        await interaction.response.send_message(
            embed=info(f"{target.mention} has **{pts}** points.", self.bot.user,"Points"),
            ephemeral=True
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Leaderboard(bot))