import os
import praw
import random

from discord.ext import commands

from bot.cogs.utils.embed_handler import reddit_embed


class Reddit(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.reddit = praw.Reddit(
            client_id=os.getenv("PRAW_CLIENT_ID"),
            client_secret=os.getenv("PRAW_CLIENT_SECRET"),
            user_agent="Tortoise Discord Bot"
        )

    @commands.command()
    async def meme(self, ctx):
        """Sends you the dankest of the dank memes from reddit"""
        subreddit = self.reddit.subreddit("memes")
        hot_memes = list(subreddit.hot(limit=100))
        rand_post = random.choice(hot_memes)
        embed = await reddit_embed(ctx, rand_post)
        await ctx.send(embed=embed)

    @commands.command()
    async def newpost(self, ctx, subreddit):
        """Sends you the fresh posts from specific subreddit."""
        sub = self.reddit.subreddit(subreddit)
        new_posts = list(sub.new(limit=10))
        rand_post = random.choice(new_posts)
        embed = await reddit_embed(ctx, rand_post)
        await ctx.send(embed=embed)

    @commands.command()
    async def hotpost(self, ctx, subreddit):
        """sends you the hottest posts from a subreddit."""
        sub = self.reddit.subreddit(subreddit)
        host_posts = list(sub.hot(limit=10))
        rand_post = random.choice(host_posts)
        embed = await reddit_embed(ctx, rand_post)
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Reddit(bot))
