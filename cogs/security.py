import re

import aiohttp
from discord import Member
from discord.ext import commands

import constants
from config_handler import ConfigHandler


class Security(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()
        self.banned_words = ConfigHandler("banned_words.json")

    @commands.Cog.listener()
    async def on_message(self, message):
        ctx = message.channel
        if message.guild is None or message.author == message.guild.me:
            return
        elif message.guild.id != constants.tortoise_guild_id:
            # Functionality only available in Tortoise guild
            return
        elif not isinstance(message.author, Member):
            # Web-hooks messages will appear as from User even tho they are in Guild.
            return
        elif message.author.guild_permissions.administrator:
            # Ignore admins
            return

        # Check for invites
        # For this to work bot needs to have manage_guild permission (so he can get guild invites)
        if "https:" in message.content or "http:" in message.content:
            # Find any url
            base_url = re.findall(r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+",
                                  message.content)
            for invite in base_url:
                # Get the endpoint of that url (for discord invite url shorteners)
                async with self.session.get(invite) as response:
                    invite = str(response.url)

                if "discordapp.com/invite/" in invite or "discord.gg/" in invite:
                    if not await Security.check_if_invite_is_our_guild(invite, message.guild):
                        await ctx.send(f"{message.author.mention} You are not allowed to post other guild invites!")
                        await message.delete()
                        # TODO give him warning points etc / send to deterrence channel

        for category, banned_words in self.banned_words.loaded.items():
            for banned_word in banned_words:
                if banned_word in message.content.lower():
                    bot_log_channel = self.bot.get_channel(constants.bot_log_channel_id)
                    msg = f"{message.author} - curse word {banned_word} detected from category {category}!"
                    await bot_log_channel.send(msg)
                    # TODO: give him warning points or smth

    @staticmethod
    async def check_if_invite_is_our_guild(full_link, guild):
        guild_invites = await guild.invites()
        for invite in guild_invites:
            # discord.gg/code resolves to https://discordapp.com/invite/code after using session.get(invite)
            if Security._get_invite_link_code(invite.url) == Security._get_invite_link_code(full_link):
                return True
        return False

    @staticmethod
    def _get_invite_link_code(string: str):
        return string.split("/")[-1]


def setup(bot):
    bot.add_cog(Security(bot))
