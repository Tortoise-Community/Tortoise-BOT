import random

import discord
from discord.ext import commands

from bot import constants
from bot.cogs.utils.checks import check_if_it_is_tortoise_guild


class Security(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.tortoise_guild = bot.get_guild(constants.tortoise_guild_id)
        self.verified_role = self.tortoise_guild.get_role(constants.verified_role_id)
        self.unverified_role = self.tortoise_guild.get_role(constants.unverified_role_id)
        self.system_log_channel = bot.get_channel(constants.system_log_channel_id)

    @commands.Cog.listener()
    @commands.check(check_if_it_is_tortoise_guild)
    async def on_member_join(self, member):
        await member.add_roles(self.unverified_role)

    @commands.command()
    @commands.check(check_if_it_is_tortoise_guild)
    async def accept(self, ctx):
        if not ctx.channel.id == constants.verification_channel_id:
            await ctx.send("This is not verification channel.")
            return

        if self.unverified_role in ctx.author.roles:
            captcha_code, captcha_url = random.choice(constants.captchas)

            msg = await ctx.send("Verification has been sent in DM!")
            await msg.add_reaction("✅")

            captcha_embed = discord.Embed(color=0x7289da)
            captcha_embed.add_field(
                name="Please complete the captcha below to gain access to the server.",
                value="**NOTE:** This is **Case and Space Sensitive**"
            )
            captcha_embed.set_image(url=captcha_url)
            await ctx.author.send(embed=captcha_embed)

            def check(m):
                return m.content == captcha_code and ctx.author.id == m.author.id

            await self.bot.wait_for("message", check=check, timeout=180)

            success_embed = discord.Embed(color=0x00FF00)
            success_embed.add_field(name="Thank you for verifying!", value="You now have access to the server.")
            await ctx.author.send(embed=success_embed)

            await ctx.author.remove_roles(self.unverified_role)
            await ctx.author.add_roles(self.verified_role)

            log_embed = discord.Embed(
                title="**Welcome!**",
                description=f"{ctx.message.author.name} has joined the Tortoise Community.",
                color=0x13D910
            )
            await self.system_log_channel.send(embed=log_embed)


def setup(bot):
    bot.add_cog(Security(bot))
