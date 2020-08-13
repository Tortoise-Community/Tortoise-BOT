import asyncio
import requests

import discord
from bs4 import BeautifulSoup
from googlesearch import search
from discord.ext import commands

"""
TODO:
long PEP8 breaking links should go to constants.
Use aiohttp as requests is blocking.
googlesearch search is also blocking so either use async version of it or run it in executor.
We have 2 paginators now extend/merge them into one.
names such as m, i..etc are not descriptive
"""

logo_url = (
    "https://www.freepnglogos.com/uploads/google-logo-png/"
    "google-logo-png-google-icon-logo-png-transparent-svg-vector-bie-supply-14.png"
)


class LinkParser:
    def __init__(self):
        self.title = "Click here"
        self.text = "Click on the Above link"
        self.logo_url = logo_url

    def fit(self, link, limit):
        soup = BeautifulSoup(requests.get(link).text, 'lxml')
        desc = soup.find("meta", property="og:description")

        if desc:
            print("desc")
            self.text = desc.get('content')

        if len(self.text) > limit:
            self.text = f"{self.text[:limit]}..."

        if soup.title:
            self.title = str(soup.title.string)

        if soup.head.link:
            self.logo_url = soup.head.link.get("href")


class StackOverFlow:
    def __init__(self):
        self.votes = None
        self.answers = None
        self.title = None
        self.text = None
        self.url = None

    def fit(self, i):
        summary = i.find("div", class_="summary")
        q_dict = summary.find("div", class_="result-link").h3.find('a').attrs

        self.url = f"https://stackoverflow.com/{q_dict['href']}"
        self.title = q_dict['title']
        self.text = i.find("div", class_="excerpt").get_text()
        self.votes = i.find("div", class_="votes").find("span").get_text()

        if i.find("div", class_="status answered"):
            self.answers = i.find("div", class_="status answered").find("strong").get_text()

        elif i.find("div", class_="status unanswered"):
            self.answers = i.find("div", class_="status unanswered").find("strong").get_text()

        elif i.find("div", class_="status answered-accepted"):
            self.answers = i.find("div", class_="status answered-accepted").find("strong").get_text()


class Paginator:
    """Constructs a Paginator when provided a list of Embeds/Messages"""
    def __init__(
            self, ctx: commands.Context, page_list, restart_button="⏮",
            back_button="◀", forward_button="⏭", next_button="▶",
            pause_button="⏸", stop_button="⏹"
    ):
        self.pages = page_list
        self.ctx = ctx
        self.bot = ctx.bot

        self.restart_button = restart_button
        self.back_button = back_button
        self.pause_button = pause_button
        self.forward_button = forward_button
        self.next_button = next_button
        self.stop_button = stop_button

    def get_next_page(self, page):
        pages = self.pages

        if page != pages[-1]:
            current_page_index = pages.index(page)
            next_page = pages[current_page_index+1]
            return next_page

        return pages[-1]

    def get_prev_page(self, page):
        pages = self.pages

        if page != pages[0]:
            current_page_index = pages.index(page)
            next_page = pages[current_page_index-1]
            return next_page

        return pages[0]

    async def start(self):
        pages = self.pages
        ctx = self.ctx

        embed = pages[0]

        msg = await ctx.send(embed=embed)

        emote_list = [self.restart_button, self.back_button, self.pause_button,
                      self.next_button, self.forward_button, self.stop_button]

        for emote in emote_list:
            await msg.add_reaction(emote)

        def check(_reaction, _user):
            return _user == ctx.author and str(_reaction.emoji) in emote_list

        current_page = embed

        try:
            while True:
                reaction, user = await self.bot.wait_for('reaction_add', timeout=60, check=check)

                if str(reaction.emoji) == self.restart_button:
                    await msg.edit(embed=pages[0])
                    current_page = pages[0]
                    await msg.remove_reaction(self.restart_button, ctx.author)
                elif str(reaction.emoji) == self.forward_button:

                    await msg.edit(embed=pages[-1])
                    current_page = pages[-1]

                    await msg.remove_reaction(self.forward_button, ctx.author)
                elif str(reaction.emoji) == self.next_button:
                    next_page = self.get_next_page(current_page)
                    await msg.edit(embed=self.get_next_page(current_page))
                    current_page = next_page

                    await msg.remove_reaction(self.next_button, ctx.author)

                elif str(reaction.emoji) == self.pause_button:
                    await msg.clear_reactions()
                    break

                elif str(reaction.emoji) == self.stop_button:
                    await msg.delete()
                    break

                elif str(reaction.emoji) == self.back_button:
                    prev_page = self.get_prev_page(current_page)
                    await msg.edit(embed=prev_page)
                    current_page = prev_page
                    await msg.remove_reaction(self.back_button, ctx.author)

        except asyncio.TimeoutError:
            await msg.clear_reactions()


class Utility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.color = 0x3498d

    @classmethod
    def is_image(cls, url):
        """Checks if a url is an image"""
        try:
            return str(requests.head(url).headers['Content-Type']).startswith("image")
        except requests.exceptions.MissingSchema:
            return False

    @commands.command(aliases=["g"])
    async def google(self, ctx, *, query):
        """searches google for a query"""
        num = 7

        embed = discord.Embed(color=self.color)
        desc = ""
        page_list = []

        await ctx.message.add_reaction("<a:loading:706195460439933000>")
        loading_msg = await ctx.send(f"🔍 **Searching Google for:** `{query}`")
        m = 1

        for i in search(query, num=num, stop=num, pause=2):

            link_parser = LinkParser()
            link_parser.fit(i, 200)

            page_embed = discord.Embed(color=self.color, title=link_parser.title, url=i)

            if self.is_image(link_parser.logo_url):
                page_embed.set_footer(text=f"Page {m}/5", icon_url=link_parser.logo_url)
            else:
                page_embed.set_footer(text=f"Page {m}/5")

            if "Youtube" not in link_parser.title:
                page_embed.description = link_parser.text

            page_list.append(page_embed)
            desc += f"[Result {m}]({i})\n"
            m += 1

        embed.description = desc
        embed.title = f"🔍 Found {len(page_list)} results"
        embed.set_footer(
            text="Google",
            icon_url=logo_url
        )

        await loading_msg.delete()
        await ctx.message.remove_reaction("<a:loading:706195460439933000>", self.bot.user)

        paginator = Paginator(ctx, page_list)
        await paginator.start()

    @commands.command(aliases=["sof", "stackof"])
    async def stackoverflow(self, ctx, *, query):
        """ Searches stackoverflow for a query"""

        msg = await ctx.send(f"Searching for `{query}`")

        limit = 5
        search_url = f"https://stackoverflow.com/search?q={str(query).replace(' ', '+')}"
        content = requests.get(search_url).content

        soup = BeautifulSoup(content, "lxml")

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
