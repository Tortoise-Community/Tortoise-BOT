import discord
from discord.ext import commands

github_repo_link = "https://github.com/Tortoise-Community/Tortoise-BOT"
sidekick_bot_id = 577140178791956500


class Other(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def say(self, ctx, *, arg):
        """Says something"""

        await ctx.message.delete()
        await ctx.send(arg)

    @commands.command()
    async def members(self, ctx):
        """Returns the number of members in a server."""
        await ctx.send(f'```{ctx.guild.member_count}```')

    @commands.command()
    async def status(self, ctx, *, member: discord.Member):
        """Returns the status of a member."""

        if member.id == sidekick_bot_id:
            await ctx.send("**I AM ONLINE , CAN'T YOU SEE?**")
        elif member.is_on_mobile():
            await ctx.send(f"```{member} is {member.status} but is on phone.```")
        else:
            await ctx.send(f"```{member} is {member.status}.```")

    @commands.command()
    async def pfp(self, ctx, *, member: discord.Member = None):
        """Displays the profile picture of a member."""

        if member is None:
            await ctx.send(f"Your avatar {ctx.author.avatar_url}")
        elif member == ctx.me:
            await ctx.send(f"My avatar {member.avatar_url}")
        else:
            await ctx.send(f"{member} avatar {member.avatar_url}")

    @commands.command()
    async def github(self, ctx):
        """GitHub repository"""

        embed = discord.Embed(title="""Tortoise-BOT github repository""", url=github_repo_link, color=0x206694)
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Other(bot))
