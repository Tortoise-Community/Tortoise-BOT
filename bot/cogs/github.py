import urllib
import datetime

import aiohttp

from discord.ext import commands, tasks

from bot.cogs.utils.embed_handler import project_embed
from bot.constants import github_repo_stats_endpoint
from bot.cogs.utils.misc import Project


class Github(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()
        self.projects = {}
        self.update_github_stats.start()

    async def get(self, endpoint: str, params=None):
        async with self.session.get(url=endpoint) as resp:
            return await resp.json()

    @staticmethod
    def get_project_name(link):
        return link.rsplit("/")[-1]

    async def get_project_commits(self, name):
        params = {
            'sha': "master",
            'per_page': 1,
        }
        async with self.session.get(url=github_repo_stats_endpoint+name+"/commits", params=params) as resp:
            if (resp.status // 100) != 2:
                raise Exception(f'invalid github response: {resp.text}')
            commit_count = len(await resp.json())
            last_page = resp.links.get('last')
            if last_page:
                # extract the query string from the last page url
                qs = urllib.parse.urlparse(str(last_page['url'])).query
                # extract the page number from the query string
                commit_count = int(dict(urllib.parse.parse_qsl(qs))['page'])
            return commit_count

    async def get_project_stats(self, name):
        stats = await self.get(endpoint=(github_repo_stats_endpoint+name))
        stats["commit_count"] = await self.get_project_commits(name)
        contributors = await self.get(endpoint=(github_repo_stats_endpoint + name + "/contributors"))
        stats["contributors_count"] = len(contributors)
        return stats

    @tasks.loop(hours=3)
    async def update_github_stats(self):
        project_list = await self.bot.api_client.get_projects_data()
        for project in project_list:
            name = self.get_project_name(project["github"])
            project_stats = await self.get_project_stats(name)
            self.projects["last_updated"] = datetime.datetime.now()
            item = Project(project_stats)
            self.projects[name] = item
            await self.bot.api_client.put_project_data(project["pk"], vars(item))

    @commands.command(aliases=["git"])
    async def github(self, ctx):
        """GitHub stats"""
        embed = project_embed(self.projects, ctx.me)
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Github(bot))
