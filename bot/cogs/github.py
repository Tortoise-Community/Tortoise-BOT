import aiohttp

import discord
from discord.ext import commands

from bot.cogs.utils.embed_handler import info
from bot.constants import github_repo_link


class Github(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()
        self.projects = []

    @commands.command(aliases=["git"])
    async def github(self, ctx):
        """GitHub repository"""
        embed = info(f"[Tortoise github repository]({github_repo_link})", ctx.me, "Github")
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Github(bot))
