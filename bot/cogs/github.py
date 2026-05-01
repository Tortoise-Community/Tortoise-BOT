import re
import datetime
import logging
import aiohttp.client_exceptions

import discord
from discord.ext import commands, tasks
from discord import app_commands

from bot.api_client import GithubAPI
from bot.utils.embed_handler import project_embed


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
        "name": "Runtime-Bot",
        "html_url": "https://github.com/Tortoise-Community/Runtime-Bot",
        "web_link": "https://github.com/Tortoise-Community/Runtime-Bot",
        "forks_count": 1,
        "commit_count": 4,
        "stargazers_count": 1,
        "contributors_count": 1,
        "language": "Python",
        "short_desc": "Discord bot for executing code directly in chat using the Hermes sandbox engine.",
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
        "html_url": "https://github.com/Bladelist/Bladelist",
        "web_link": "https://github.com/Bladelist/Bladelist",
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
        self._load_static()
        self.update_static_projects.start()


    def _load_static(self):
        try:
            for project_stats in STATIC_PROJECTS_DATA:
                item = Project(project_stats)
                self.projects[item.name] = item

            self.projects["last_updated"] = datetime.datetime.now()

        except Exception as e:
            logging.error(f"Failed loading static GitHub data: {e}")

    def cog_unload(self):
        self.update_static_projects.cancel()

    @tasks.loop(hours=6)
    async def update_static_projects(self):
        headers = {"User-Agent": "Tortoise-Discord-Bot"}
        async with aiohttp.ClientSession(headers=headers) as session:
            for project in STATIC_PROJECTS_DATA:
                try:
                    parts = project['html_url'].rstrip('/').split('/')
                    repo_path = f"{parts[-2]}/{parts[-1]}"

                    api_url = f"https://api.github.com/repos/{repo_path}"
                    # These data are available from API directly
                    async with session.get(api_url) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            project['stargazers_count'] = data.get('stargazers_count', 0)
                            project['forks_count'] = data.get('forks_count', 0)
                            project['language'] = data.get('language', 'Python')

                    # Fetch Commit Count (Efficiently via Link Header)
                    commits_url = f"{api_url}/commits?per_page=1"
                    async with session.get(commits_url) as resp:
                        link_header = resp.headers.get('Link', '')
                        if 'rel="last"' in link_header:
                            match = re.search(r'page=(\d+)[^>]*>;\s*rel="last"', link_header)
                            project['commit_count'] = int(match.group(1)) if match else 1
                        else:
                            commits = await resp.json()
                            project['commit_count'] = len(commits) if isinstance(commits, list) else 0

                    item = Project(project)
                    self.projects[item.name] = item

                except Exception as e:
                    logging.error(f"Failed to background update {project['name']}: {e}")

            self.projects["last_updated"] = datetime.datetime.now()
            logging.info("GitHub static projects data refreshed.")

    @update_static_projects.before_loop
    async def before_update_static_projects(self):
        await self.bot.wait_until_ready()

    async def _github_handler(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            embed=project_embed(self.projects, interaction.client.user)
        )

    @app_commands.command(name="github", description="Show Tortoise GitHub projects stats.")
    async def github(self, interaction: discord.Interaction):
        await self._github_handler(interaction)

    @app_commands.command(name="git", description="Alias for /github")
    async def git(self, interaction: discord.Interaction):
        await self._github_handler(interaction)



async def setup(bot):
    await bot.add_cog(Github(bot))
