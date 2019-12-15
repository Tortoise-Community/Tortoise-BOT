import random
import discord
from discord.ext import commands

captchas = [("9GphJ", 'https://cdn.discordapp.com/attachments/581139962611892229/622697748788936704/blog74054e389122fd355363104c1990700d__t_e048fd7a0f1e.png'), 
            ("PRNU", 'https://cdn.discordapp.com/attachments/581139962611892229/622697949914464286/Example-of-PDM-character-extraction-for-the-animated-CAPTCHA-available-on-the-Sandbox.png'),
            ("PQJRYD", 'https://cdn.discordapp.com/attachments/581139962611892229/622698143842172955/captche.jpg')]
unverified_role_id = 628674026927161374
verified_role_id = 599647985198039050
verification_channel_id = 602156675863937024
system_log_channel_id = 593883395436838942


class Security(commands.Cog):
    # Bot will have to have manage_roles permission in order for this to work
    def __init__(self, bot):
        self.bot = bot
        
    @commands.Cog.listener()
    async def on_member_join(self, member):
        unverified_role = member.guild.get_role(unverified_role_id)
        await member.add_roles(unverified_role)
        
    @commands.command()
    async def accept(self, ctx):
        if not ctx.channel.id == verification_channel_id:
            await ctx.send("This is not verification channel.")
            return

        verified_role = ctx.guild.get_role(verified_role_id)
        unverified_role = ctx.guild.get_role(unverified_role_id)
        if unverified_role in ctx.author.roles:
            captcha_code, captcha_url = random.choice(captchas)

            msg = await ctx.send("Verification has been sent in DM!")
            await msg.add_reaction("✅")

            captcha_embed = discord.Embed(color=0x7289da)
            captcha_embed.add_field(name="Please complete the captcha below to gain access to the server.",
                                    value="**NOTE:** This is **Case and Space Sensitive**")
            captcha_embed.set_image(url=captcha_url)
            await ctx.author.send(embed=captcha_embed)

            def check(m):
                return m.content == captcha_code and ctx.author.id == m.author.id

            await self.bot.wait_for("message", check=check, timeout=180)

            success_embed = discord.Embed(color=0x00FF00)
            success_embed.add_field(name="Thank you for verifying!", value="You now have access to the server.")
            await ctx.author.send(embed=success_embed)

            await ctx.author.remove_roles(unverified_role)
            await ctx.author.add_roles(verified_role)

            system_log_channel = self.bot.get_channel(system_log_channel_id)
            log_embed = discord.Embed(title="**Welcome!**",
                                      description=f"{ctx.message.author.name} has joined the Tortoise Community.",
                                      color=0x13D910)
            await system_log_channel.send(embed=log_embed)


def setup(bot):
    bot.add_cog(Security(bot))
