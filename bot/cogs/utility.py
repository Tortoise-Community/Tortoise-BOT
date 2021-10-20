import os

import discord
from async_cse import Search
from discord.ext import commands

from bot.api_client import StackAPI
from bot.utils.paginator import ListPaginator
from bot.constants import upvote_emoji_id, google_icon, stack_overflow_icon


class Utility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.utility_embed_color = 0x3498d
        self.stack_api_client = StackAPI(loop=bot.loop)
        self.google_client = Search(os.getenv("GOOGLE_API_KEY"))

    @commands.command(aliases=["g"])
    async def google(self, ctx, *, query):
        """Searches Google for a query."""
        page_list = []

        await ctx.trigger_typing()
        results = await self.google_client.search(query)
        page_number = 1

        for result in results:
            page_embed = discord.Embed(color=self.utility_embed_color)

            page_embed.title = result.title
            page_embed.description = result.description
            page_embed.url = result.url

            page_embed.set_thumbnail(url=result.image_url)

            page_list.append(page_embed)
            page_number += 1

        paginator = ListPaginator(ctx, page_list, footer_icon=google_icon)
        await paginator.start()

    @commands.command(aliases=["sof", "stack"])
    async def stackoverflow(self, ctx, *, query: str):
        """Searches StackOverflow for a query."""
        page_list = []
        upvote_emoji = self.bot.get_emoji(upvote_emoji_id)

        await ctx.trigger_typing()
        results = await self.stack_api_client.search(query, site="stackoverflow")
        total_answered_count = sum(1 for question in results["items"] if question["is_answered"])

        questions_count = 0
        for question in results["items"]:
            if not question["is_answered"]:
                continue

            questions_count += 1
            embed = discord.Embed(title=question['title'], color=self.utility_embed_color, url=question['link'])
            embed.description = f"{upvote_emoji} {question['score']}  ​​​​ ​💬 {question['answer_count']}"

            embed.set_author(name="StackOverFlow", icon_url=stack_overflow_icon)
            embed.set_footer(text=f"Result {questions_count}/{total_answered_count}")
            page_list.append(embed)

        paginator = ListPaginator(ctx, page_list)
        await paginator.start()


def setup(bot):
    bot.add_cog(Utility(bot))
