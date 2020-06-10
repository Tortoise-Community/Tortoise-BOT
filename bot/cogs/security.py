import re
import functools

import aiohttp
from discord import Member
from discord.ext import commands

from bot import constants
from bot.config_handler import ConfigHandler
from bot.cogs.utils.embed_handler import info


class Security(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()
        self.banned_words = ConfigHandler("banned_words.json")
        self.trusted = bot.get_role(constants.trusted_role_id)
        self.log_channel = bot.get_channel(constants.bot_log_channel_id)

    async def _security_check(self, message):

        if "https:" in message.content or "http:" in message.content:

            # Find any url
            base_url = re.findall(
                r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+",
                message.content
            )

            for invite in base_url:

                # Get the endpoint of that url (for discord invite url shorteners)
                try:
                    async with self.session.get(invite) as response:
                        invite = str(response.url)
                except aiohttp.ClientConnectorError:
                    # The link is not valid
                    continue

                if "discord.com/invite/" in invite or "discord.gg/" in invite:
                    if not await Security.check_if_invite_is_our_guild(invite, message.guild):
                        # TODO give him warning points etc / send to deterrence channel
                        embed = info(
                            f"{message.author.mention} You are not allowed to send other server invites here.",
                            message.guild.me,
                            ""
                        )
                        await message.channel.send(embed=embed)
                        await message.delete()

        for category, banned_words in self.banned_words.loaded.items():
            for banned_word in banned_words:
                if banned_word in message.content.lower():
                    embed = info(
                        f"Curse word **{banned_word}** detected from the category **{category}**",
                        message.guild.me,
                        ""
                    )
                    embed.set_footer(text=f"Author: {message.author}", icon_url=message.author.avatar_url)
                    await self.log_channel.send(embed=embed)

    # Checks all the conditions for message moderation
    def check_config(function):
        @functools.wraps(function)
        async def wrapper(self, *args):
            for message in args:
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
                    # Whitelists the members with Trusted role to prevent unnecessary logging
                elif self.trusted in message.author.roles:
                    return
            return await function(self, *args)

        return wrapper

    @commands.Cog.listener()
    @check_config
    async def on_message(self, message):
        await self._security_check(message)

    @commands.Cog.listener()
    @check_config
    async def on_message_edit(self, msg_before, msg_after):
        msg = (
            f"**Message edited in** {msg_before.channel.mention}\n\n"
            f"**Before:** {msg_before.content}\n"
            f"**After: **{msg_after.content}\n\n"
            f"[jump]({msg_after.jump_url})"
        )

        embed = info(msg, msg_before.guild.me)
        embed.set_footer(text=f"Author: {msg_before.author}", icon_url=msg_before.author.avatar_url)
        await self.log_channel.send(embed=embed)
        await self._security_check(msg_after)

    @commands.Cog.listener()
    @check_config
    async def on_message_delete(self, message):
        msg = (
            f"**Message deleted in** {message.channel.mention}\n\n"
            f"**Message: **{message.content}"
        )

        embed = info(msg, message.guild.me, "")
        embed.set_footer(text=f"Author: {message.author}", icon_url=message.author.avatar_url)
        await self.log_channel.send(embed=embed)

    @staticmethod
    async def check_if_invite_is_our_guild(full_link, guild):
        guild_invites = await guild.invites()
        for invite in guild_invites:
            # discord.gg/code resolves to https://discord.com/invite/code after using session.get(invite)
            if Security._get_invite_link_code(invite.url) == Security._get_invite_link_code(full_link):
                return True
        return False

    @staticmethod
    def _get_invite_link_code(string: str):
        return string.split("/")[-1]


def setup(bot):
    bot.add_cog(Security(bot))
