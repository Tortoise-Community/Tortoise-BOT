import re
import functools

import aiohttp
from discord.ext import commands
from discord import Member, Message

from bot import constants
from bot.constants import banned_file_extensions, tortoise_paste_endpoint, tortoise_paste_service_link
from bot.config_handler import ConfigHandler
from bot.cogs.utils.embed_handler import info


def security_bypass_check(function):
    @functools.wraps(function)
    async def wrapper(self, *args):
        for message in args:
            if message.guild is None or message.author.bot:
                return
            elif message.guild.id != constants.tortoise_guild_id:
                return
            elif not isinstance(message.author, Member):
                # Web-hooks messages will appear as from User even tho they are in Guild.
                return
            elif message.author.guild_permissions.administrator:
                return
            elif self.trusted in message.author.roles:
                # Whitelists the members with Trusted role to prevent unnecessary logging
                return
        return await function(self, *args)
    return wrapper


class Security(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.guild = bot.get_guild(constants.tortoise_guild_id)
        self.session = aiohttp.ClientSession()
        self.banned_words = ConfigHandler("banned_words.json")
        self.trusted = self.guild.get_role(constants.trusted_role_id)
        self.log_channel = bot.get_channel(constants.bot_log_channel_id)

    async def _security_check(self, message):
        await self._deal_with_vulgar_words(message)
        if "https:" in message.content or "http:" in message.content:
            await self._deal_with_invites(message)
        if len(message.attachments) != 0:
            await self._deal_with_attachments(message)

    async def _deal_with_invites(self, message: Message):
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
                        title=""
                    )
                    await message.channel.send(embed=embed)
                    await message.delete()

    async def _deal_with_vulgar_words(self, message: Message):
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

    async def _deal_with_attachments(self, message: Message):
        for attachment in message.attachments:
            extension = attachment.filename.rsplit('.')[-1]
            if extension in banned_file_extensions:
                paste_keys = {}
                file_content = await attachment.read()
                async with self.session.post(url=tortoise_paste_endpoint, data=file_content) as resp:
                    key = (await resp.json()).get("key")
                    paste_keys[attachment.filename] = key
                await message.delete()
                attachment_list = "".join(f"[**{file}**: {tortoise_paste_service_link+paste_keys[file]}]\n"
                                          for file in paste_keys)
                file_type = banned_file_extensions[extension]
                embed = info(
                    f"It looks like you tried to attach a {file_type} file which is not allowed, "
                    f"As it could potentially contain malicious code."
                    f"\n\nYou can find the file paste here:\n {attachment_list}", message.guild.me, ""
                )
                await message.channel.send(f"Hey {message.author.mention}!", embed=embed)
                await message.delete()

    @commands.Cog.listener()
    @security_bypass_check
    async def on_message(self, message):
        await self._security_check(message)

    @commands.Cog.listener()
    @security_bypass_check
    async def on_message_edit(self, msg_before, msg_after):
        if msg_before.content == msg_after.content:
            return

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
    @security_bypass_check
    async def on_message_delete(self, message):
        if message.content == "":
            return
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
