import os
import aiohttp
import json

import discord
from async_cse import Search
from bs4 import BeautifulSoup
from discord.ext import commands

from bot.utils.paginator import ListPaginator
from bot.constants import upvote_emoji_id, google_icon, stackof_icon



class Question:
    def __init__(self, **kwargs):
        self.votes = kwargs["votes"]
        self.answers = kwargs["answers"]
        self.title = kwargs["title"]
        self.url = kwargs["url"]

    @staticmethod
    def from_json(json_dict,limit= 10):
        json_dict = json.loads(json_dict)
        items = json_dict["items"]
        questions = []

        for item in items:
            if item["is_answered"]:
               question = Question(votes=item["score"],
                               answers=item["answer_count"],
                               title = item["title"],url = item["link"])
               questions.append(question)


        if len(questions) < limit:
            return questions
        else:
            return questions[:limit]


class StackOverFlow:
    def __init__(self,num_questions = 10):
        self.num_questions = num_questions

    async def search(self, keyword):
        search_url = f"https://api.stackexchange.com/2.2/search/advanced?order=desc&sort=activity&title={keyword}&site=stackoverflow"
        async with aiohttp.ClientSession() as session:
            async with session.get(search_url) as resp:
                self.resp_text = await resp.text()

        results = Question.from_json(self.resp_text,limit= self.num_questions)
        return results


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
            page_embed = discord.Embed(color=self.color)

            page_embed.title = result.title
            page_embed.description = result.description
            page_embed.url = result.url

            page_embed.set_thumbnail(url=result.image_url)
            page_embed.set_footer(text=f"Page {page_number}/{len(results)}", icon_url=google_icon)

            page_list.append(page_embed)
            page_number += 1

        await loading_msg.delete()
        paginator = ListPaginator(ctx, page_list)
        await paginator.start()

    @commands.command(aliases=["sof", "stack"])
    async def stackoverflow(self, ctx, *, query):
        """ Searches stackoverflow for a query"""

        msg = await ctx.send(f"Searching for `{query}`")
        upvote_emoji = self.bot.get_emoji(upvote_emoji_id)
        stackof = StackOverFlow()
        page_list = []
        results = await stackof.search(query)

        for result in results:
            embed = discord.Embed(color=self.color, title=result.title, url=result.url)
            embed.description = f"{upvote_emoji} {result.votes}  ​​​​ ​💬 {result.answers}"

            embed.set_author(name="StackOverFlow", icon_url=stackof_icon)
            embed.set_footer(text=f"Page {results.index(result)}/{len(results)}")
            page_list.append(embed)

        paginator = ListPaginator(ctx, page_list)
        await msg.delete()
        await paginator.start()


def setup(bot):
    bot.add_cog(Utility(bot))
