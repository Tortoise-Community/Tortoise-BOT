import datetime

from discord.ext import commands, tasks

from bot.api_client import GithubAPI
from bot.constants import project_url
from bot.utils.embed_handler import project_embed


class Project:
    def __init__(self, project_data: dict):
        self.name = project_data["name"]
        self.link = project_data["html_url"]
        self.web_url = project_data["web_link"]
        self.forks = project_data["forks_count"]
        self.commits = project_data["commit_count"]
        self.stars = project_data["stargazers_count"]
        self.contributors = project_data["contributors_count"]


class Github(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.github_client = GithubAPI()
        self.projects = {}
        self.update_github_stats.start()

    @classmethod
    def get_project_name(cls, link):
        return link.rsplit("/")[-1]

    async def get_project_stats(self, project):
        name = self.get_project_name(project["github"])
        stats = await self.github_client.get(name)
        stats["commit_count"] = await self.github_client.get_project_commits(name)
        contributors = await self.github_client.get(f"{name}/contributors")
        stats["contributors_count"] = len(contributors)
        stats["web_link"] = f"{project_url}{project.get('pk')}"
        return stats

    @tasks.loop(hours=3)
    async def update_github_stats(self):
        project_list = await self.bot.api_client.get_projects_data()
        for project in project_list:
            project_stats = await self.get_project_stats(project)
            item = Project(project_stats)
            self.projects[item.name] = item
            self.projects["last_updated"] = datetime.datetime.now()
            await self.bot.api_client.put_project_data(project["pk"], vars(item))

    @commands.command(aliases=["git"])
    async def github(self, ctx):
        """Show Tortoise GitHub projects stats."""
        await ctx.send(embed=project_embed(self.projects, ctx.me))


async def setup(bot):
    await bot.add_cog(Github(bot))
