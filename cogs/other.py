import psutil
import time
import os
import discord
from discord.ext import commands
from .utils.embed_handler import info

github_repo_link = "https://github.com/Tortoise-Community/Tortoise-BOT"


class Other(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.process = psutil.Process(os.getpid())

    @commands.command()
    async def say(self, ctx, *, message):
        """Says something"""
        await ctx.message.delete()
        await ctx.send(message)

    @commands.command()
    async def members(self, ctx):
        """Returns the number of members in a server."""
        await ctx.send(embed=info(f"{ctx.guild.member_count}", ctx.me, "Member count"))

    @commands.command()
    async def status(self, ctx, member: discord.Member = None):
        """Returns the status of a member."""
        roles_ = ""

        def rolls(rolelist):
            stuff = ""
            for i in rolelist:
                stuff += i.mention
            return stuff

        def activ(member):

            if member.activity == None:
                return None

            elif member.activity.type  != discord.ActivityType.custom:
                text = f"{member.activity.type.name} {member.activity.name}"
                return text
            else:
                return member.activity.name
            
            

        def stat(member):
            if member.status == discord.Status.dnd:
                return "DND 🔴"

            elif  member.status == discord.Status.online:
                return "ONLINE 🟢 "

            elif member.status == discord.Status.idle:
                return "IDLE 🌙 "

            elif member.status == discord.Status.offline:
                return "OFFLINE 💀 "










            

                


        async def custom_status(desc):
            if member.is_on_mobile() and member.status != discord.Status.offline:
                embed = discord.Embed(title=member.display_name,
                                      description=desc, color=member.top_role.color)
                embed.add_field(name='**DEVICE **', value='Phone: :iphone:  ')
                embed.add_field(name="|", value="_ _ ")
                # embed.set_author(member.display_name)
                embed.add_field(name='**STATUS**', value=stat(member=member))
                embed.add_field(name="**JOINED SERVER AT**", value=member.joined_at)
                embed.add_field(name="|", value="_ _ ")
                embed.add_field(name="**ROLES**", value=rolls(member.roles))
                embed.add_field(name="**ACTIVITY**", value=activ(member=member))

                embed.set_thumbnail(url=member.avatar_url)

                await ctx.send(embed=embed)

            elif member.status != discord.Status.offline:
                # await ctx.send(f"```{member} is {member.status}```")
                embed = discord.Embed(title=member.display_name,
                                      description=desc, color=member.top_role.color)
                embed.add_field(name='**DEVICE **', value='PC:  :desktop:  ')
                embed.add_field(name="|", value="_ _  ")
                embed.add_field(name='**STATUS**', value=stat(member=member))
                embed.add_field(name="**JOINED SERVER AT**", value=member.joined_at)
                embed.add_field(name="|", value="_ _ ")
                embed.add_field(name="**ROLES**", value=rolls(member.roles))
                embed.add_field(name="**ACTIVITY**", value=activ(member=member))
                embed.set_thumbnail(url=member.avatar_url)

                # embed.set_author(name=member.display_name,url=member.avatar_url)

                # embed.set_author(member.display_name)
                await ctx.send(embed=embed)

            elif member.status == discord.Status.offline:
                embed = discord.Embed(title=member.display_name,
                                      description=desc, color=member.top_role.color)
                embed.add_field(name='Device', value=':no_entry:  ')
                embed.add_field(name="|", value="_ _ ")
                embed.add_field(name='**STATUS**', value=stat(member=member))
                embed.add_field(name="**JOINED SERVER AT**", value=member.joined_at)
                embed.add_field(name="|", value="_ _ ")
                embed.add_field(name="**ROLES**", value=rolls(member.roles))
                embed.add_field(name="**ACTIVITY**", value=activ(member=member))
                embed.set_thumbnail(url=member.avatar_url)

                await ctx.send(embed=embed)

        if member.id == 577140178791956500:
            await custom_status(desc="bunny waifu")
            
        elif member.id == 247292930346319872:  # fwizz custom
            await custom_status(desc=" Usagis father ")

          


        elif member.is_on_mobile() and member.status != discord.Status.offline:
            embed = discord.Embed(title=member.display_name, color=member.top_role.color)
            embed.add_field(name='**DEVICE **', value='Phone: :iphone:  ')
            embed.add_field(name="|", value="_ _ ")
            # embed.set_author(member.display_name)
            embed.add_field(name='**STATUS**', value=stat(member=member))
            embed.add_field(name="**JOINED SERVER AT**", value=member.joined_at)
            embed.set_thumbnail(url=member.avatar_url)
            embed.add_field(name="|", value="_ _ ")
            embed.add_field(name="**ROLES**", value=rolls(member.roles))
            embed.add_field(name="**ACTIVITY**", value=activ(member=member))
            await ctx.send(embed=embed)





        elif member.status != discord.Status.offline:
            # await ctx.send(f"```{member} is {member.status}```")
            embed = discord.Embed(title=member.display_name, color=member.top_role.color)
            embed.add_field(name='**DEVICE **', value='PC:  :desktop:  ')
            embed.add_field(name="|", value="_ _ ")
            embed.add_field(name='**STATUS**', value=stat(member=member))
            embed.add_field(name="**JOINED SERVER AT**", value=member.joined_at)
            embed.add_field(name="|", value="_ _ ")
            embed.add_field(name="**ROLES**", value=rolls(member.roles))
            embed.add_field(name="**ACTIVITY**", value=activ(member=member))
            embed.set_thumbnail(url=member.avatar_url)

            # embed.set_author(name=member.display_name,url=member.avatar_url)

            # embed.set_author(member.display_name)
            await ctx.send(embed=embed)

        elif member.status == discord.Status.offline:
            embed = discord.Embed(title=member.display_name, color=member.top_role.color)
            embed.add_field(name='Device', value=':no_entry:  ')
            embed.add_field(name="|", value="_ _ ")
            embed.add_field(name='**STATUS**', value=stat(member=member))
            embed.add_field(name="**JOINED SERVER AT**", value=member.joined_at)
            embed.add_field(name="|", value="_ _ ")
            embed.add_field(name="**ROLES**", value=rolls(member.roles))
            embed.add_field(name="**ACTIVITY**", value=activ(member=member))
            embed.set_thumbnail(url=member.avatar_url)

            await ctx.send(embed=embed)

    @commands.command()
    async def pfp(self, ctx, member: discord.Member = None):
        """Displays the profile picture of a member."""
        if member is None:
            message, url = "Your avatar", ctx.author.avatar_url
        elif member == ctx.me:
            message, url = "My avatar", member.avatar_url
        else:
            message, url = f"{member} avatar", member.avatar_url

        embed = info(message, ctx.me)
        embed.set_image(url=url)
        await ctx.send(embed=embed)

    @commands.command(aliases=["git"])
    async def github(self, ctx):
        """GitHub repository"""
        embed = info(f"[Tortoise github repository]({github_repo_link})", ctx.me, "Github")
        await ctx.send(embed=embed)

    @commands.command()
    async def ping(self, ctx):
        """Replies to a ping."""
        start = time.perf_counter()
        message = await ctx.send(embed=info("Pong!", ctx.me))
        end = time.perf_counter()
        duration = (end - start) * 1000
        await message.edit(embed=info(f":ping_pong: {duration:.2f}ms", ctx.me, "Pong!"))

    @commands.command()
    @commands.cooldown(1, 10, commands.BucketType.guild)
    async def stats(self, ctx):
        """
        Show bot information (stats/links/etc).
        """
        bot_ram_usage = self.process.memory_full_info().rss / 1024 ** 2
        bot_ram_usage = f"{bot_ram_usage:.2f} MB"

        virtual_memory = psutil.virtual_memory()
        server_ram_usage = f"{virtual_memory.used / 1024 / 1024:.0f} MB"
        total_server_ram = f"{virtual_memory.total / 1024 / 1024:.0f} MB"

        cpu_count = psutil.cpu_count()

        bot_cpu_usage = self.process.cpu_percent()
        if bot_cpu_usage > 100:
            bot_cpu_usage = bot_cpu_usage / cpu_count

        server_cpu_usage = psutil.cpu_percent()
        if server_cpu_usage > 100:
            server_cpu_usage = server_cpu_usage / cpu_count

        io_counters = self.process.io_counters()
        io_read_bytes = f"{io_counters.read_bytes / 1024 / 1024:.3f}MB"
        io_write_bytes = f"{io_counters.write_bytes / 1024 / 1024:.3f}MB"

        msg = (f"Bot RAM usage: {bot_ram_usage}\n"
               f"Server RAM usage: {server_ram_usage}\n"
               f"Total server RAM: {total_server_ram}\n"
               f"Bot CPU usage: {bot_cpu_usage}\n"
               f"Server CPU usage: {server_cpu_usage}\n"
               f"IO (r/w): {io_read_bytes} / {io_write_bytes}")

        await ctx.send(f"```{msg}```")


def setup(bot):
    bot.add_cog(Other(bot))
