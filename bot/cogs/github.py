import datetime
import logging
import aiohttp.client_exceptions

from discord.ext import commands, tasks

from bot.api_client import GithubAPI
from bot.constants import project_url
from bot.utils.embed_handler import project_embed


USE_STATIC = True

STATIC_PROJECTS_DATA = [
    {
        "name": "Tortoise-Bot",
        "html_url": "https://github.com/Tortoise-Community/Tortoise-Bot",
        "web_link": "https://github.com/Tortoise-Community/Tortoise-Bot",
        "forks_count": 21,
        "commit_count": 732,
        "stargazers_count": 57,
        "contributors_count": 0,
        "language": "Python",
        "short_desc": "Fully functional Bot for Discord coded in Discord.py",
    },
    {
        "name": "Snappy-Bot",
        "html_url": "https://github.com/Tortoise-Community/Snappy-Bot",
        "web_link": "https://github.com/Tortoise-Community/Snappy-Bot",
        "forks_count": 1,
        "commit_count": 25,
        "stargazers_count": 1,
        "contributors_count": 0,
        "language": "Python",
        "short_desc": "Snappy is a lightweight Discord bot built using discord.py v2+",
    },
    {
        "name": "Backend",
        "html_url": "https://github.com/Tortoise-Community/Backend",
        "web_link": "https://github.com/Tortoise-Community/Backend",
        "forks_count": 1,
        "commit_count": 573,
        "stargazers_count": 8,
        "contributors_count": 0,
        "language": "Python",
        "short_desc": "Website build with django for the Tortoise Community discord server",
    },
    {
        "name": "Frontend",
        "html_url": "https://github.com/Tortoise-Community/Frontend",
        "web_link": "https://github.com/Tortoise-Community/Frontend",
        "forks_count": 1,
        "commit_count": 119,
        "stargazers_count": 1,
        "contributors_count": 0,
        "language": "React",
        "short_desc": "Web frontend built with React for Tortoise Community discord server",
    },
    {
        "name": "BladeList",
        "html_url": "https://github.com/Bladelist",
        "web_link": "https://github.com/Bladelist",
        "forks_count": 7,
        "commit_count": 290,
        "stargazers_count": 9,
        "contributors_count": 0,
        "language": "Django",
        "short_desc": "An open-source Discord Bot and Server Listing site built with Django.",
    },
]

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

        if USE_STATIC:
            self._load_static()
        else:
            self.update_github_stats.start()


    def _load_static(self):
        try:
            for project_stats in STATIC_PROJECTS_DATA:
                item = Project(project_stats)
                self.projects[item.name] = item

            self.projects["last_updated"] = datetime.datetime.now()

        except Exception as e:
            logging.error(f"Failed loading static GitHub data: {e}")


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
        try:
            project_list = await self.bot.api_client.get_projects_data()
            for project in project_list:
                project_stats = await self.get_project_stats(project)
                item = Project(project_stats)
                self.projects[item.name] = item
                self.projects["last_updated"] = datetime.datetime.now()
                await self.bot.api_client.put_project_data(project["pk"], vars(item))
        except aiohttp.client_exceptions.ClientConnectorDNSError as e:
            logging.error(f"DNS resolution failed in GitHub stats update: {e}")
        except Exception as e:
            logging.error(f"Unexpected error in GitHub stats update: {e}")

    @commands.command(aliases=["git"])
    async def github(self, ctx):
        """Show Tortoise GitHub projects stats."""
        await ctx.send(embed=project_embed(self.projects, ctx.me))


async def setup(bot):
    await bot.add_cog(Github(bot))
