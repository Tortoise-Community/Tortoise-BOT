import aiohttp

import discord  # noqa
from discord.ext import commands, tasks

from bot.cogs.utils.embed_handler import info, project_embed
from bot.constants import github_repo_link, github_repo_stats_endpoint
from bot.api_client import TortoiseAPI  # noqa


class Github(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()
        self.projects = {}
        self.update_github_stats.start()

    async def get(self, endpoint: str):
        async with self.session.get(url=endpoint) as resp:
            return await resp.json()

    @staticmethod
    async def get_project_name(project):
        return project.rsplit("/")[-1]

    async def get_project_stats(self, name):
        return await self.get(endpoint=(github_repo_stats_endpoint+name))

    async def get_total_commits(self, name):
        endpoint = (github_repo_stats_endpoint + name + "/stats/participation")
        commit_list = await self.get(endpoint=endpoint)
        return sum(commit_list["all"])

    @tasks.loop(hours=6)
    async def update_github_stats(self):
        project_list = await self.bot.api_client.get_projects_data()
        for project in project_list:
            name = await self.get_project_name(project["github"])
            project = await self.get_project_stats(name)
            print(project)
            self.projects[name] = {}
            self.projects['repo_count'] = len([project_list])
            self.projects[name]['name'] = name
            self.projects[name]['issues'] = project["issues_url"]
            self.projects[name]['link'] = project["html_url"]
            self.projects[name]["stars"] = project["stargazers_count"]
            self.projects[name]["commits"] = "N/A"
            self.projects[name]["forks"] = project["forks_count"]

    @commands.command(aliases=["git"])
    async def github(self, ctx):
        """GitHub repository"""
        embed = project_embed(self.projects, ctx.me)
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Github(bot))
