import asyncio
import aiohttp

import discord
from bs4 import BeautifulSoup
from async_cse import Search
from discord.ext import commands
import os

from bot.constants import upvote_emoji_id, google_icon, stackof_icon
from bot.cogs.utils.paginator import ListPaginator


class StackOverFlow:
    def __init__(self):
        self.votes = None
        self.answers = None
        self.title = None
        self.text = None
        self.url = None

    def fit(self, soup):
        summary = soup.find("div", class_="summary")
        q_dict = summary.find("div", class_="result-link").h3.find('a').attrs

        self.url = f"https://stackoverflow.com/{q_dict['href']}"
        self.title = q_dict['title']
        self.text = soup.find("div", class_="excerpt").get_text()
        self.votes = soup.find("div", class_="votes").find("span").get_text()

        if soup.find("div", class_="status answered"):
            self.answers = soup.find("div", class_="status answered").find("strong").get_text()

        elif soup.find("div", class_="status unanswered"):
            self.answers = soup.find("div", class_="status unanswered").find("strong").get_text()

        elif soup.find("div", class_="status answered-accepted"):
            self.answers = soup.find("div", class_="status answered-accepted").find("strong").get_text()


class Utility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.color = 0x3498d
        self.google_api_key = os.getenv("GOOGLE_API_KEY")
        self.google_client = Search(self.google_api_key)


    @commands.command(aliases=["g"])
    async def google(self, ctx, *, query):
        """searches google for a query"""

        page_list = []

        loading_msg = await ctx.send(f"🔍 **Searching Google for:** `{query}`")
        results = await self.google_client.search(query)
        page_number = 1

        for result in results:
            page_embed = discord.Embed(color= self.color)

            page_embed.title = result.title
            page_embed.description = result.description
            page_embed.url = result.url

            page_embed.set_thumbnail(url = result.image_url)
            page_embed.set_footer(text=f"Page {page_number}/{len(results)}",icon_url=google_icon)

            page_list.append(page_embed)
            page_number += 1

        await loading_msg.delete()
        paginator = ListPaginator(ctx, page_list)
        await paginator.start()


    @commands.command(aliases=["sof", "stackof"])
    async def stackoverflow(self, ctx, *, query):
        """ Searches stackoverflow for a query"""



        msg = await ctx.send(f"Searching for `{query}`")

        limit = 5
        search_url = f"https://stackoverflow.com/search?q={str(query).replace(' ', '+')}"

        resp_text = ""

        async with aiohttp.ClientSession() as session:
            async with session.get(search_url) as resp:
                resp_text = await resp.text()



        soup = BeautifulSoup(resp_text, "lxml")

        m = 1

        page_list = []

        for i in soup.find_all("div", class_="question-summary search-result")[:limit]:
            sof = StackOverFlow()
            sof.fit(i)

            embed = discord.Embed(color=self.color, title=sof.title, url=sof.url)

            embed.description = f"{sof.text}\n\n<:upvote:741202481090002994> {sof.votes}  ​​​​ ​💬 {sof.answers}"

            embed.set_author(
                name="StackOverFlow",
                icon_url="https://cdn2.iconfinder.com/data/icons/social-icons-color/512/stackoverflow-512.png"
            )
            embed.set_footer(
                text=f"Page {m}/{len(soup.find_all('div', class_='question-summary search-result')[:limit])}")

            page_list.append(embed)

            m += 1

        paginator = Paginator(ctx, page_list)
        await msg.delete()
        await paginator.start()


def setup(bot):
    bot.add_cog(Utility(bot))
