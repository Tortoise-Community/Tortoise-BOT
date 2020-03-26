import logging
import discord
from discord.ext import commands
from .utils.checks import check_if_it_is_tortoise_guild
from .utils.embed_handler import success, failure, authored

logger = logging.getLogger(__name__)


announcements_channel_id = 578197131526144024
welcome_channel_id = 657704940080201739
event_submission_channel_id = 610079185569841153
react_for_roles_channel_id = 603651772950773761
# Keys are IDs of reaction emojis, values are role IDs which will get
# added if that reaction gets added/removed
self_assignable_roles = {
    582547250635603988: 589128905290547217,     # python
    603276308084031511: 589129070609039454,     # java
    603647289902366723: 589129970820055080,     # go
    603276263414562836: 589129320480636986,     # javascript
    603274583772233728: 589808988506554398,     # rust
    603274784805224478: 591254311162347561,     # hmtl
    603278259517390880: 589131517683433485,     # css
    603277646234779658: 589129183494406154,     # php
    603277725679222819: 589131126619111424,     # sql
    603277676714786914: 589131390944280577,     # ruby
    603275563972689942: 589131022520811523,     # c
    603275529587654665: 589129873809735700,     # c++
    603275597514407941: 589130125208190991,     # c#
    603277763293609990: 589129583375286415,     # r
    610825682070798359: 610834658267103262,     # events
    583614910215356416: 603157798225838101      # announcements
}


class TortoiseServer(commands.Cog):
    """These commands will only work in the tortoise discord server."""
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.channel_id == react_for_roles_channel_id:
            guild = self.bot.get_guild(payload.guild_id)
            member = guild.get_member(payload.user_id)
            role = self.get_assignable_role(payload, guild)
            if role is not None:
                await member.add_roles(role)
                embed = success(f"`**{role.name}**` has been assigned to you in the Tortoise community.")
                await member.send(embed=embed)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        if payload.channel_id == react_for_roles_channel_id:
            guild = self.bot.get_guild(payload.guild_id)
            member = guild.get_member(payload.user_id)
            role = self.get_assignable_role(payload, guild)
            if role is not None:
                await member.remove_roles(role)

    @classmethod
    def get_assignable_role(cls, payload, guild):
        role_id = self_assignable_roles.get(payload.emoji.id)
        if role_id is not None:
            role = guild.get_role(role_id)
            if role is not None:
                return role
            else:
                logger.critical(f"Emoji id found in dictionary but role id {role_id} not found in guild!")
        else:
            logger.critical(f"No mapping for emoji {payload.emoji.id} in self_assignable_roles!")

    @commands.command()
    @commands.check(check_if_it_is_tortoise_guild)
    async def submit(self, ctx):
        """Initializes process of submitting code for event."""
        dm_msg = ("Submitting process has begun.\n\n"
                  "Please reply with 1 message below that either contains your full code or, "
                  "if it's too long, contains a link to code (pastebin/hastebin..)\n"
                  "If using those services make sure to set code to private and "
                  "expiration date to at least 30 days.")
        await ctx.author.send(embed=authored(ctx.guild.me, dm_msg))

        def check(msg):
            return msg.author == ctx.author and msg.guild is None

        try:
            code_msg = await self.bot.wait_for("message", check=check, timeout=300)
        except TimeoutError:
            await ctx.send(embed=failure("You took too long to reply."))
            return

        event_submission_channel = self.bot.get_channel(event_submission_channel_id)

        title = f"Submission from {ctx.author}"
        embed = discord.Embed(title=title, description=code_msg.content, color=ctx.me.top_role.color)
        embed.set_thumbnail(url=ctx.author.avatar_url)

        await event_submission_channel.send(embed=embed)

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    @commands.check(check_if_it_is_tortoise_guild)
    async def announce(self, ctx, *, arg):
        announcements_channel = self.bot.get_channel(announcements_channel_id)
        await announcements_channel.send(arg)
        await ctx.send(success("Announced ✅"))

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    @commands.check(check_if_it_is_tortoise_guild)
    async def welcome(self, ctx, *, arg):
        channel = self.bot.get_channel(welcome_channel_id)
        await channel.send(arg)
        await ctx.send(success("Added in Welcome ✅"))


def setup(bot):
    bot.add_cog(TortoiseServer(bot))
