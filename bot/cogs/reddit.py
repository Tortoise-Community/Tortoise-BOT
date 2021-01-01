import os
import random
import datetime
from typing import List, AsyncGenerator

import asyncpraw
from discord.ext import commands
from asyncpraw.models import Subreddit, Submission

from bot.utils.embed_handler import reddit_embed


class RedditPostsCache:
    def __init__(self, max_size: int = 10):
        """
        Class to cache posts from subreddit.
        Idea is to cache posts from subreddit while not eating lot of memory, thus param max_size.
        However it's not good to get same posts all over the time if you're accessing cache often (since default posts
        cached is 100 so sooner or later you'll get duplicates). Thus when getting post from cache for specific
        subreddit said post is actually removed from cache so it cannot be duplicated again.
        If getting post from cache and there is only one post then cache will fetch posts again (hopefully enough time
        passed and there are new ones).
        You can also specify how much time needs to pass since last posts were fetched when getting posts from cache.
        If said time has passed the post cache for specific subreddit will get refreshed.
        :param max_size: maximum number of subreddits to cache.
                         When exceeded the oldest (first) subreddit gets deleted.
        """
        self._max_size = max_size
        self._cache = {}

    def cache_subreddit(self, subreddit: Subreddit, subreddit_posts: List[Submission]):
        """
        Adds subreddit to cache. If already exists then overwrites.
        :param subreddit: Subreddit object that will get cached
        :param subreddit_posts: list of submissions from subreddit that you want to cache
        """
        self._cache[subreddit.display_name] = {
            "posts": subreddit_posts,
            "last_updated": datetime.datetime.now()
        }

        # Remove first key
        if len(self._cache) > self._max_size:
            del self._cache[next(iter(self._cache))]

    def should_update(self, subreddit: Subreddit, *, hour_interval: int) -> bool:
        """
        :param subreddit: subreddit to check.
        :param hour_interval: integer representing hours
        :return: bool whether 'hour_interval' has passed since the last update of specified subreddit cache.
                 If passed subreddit does not exist in cache then returns True.
                 If posts for subreddit have been reduced to 1 it will also return True.
        """
        subreddit_data = self._cache.get(subreddit.display_name)
        if subreddit_data is None:
            return True
        elif len(self._cache[subreddit.display_name]["posts"]) == 1:
            return True

        hours_since_last_update = (datetime.datetime.now() - subreddit_data["last_updated"]).seconds // 3600
        return hours_since_last_update >= hour_interval

    def get_random_post(self, subreddit: Subreddit) -> Submission:
        """
        Get a random post for specific subreddit from cache.
        Removes post to be returned from cache to reduce getting duplicates.
        :param subreddit: Subreddit to get the post from
        :return: random Submission (post)
        :raises: KeyError the specified subreddit is not cached
        """
        posts = self._cache[subreddit.display_name]["posts"]
        random_post = random.choice(posts)
        posts.remove(random_post)
        return random_post


class Reddit(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.reddit = asyncpraw.Reddit(
            client_id=os.getenv("PRAW_CLIENT_ID"),
            client_secret=os.getenv("PRAW_CLIENT_SECRET"),
            user_agent="Tortoise Discord Bot",
        )
        self._cache = RedditPostsCache()

    async def _post_cache_helper(
            self,
            ctx,
            subreddit: Subreddit,
            post_generator: AsyncGenerator,
            hour_interval: int = 6
    ) -> Submission:
        """
        Get random post for specific subreddit.
        :param ctx: context from dpy command, used to trigger typing when loading posts. Purely cosmetic thing.
        :param subreddit: Subreddit object we want to get post from. If one does not exist in cache then we
                          fetch posts for that subreddit and cache them. Number of posts fetched is 100.
        :param post_generator: when fetching posts which generator to use? Example would be subreddit.hot(),
                               subreddit.new() etc.
        :param hour_interval: integer representing hours. Default value is 6.
                              If this many hours has passed since the last cached posts update for specific subreddit
                              then before getting random post we'll fetch posts again (aka update them).
        :return: Submission, aka random post
        """
        if self._cache.should_update(subreddit, hour_interval=hour_interval):
            await ctx.channel.trigger_typing()
            self._cache.cache_subreddit(subreddit, [meme async for meme in post_generator])

        return self._cache.get_random_post(subreddit)

    """
    @BrainDead - 
    Maybe for these commands below, you could add something that detects
    whether the command is taking too long to run?
    Like say maybe if the command output doesn't pop up in the channel for 10 or more seconds,
    you could send a message that says something like 'Command took too long to run. Maybe try again? Or report this issue to the developers?'
    """
    
    
    @commands.command()
    async def meme(self, ctx):
        """Sends you the dankest of the dank memes from reddit."""
        subreddit = await self.reddit.subreddit("dankmemes")
        rand_post = await self._post_cache_helper(ctx, subreddit, subreddit.hot())
        embed = await reddit_embed(ctx, rand_post)
        await ctx.send(embed=embed)

    @commands.command()
    async def newpost(self, ctx, subreddit: str):
        """Sends you new posts from a subreddit."""
        subreddit = await self.reddit.subreddit(subreddit)
        rand_post = await self._post_cache_helper(ctx, subreddit, subreddit.new(), 1)
        embed = await reddit_embed(ctx, rand_post)
        await ctx.send(embed=embed)

    @commands.command()
    async def hotpost(self, ctx, subreddit: str):
        """Sends you hot posts from a subreddit."""
        subreddit = await self.reddit.subreddit(subreddit)
        rand_post = await self._post_cache_helper(ctx, subreddit, subreddit.new())
        embed = await reddit_embed(ctx, rand_post)
        await ctx.send(embed=embed)

    @commands.command()
    async def toppost(self, ctx, subreddit: str):
        """Sends you top posts of all time from a subreddit."""
        subreddit = await self.reddit.subreddit(subreddit)
        rand_post = await self._post_cache_helper(ctx, subreddit, subreddit.top())
        embed = await reddit_embed(ctx, rand_post)
        await ctx.send(embed=embed)

    @commands.command()
    async def controversialpost(self, ctx, subreddit: str):
        """sends you controversial posts from a subreddit."""
        subreddit = await self.reddit.subreddit(subreddit)
        rand_post = await self._post_cache_helper(ctx, subreddit, subreddit.controversial())
        embed = await reddit_embed(ctx, rand_post)
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Reddit(bot))
