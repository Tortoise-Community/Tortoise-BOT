import os
import random

import praw
import discord
from discord.ext import commands


class Reddit(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.reddit = praw.Reddit(client_id=os.getenv("PRAW_CLIENT_ID"),
                                  client_secret=os.getenv("PRAW_CLIENT_SECRET"),
                                  user_agent="Tortoise Discord Bot"
                                  )

    @commands.command()
    async def meme(self, ctx):
        """Sends you the dankest of the dank memes from reddit"""
        subreddit = self.reddit.subreddit("memes")
        hot_memes = list(subreddit.hot(limit=100))
        rand_post = random.choice(hot_memes)
        embed = discord.Embed(title=rand_post.title,
                              description=f":thumbsup: {rand_post.score}\n\n:speech_balloon:{len(rand_post.comments)}",
                              url=rand_post.url,
                              colour=0x3498d)
        embed.set_image(url=rand_post.url)
        await ctx.send(embed=embed)

    @commands.command()
    async def newpost(self, ctx, subreddit):
        """Sends you the fresh posts from specific subreddit."""
        sub = self.reddit.subreddit(subreddit)
        new_posts = list(sub.new(limit=10))
        rand_post = random.choice(new_posts)
        embed = discord.Embed(title=rand_post.title,
                              description=f":thumbsup: {rand_post.score}\n\n:speech_balloon: {len(rand_post.comments)}",
                              url=rand_post.url,
                              colour=0x3498d)
        embed.set_image(url=rand_post.url)
        await ctx.send(embed=embed)

    @commands.command()
    async def hotpost(self, ctx, subreddit):
        """sends you the hottest posts from a subreddit."""
        sub = self.reddit.subreddit(subreddit)
        host_posts = list(sub.hot(limit=10))
        rand_post = random.choice(host_posts)
        embed = discord.Embed(title=rand_post.title,
                              description=f":thumbsup: {rand_post.score}\n\n:speech_balloon: {len(rand_post.comments)}",
                              url=rand_post.url,
                              colour=0x3498db)
        embed.set_image(url=rand_post.url)
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Reddit(bot))
