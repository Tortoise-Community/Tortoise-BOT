import discord
from discord.ext import commands


class TortoiseServer(commands.Cog):
    """These commands will only work in the tortoise discord server."""
    def __init__(self, bot):
        self.bot = bot
       
    announcements_channel_id = 578197131526144024
    welcome_channel_id = 591662973307584513
  
    @commands.command()
    @commands.guild_only()
    async def submit(self, ctx):
        """Initializes process of submitting code for event."""
        await ctx.author.send("Submitting process has begun.\n\n"
                              "Please reply with 1 message below that either contains your full code "
                              "or , if it's too long, contains a link to code (pastebin/hastebin..)\n"
                              "If using those services make sure to set code to private and "
                              "expiration date to at least 30 days")

        def check(msg):
            return msg.author == ctx.author and msg.guild is None

        try:
            code_msg = await self.bot.wait_for("message", check=check, timeout=300)
        except TimeoutError:
            await ctx.send("You took too long to reply.")
            return

        event_submission_channel = self.bot.get_channel(self.bot.config.get_key("event_submission_channel_id"))

        title = f"Submission from {ctx.author}"
        embed = discord.Embed(title=title, description=code_msg.content, color=ctx.me.top_role.color)
        embed.set_thumbnail(url=ctx.author.avatar_url)

        await event_submission_channel.send(embed=embed)

        
    @commands.command()
    @commands.has_role('Admin')
    async def count(self, ctx, start: int):
        await ctx.message.delete()
        message = await ctx.send(start)
        while start:
            minutes, secs = divmod(start, 60)
            content = "{:02d}:{:02d}".format(minutes, secs)
            await message.edit(content=content)
            start -= 1
            await asyncio.sleep(1)
        await message.delete()

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def announce(self, ctx, *, arg):
        announcements_channel = self.bot.get_channel(announcements_channel_id)
        await announcements_channel.send(arg)
        await ctx.send("Announced ✅")  
        
    @commands.command()
    @commands.has_role("Admin")
    async def welcome(self, ctx, *, arg):
        channel = self.bot.get_channel(welcome_channel_id)
        await channel.send(arg)
        await ctx.send("Added in Welcome ✅")
    
    @commands.command()
    @commands.dm_only()
    async def report(self, ctx):
        data = get_data()
        for user in data["reporters"]:
            if user["user_id"] == ctx.author.id and user["status"] == "false":
                await ctx.send(embed=errorbed)
                return
        channel = self.client.get_channel(580809054067097600)
        await ctx.send(embed=membed)
        create_issue(ctx.author.id)
        embed = discord.Embed(title=f"**Report Opened!**", description=f"{ctx.author.mention} opened a report.\n\nType in `t.attend` to attend the report.", color=0xF2771A)
        embed.set_author(name="Mod-Mail", icon_url=ctx.me.avatar_url)
        await channel.send(f"<@&605808609128873985>")
        await channel.send(embed=embed)
    
def setup(bot):
    bot.add_cog(TortoiseServer(bot))
