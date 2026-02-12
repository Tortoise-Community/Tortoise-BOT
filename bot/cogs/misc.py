import os
import time
import asyncio
import random
from textwrap import wrap

import psutil
import discord
from discord.ext import commands
from discord import app_commands

from bot.utils.message_handler import RemovableMessage
from bot.utils.embed_handler import info, status_embed
from bot.utils.checks import check_if_it_is_tortoise_guild
from bot.constants import embed_space, tortoise_paste_service_link


class Miscellaneous(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.process = psutil.Process(os.getpid())
        self.countdown_started = False

    @app_commands.command(name="say", description="Make the bot say a message")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def say(self, interaction: discord.Interaction, message: str):
        clean = await commands.clean_content().convert(interaction, message)
        await interaction.response.send_message(clean)

    @app_commands.command(name="slap")
    async def slap(self, interaction: discord.Interaction, member: discord.Member):
        if interaction.user == member:
            embed = info(f"{member.mention} slapped him/her self LOL", interaction.guild.me, "Slap!")
            img_url = "https://media.giphy.com/media/j1zuL4htGTFQY/giphy.gif"
        else:
            embed = info(
                f"{member.mention} got slapped in the face by: {interaction.user.mention}!",
                interaction.guild.me,
                "Slap!",
            )
            img_url = "https://66.media.tumblr.com/05212c10d8ccfc5ab190926912431344/tumblr_mt7zwazvyi1rqfhi2o1_400.gif"

        embed.set_image(url=img_url)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="shoot")
    async def shoot(self, interaction: discord.Interaction, member: discord.Member):
        embed = info(
            f"{member.mention} shot by {interaction.user.mention}  :gun: :boom:",
            interaction.guild.me,
            "Boom!",
        )
        embed.set_image(url="https://i.gifer.com/XdhK.gif")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="throw")
    async def throw(self, interaction: discord.Interaction):
        await interaction.response.send_message("```(╯°□°)╯︵ ┻━┻```")

    @app_commands.command(name="members")
    async def members(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            embed=info(f"{interaction.guild.member_count}", interaction.guild.me, "Member count")
        )

    @app_commands.command(name="status")
    async def status(self, interaction: discord.Interaction, member: discord.Member | None = None):
        if member is None:
            member = interaction.user
        embed = status_embed(interaction, member)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="pfp")
    async def pfp(self, interaction: discord.Interaction, member: discord.Member | None = None):
        if member is None:
            message, member = "Your avatar", interaction.user
        elif member == interaction.guild.me:
            message = "My avatar"
        else:
            message = f"{member} avatar"

        embed = info(message, interaction.guild.me)
        embed.set_image(url=member.display_avatar.replace(size=4096))
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="ping")
    async def ping(self, interaction: discord.Interaction):
        start = time.perf_counter()
        await interaction.response.send_message(embed=info("Pong!", interaction.guild.me))
        end = time.perf_counter()
        duration = (end - start) * 1000
        await interaction.edit_original_response(
            embed=info(f":ping_pong: {duration:.2f}ms", interaction.guild.me, "Pong!")
        )

    @app_commands.command(name="stats")
    @app_commands.checks.cooldown(1, 10)
    async def stats(self, interaction: discord.Interaction):
        bot_ram_usage = self.process.memory_full_info().rss / 1024 ** 2
        bot_ram_usage = f"{bot_ram_usage:.2f} MB"
        bot_ram_usage_field = self.construct_load_bar_string(
            self.process.memory_percent(), bot_ram_usage
        )

        virtual_memory = psutil.virtual_memory()
        server_ram_usage = f"{virtual_memory.used/1024/1024:.0f} MB"
        server_ram_usage_field = self.construct_load_bar_string(
            virtual_memory.percent, server_ram_usage
        )

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

        field_content = (
            f"**Bot RAM usage:**{embed_space*7}{bot_ram_usage_field}\n"
            f"**Server RAM usage:**{embed_space}{server_ram_usage_field}\n"
            f"**Bot CPU usage:**{embed_space*9}{bot_cpu_usage_field}\n"
            f"**Server CPU usage:**{embed_space*3}{server_cpu_usage_field}\n"
            f"**IO (r/w):** {io_read_bytes} / {io_write_bytes}\n"
        )

        embed = info("", interaction.guild.me, title="")
        embed.set_author(name="Tortoise BOT", icon_url=interaction.guild.me.avatar.url)
        embed.add_field(name="Bot Stats", value=field_content)
        embed.set_footer(text="Tortoise Community")

        await interaction.response.send_message(embed=embed)

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

    @app_commands.command(name="countdown")
    @app_commands.check(check_if_it_is_tortoise_guild)
    async def countdown(self, interaction: discord.Interaction, start: int):
        if self.countdown_started:
            return await interaction.response.send_message(
                embed=info("There is already an ongoing timer", interaction.guild.me, "")
            )

        self.countdown_started = True
        await interaction.response.send_message(str(start))
        message = await interaction.original_response()

        while start:
            minutes, seconds = divmod(start, 60)
            content = f"{minutes:02d}:{seconds:02d}"
            try:
                await message.edit(content=content)
            except discord.HTTPException:
                break
            start -= 1
            await asyncio.sleep(1)

        self.countdown_started = False
        await message.delete()

    @app_commands.command(name="add_to_issues")
    async def add_to_issues(self, interaction: discord.Interaction):
        msg = (
            "░█████╗░██████╗░██████╗░  ████████╗░█████╗░  ██╗░██████╗░██████╗██╗░░░██╗███████╗░██████╗\n"
            "██╔══██╗██╔══██╗██╔══██╗  ╚══██╔══╝██╔══██╗  ██║██╔════╝██╔════╝██║░░░██║██╔════╝██╔════╝\n"
            "███████║██║░░██║██║░░██║  ░░░██║░░░██║░░██║  ██║╚█████╗░╚█████╗░██║░░░██║█████╗░░╚█████╗░\n"
            "██╔══██║██║░░██║██║░░██║  ░░░██║░░░██║░░██║  ██║░╚═══██╗░╚═══██╗██║░░░██║██╔══╝░░░╚═══██╗\n"
            "██║░░██║██████╔╝██████╔╝  ░░░██║░░░╚█████╔╝  ██║██████╔╝██████╔╝╚██████╔╝███████╗██████╔╝\n"
            "╚═╝░░╚═╝╚═════╝░╚═════╝░  ░░░╚═╝░░░░╚════╝░  ╚═╝╚═════╝░╚═════╝░░╚═════╝░╚══════╝╚═════╝░\n"
        )
        await interaction.response.send_message(f"```{msg}```")

    @app_commands.command(name="ask")
    async def ask(self, interaction: discord.Interaction):
        content = (
            "Don't ask to ask, just ask.\n\n"
            " • You will have much higher chances of getting an answer\n"
            " • We can skip the whole process of actually getting the question out of you thus you will get "
            "answer faster\n\n"
            "For more info visit https://dontasktoask.com/"
        )
        embed = info(content, interaction.guild.me, "")
        await interaction.response.send_message(embed=embed)
        message = await interaction.original_response()
        await RemovableMessage.create_instance(self.bot, message, interaction.user)

    @app_commands.command(name="markdown")
    async def markdown(self, interaction: discord.Interaction):
        content = (
            "You can format your code by using markdown like this:\n\n"
            "\\`\\`\\`python\n"
            "print('Hello world')\n"
            "\\`\\`\\`\n\n"
            "This would give you:\n"
            "```python\n"
            "print('Hello world')```\n"
            "Note that character ` is not a quote but a backtick.\n\n"
            # "If, however, you have large amounts of code then it's better to use our paste service: "
            # f"{tortoise_paste_service_link}"
        )
        embed = info(content, interaction.guild.me, "")
        await interaction.response.send_message(embed=embed)
        message = await interaction.original_response()
        await RemovableMessage.create_instance(self.bot, message, interaction.user)

    # @app_commands.command(name="paste")
    async def paste(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            embed=info(f":page_facing_up: {tortoise_paste_service_link}", interaction.guild.me, title="")
        )

    @app_commands.command(name="zen")
    async def zen(self, interaction: discord.Interaction):
        zen = """
            Beautiful is better than ugly.
            Explicit is better than implicit.
            Simple is better than complex.
            Complex is better than complicated.
            Flat is better than nested.
            Sparse is better than dense.
            Readability counts.
            Special cases aren't special enough to break the rules.
            Although practicality beats purity.
            Errors should never pass silently.
            Unless explicitly silenced.
            In the face of ambiguity, refuse the temptation to guess.
            There should be one-- and preferably only one --obvious way to do it.
            Although that way may not be obvious at first unless you're Dutch.
            Now is better than never.
            Although never is often better than *right* now.
            If the implementation is hard to explain, it's a bad idea.
            If the implementation is easy to explain, it may be a good idea.
            Namespaces are one honking great idea -- let's do more of those!
        """
        await interaction.response.send_message(
            embed=info(zen, interaction.guild.me, title="The Zen of Python, by Tim Peters")
        )

    @app_commands.command(name="antigravity")
    async def antigravity(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            embed=info("https://xkcd.com/353/", interaction.guild.me, title="")
        )

    @app_commands.command(name="coin")
    async def coin(self, interaction: discord.Interaction, times: int = 1):
        sample_space = ("Head", "Tail")

        if times == 1:
            coin_toss = sample_space[random.randint(0, 1)]
            await interaction.response.send_message(
                embed=info(f":coin: | Coin Toss | **{coin_toss}**", interaction.guild.me, title="")
            )
        elif times <= 25:
            coin_toss = ", ".join(sample_space[random.randint(0, 1)] for _ in range(times))
            await interaction.response.send_message(
                embed=info(
                    f":coin: | Coin tossed {times} times | **{coin_toss}**",
                    interaction.guild.me,
                    title="",
                )
            )
        else:
            await interaction.response.send_message(
                embed=info(
                    "Oops! You can't toss that many times. Try a number less than 25",
                    interaction.guild.me,
                    title="",
                )
            )

    @app_commands.command(name="dice")
    async def dice(self, interaction: discord.Interaction, times: int = 1):
        if times == 1:
            dice_roll = random.randint(1, 6)
            await interaction.response.send_message(
                embed=info(f"🎲 | Dice Roll | **{dice_roll}**", interaction.guild.me, title="")
            )
        elif times <= 25:
            dice_roll = ", ".join(str(random.randint(1, 6)) for _ in range(times))
            await interaction.response.send_message(
                embed=info(
                    f"🎲 | Dice Rolled {times} times | **{dice_roll}**",
                    interaction.guild.me,
                    title="",
                )
            )
        else:
            await interaction.response.send_message(
                embed=info(
                    "Oops! You can't roll that many times. Try a number less than 25",
                    interaction.guild.me,
                    title="",
                )
            )

    @app_commands.command(name="randint")
    async def randint(
        self,
        interaction: discord.Interaction,
        low: int = 1,
        high: int = 100,
        n: int = 1,
    ):
        if low > high:
            low, high = high, low

        if (low < -1000000000 or high > 1000000000 or n > 100):
            await interaction.response.send_message(
                embed=info(
                    "Oops! That was a lot, try with smaller arguments",
                    interaction.guild.me,
                    title="",
                )
            )
        elif n == 1:
            output = random.randint(low, high)
            await interaction.response.send_message(
                embed=info(
                    f"🔢 | Random number between {low} & {high} | **{output}**",
                    interaction.guild.me,
                    title="",
                )
            )
        else:
            output = ", ".join(str(random.randint(low, high)) for _ in range(n))
            await interaction.response.send_message(
                embed=info(
                    f"🔢 | {n} Random numbers between {low} & {high} | **{output}**",
                    interaction.guild.me,
                    title="",
                )
            )

    @app_commands.command(name="choice")
    async def choice(self, interaction: discord.Interaction, args: str):
        choices = args.split(",")
        if len(choices):
            choice = random.choice(choices)
            await interaction.response.send_message(
                embed=info(
                    f"🎰 | Random choice | **{choice.strip()}**",
                    interaction.guild.me,
                    title="",
                )
            )

    @app_commands.command(name="shuffle")
    async def shuffle(self, interaction: discord.Interaction, args: str):
        choices = [word.strip() for word in args.split(",")]
        if len(choices):
            random.shuffle(choices)
            await interaction.response.send_message(
                embed=info(
                    f"📃 | Random shuffle | **{', '.join(choices)}**",
                    interaction.guild.me,
                    title="",
                )
            )

    @app_commands.command(name="speak")
    async def speak(self, interaction: discord.Interaction, text: str):
        tortoise = r'''
        \
         \     ,-"""-.
          oo._/ \___/ \
         (____)_/___\__\_)
             /_//   \\_\ '''

        lines = wrap(text, 40)
        width = max(map(len, lines))
        bubble = ["  " + "-" * width]

        if len(lines) == 1:
            bubble.append("< " + lines[0] + " >")
        else:
            bubble.append("/ " + lines[0] + " " * (width - len(lines[0])) + " \\")
            for line in lines[1:-1]:
                bubble.append("| " + line + " " * (width - len(line)) + " |")
            bubble.append("\\ " + lines[-1] + " " * (width - len(lines[-1])) + " /")

        bubble.append("  " + "-" * width)
        output = "\n".join(bubble) + tortoise
        await interaction.response.send_message(f"```{output}```")


async def setup(bot):
    cog = Miscellaneous(bot)
    await bot.add_cog(cog)
