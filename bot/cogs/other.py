import os
import time
import asyncio

import psutil
import discord
from discord.ext import commands

from bot.cogs.utils.embed_handler import info, status_embed
from bot.constants import github_repo_link, embed_space, tortoise_paste_service_link


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
        if member is None:
            member = ctx.author

        if member.id == 577140178791956500:
            embed = status_embed(member, description="waifu")
        elif member.id == 247292930346319872:
            embed = status_embed(member, description="Not telling")
        else:
            embed = status_embed(member)

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
        """Shows bot ping."""
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
        bot_ram_usage_field = self.construct_load_bar_string(self.process.memory_percent(), bot_ram_usage)

        virtual_memory = psutil.virtual_memory()
        server_ram_usage = f"{virtual_memory.used/1024/1024:.0f} MB"
        server_ram_usage_field = self.construct_load_bar_string(virtual_memory.percent, server_ram_usage)

        cpu_count = psutil.cpu_count()

        bot_cpu_usage = self.process.cpu_percent()
        if bot_cpu_usage > 100:
            bot_cpu_usage = bot_cpu_usage / cpu_count
        bot_cpu_usage_field = self.construct_load_bar_string(bot_cpu_usage)

        server_cpu_usage = psutil.cpu_percent()
        if server_cpu_usage > 100:
            server_cpu_usage = server_cpu_usage / cpu_count
        server_cpu_usage_field = self.construct_load_bar_string(server_cpu_usage)

        io_counters = self.process.io_counters()
        io_read_bytes = f"{io_counters.read_bytes/1024/1024:.3f}MB"
        io_write_bytes = f"{io_counters.write_bytes/1024/1024:.3f}MB"

        # The weird numbers is just guessing number of spaces so the lines align
        # Needed since embeds are not monospaced font
        field_content = (
            f"**Bot RAM usage:**{embed_space*7}{bot_ram_usage_field}\n"
            f"**Server RAM usage:**{embed_space}{server_ram_usage_field}\n"
            f"**Bot CPU usage:**{embed_space*9}{bot_cpu_usage_field}\n"
            f"**Server CPU usage:**{embed_space*3}{server_cpu_usage_field}\n"
            f"**IO (r/w):** {io_read_bytes} / {io_write_bytes}\n"
        )

        embed = info("", ctx.me, title="")
        embed.set_author(name="Tortoise BOT", icon_url=ctx.me.avatar_url)
        embed.add_field(name="Bot Stats", value=field_content)
        embed.set_footer(text="Tortoise Community")

        await ctx.send(embed=embed)

    @staticmethod
    def construct_load_bar_string(percent: int, suffix_message: str = None, size: int = 10):
        limiters = "|"
        element_emtpy = "▱"
        element_full = "▰"
        constructed = [limiters]

        if size < 8:
            size = 8

        if percent > 100:
            percent = 100

        progress = int(round(percent / size))

        for _ in range(0, progress):
            constructed.append(element_full)

        for _ in range(progress, size):
            constructed.append(element_emtpy)

        constructed.append(limiters)
        constructed = "".join(constructed)

        if suffix_message is None:
            constructed = f"{constructed} {percent:.2f}%"
        else:
            constructed = f"{constructed} {suffix_message}"

        return constructed

    @commands.command()
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def countdown(self, ctx, start: int):
        try:
            await ctx.message.delete()
        except discord.Forbidden:
            pass

        message = await ctx.send(start)
        while start:
            minutes, seconds = divmod(start, 60)
            content = f"{minutes:02d}:{seconds:02d}"
            await message.edit(content=content)
            start -= 1
            await asyncio.sleep(1)
        await message.delete()

    @commands.command(aliases=['issues', 'add'])
    async def add_to_issues(self, ctx):
        msg = (
            "░█████╗░██████╗░██████╗░  ████████╗░█████╗░  ██╗░██████╗░██████╗██╗░░░██╗███████╗░██████╗\n"
            "██╔══██╗██╔══██╗██╔══██╗  ╚══██╔══╝██╔══██╗  ██║██╔════╝██╔════╝██║░░░██║██╔════╝██╔════╝\n"
            "███████║██║░░██║██║░░██║  ░░░██║░░░██║░░██║  ██║╚█████╗░╚█████╗░██║░░░██║█████╗░░╚█████╗░\n"
            "██╔══██║██║░░██║██║░░██║  ░░░██║░░░██║░░██║  ██║░╚═══██╗░╚═══██╗██║░░░██║██╔══╝░░░╚═══██╗\n"
            "██║░░██║██████╔╝██████╔╝  ░░░██║░░░╚█████╔╝  ██║██████╔╝██████╔╝╚██████╔╝███████╗██████╔╝\n"
            "╚═╝░░╚═╝╚═════╝░╚═════╝░  ░░░╚═╝░░░░╚════╝░  ╚═╝╚═════╝░╚═════╝░░╚═════╝░╚══════╝╚═════╝░\n"
        )
        await ctx.send(f"```{msg}```")
        await ctx.message.delete()

    @commands.command()
    async def ask(self, ctx):
        msg = (
            "Don't ask to ask just ask.\n\n"
            " • You will have much higher chances of getting a answer\n"
            " • It saves time both for us and you as we can skip the whole process of actually getting the "
            "question out of you\n\n"
            "For more info visit https://dontasktoask.com/"
        )
        embed = info(msg, ctx.me, "")
        await ctx.send(embed=embed)

    @commands.command()
    async def markdown(self, ctx):
        msg = (
            "You can format your code by using markdown like this:\n\n"
            "\\`\\`\\`python\n"
            "your code here\n"
            "\\`\\`\\`\n\n"
            "Note that character ` is not a quote but a backtick.\n\n"
            "If, however, you have large amounts of code then it's better to use our paste service: "
            f"{tortoise_paste_service_link}"
        )
        embed = info(msg, ctx.me, "")
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Other(bot))
