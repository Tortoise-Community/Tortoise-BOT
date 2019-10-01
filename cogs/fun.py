import discord
from discord.ext import commands

fwiz_id = 247292930346319872


class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def slap(self, ctx, member: discord.Member):
        """Slaps a member."""
        if ctx.author == member:
            await ctx.send(f"{member.mention} slapped him/her self LOL")
        elif member.id == fwiz_id:
            embed = discord.Embed(description=f"{ctx.message.author.mention} Nah you can't slap my dad!....."
                                              f"wait I will kick him in the balls for you ;-)")
            embed.set_image(url="https://media.giphy.com/media/3o7TKwVQMoQh2At9qU/giphy.gif")
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(description=f"{member.mention} got slapped in the face by: {ctx.message.author.mention}!")
            embed.set_image(
                url="https://66.media.tumblr.com/05212c10d8ccfc5ab190926912431344/tumblr_mt7zwazvyi1rqfhi2o1_400.gif")
            await ctx.send(embed=embed)

    @commands.command()
    async def shoot(self, ctx, member: discord.Member):
        """Shoots a member."""

        if ctx.author.id == fwiz_id and member.id == fwiz_id:
            embed = discord.Embed(description=f"{member.mention} DAD! DON'T SHOOT YOURSELF!")
            embed.set_image(url="https://media.giphy.com/media/f2fVSJWddYb6g/giphy.gif")
            await ctx.send(embed=embed)
        elif member.id == fwiz_id:
            embed = discord.Embed(description=f"{ctx.author.mention} Anyday!")
            embed.set_image(url="https://media.giphy.com/media/oQfhD732U71YI/giphy.gif")
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                description=f"{member.mention} shot by {ctx.author.mention}  :gun: :boom:")
            embed.set_image(url='https://i.gifer.com/XdhK.gif')
            await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Fun(bot))
