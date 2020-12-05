import discord
from discord.ext import commands

from bot.utils.embed_handler import info


class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def slap(self, ctx, member: discord.Member):
        """Slaps a member."""
        if ctx.author == member:
            embed = info(f"{member.mention} slapped him/her self LOL", ctx.me, "Slap!")
            img_url = "https://media.giphy.com/media/j1zuL4htGTFQY/giphy.gif"
        else:
            embed = info(f"{member.mention} got slapped in the face by: {ctx.author.mention}!", ctx.me, "Slap!")
            img_url = "https://66.media.tumblr.com/05212c10d8ccfc5ab190926912431344/tumblr_mt7zwazvyi1rqfhi2o1_400.gif"
        embed.set_image(url=img_url)
        await ctx.send(embed=embed)

    @commands.command()
    async def shoot(self, ctx, member: discord.Member):
        """Shoots a member."""
        embed = info(f"{member.mention} shot by {ctx.author.mention}  :gun: :boom:", ctx.me, "Boom!")
        embed.set_image(url="https://i.gifer.com/XdhK.gif")
        await ctx.send(embed=embed)

    @commands.command(aliases=["table", "flip"])
    async def throw(self, ctx):
        """Throw a table in anger."""
        await ctx.send("```(╯°□°)╯︵ ┻━┻```")


def setup(bot):
    bot.add_cog(Fun(bot))
