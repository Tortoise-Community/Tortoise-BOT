import re
import logging
import functools

import aiohttp
from guesslang import Guess
from discord.ext import commands
from discord import Member, Message, Guild

from bot import constants
from bot.config_handler import ConfigHandler
from bot.utils.embed_handler import info, warning
from bot.constants import (
    extension_to_pastebin, allowed_file_extensions, tortoise_paste_endpoint, tortoise_paste_service_link
)


logger = logging.getLogger(__name__)


class Security(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.guild = bot.get_guild(constants.tortoise_guild_id)
        self.session = aiohttp.ClientSession()
        self.banned_words = ConfigHandler("banned_words.json")
        self.trusted = self.guild.get_role(constants.trusted_role_id)
        self.log_channel = bot.get_channel(constants.bot_log_channel_id)
        self.guess_language = Guess()

    async def security_check(self, message: Message):
        """
        Runs security checks on message.
        Some checks can delete the message, so no need to run additional checks if message got deleted.
        :param message: message to run checks on
        """
        if self.skip_security(message):
            return

        is_message_deleted = False
        await self.deal_with_vulgar_words(message)

        if "https:" in message.content or "http:" in message.content:
            is_message_deleted = await self.deal_with_invites(message)

        if len(message.attachments) != 0 and not is_message_deleted:
            is_message_deleted = await self.deal_with_attachments(message)

        if not is_message_deleted:
            await self.deal_with_long_code(message)

    def skip_security(self, message: Message) -> bool:
        """
        In which cases we will skip our security check for message.
        :param message: message on which we will potentially run security checks
        :return: bool whether we should skip security checks or not
        """
        if message.guild is None or message.author.bot:
            return True
        elif message.guild.id != constants.tortoise_guild_id:
            return True
        elif not isinstance(message.author, Member):
            return True  # Web-hooks messages will appear as from User even tho they are in Guild.
        elif message.author.guild_permissions.administrator:
            return True
        elif self.trusted in message.author.roles:
            return True  # Whitelists the members with Trusted role to prevent unnecessary logging

        return False

    async def deal_with_invites(self, message: Message) -> bool:
        """
        Checks if the message has any invites that are not for Tortoise guild,
        if so deletes the message.
        Works both with discord.com/invite and discord.gg ,including link shorteners.
        :param message: message to check for Discord invites
        :return: bool, was the passed message deleted or not?
        """
        base_url = re.findall(
            r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+",  # Find any url
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
                if not await self.check_if_invite_is_our_guild(invite, message.guild):
                    # TODO give him warning points etc / send to deterrence channel
                    embed = warning(f"{message.author.mention} You are not allowed to send other server invites here.")
                    await message.channel.send(embed=embed)
                    await message.delete()
                    return True

        # If we've come here we did not delete our message
        return False

    async def deal_with_vulgar_words(self, message: Message) -> None:
        """
        Checks passed message for vulgar words and if found sends info message to bot log channel.
        As we currently don't have a reliable method to detect truly bad messages (context matters)
        we are not punishing users, we are only logging the behaviour.
        :param message: message to check for vulgar words
        :return: bool, was the passed message deleted or not?
        """
        for category, banned_words in self.banned_words.loaded.items():
            for banned_word in banned_words:
                if banned_word in message.content.lower():
                    embed = info(
                        f"Curse word **{banned_word}** detected from the category **{category}**",
                        message.guild.me,
                        title=""
                    )
                    embed.set_footer(text=f"Author: {message.author}", icon_url=message.author.avatar_url)
                    await self.log_channel.send(embed=embed)

    async def deal_with_attachments(self, message: Message) -> bool:
        """
        Will delete message if it has attachment that we don't allow or if it is a
        whitelisted attachment extension it will upload it's content to our pastebin
        and reply with link to it.
        :param message: message to check for attachments
        :return: bool, was the passed message deleted or not?
        """
        reply = None

        for attachment in message.attachments:
            try:
                extension = attachment.filename.rsplit('.', 1)[1]
            except IndexError:
                extension = ""  # file has no extension

            extension = extension.lower()

            if extension in extension_to_pastebin:
                # Maximum file size to upload to Pastebin is 4MB
                if attachment.size > 4 * 1024 * 1024:
                    reply = (
                        f"It looks like you tried to attach a {extension} file which "
                        f"could be code related but since it's over 4MB in size I will not be uploading it "
                        f"to our pastebin for viewing."
                    )
                else:
                    file_content = await attachment.read()
                    url = await self.create_pastebin_link(file_content)
                    reply = (
                        f"It looks like you tried to attach a {extension} file which is not allowed, "
                        "however since it could be code related you can find the paste link here:\n"
                        f"[**{attachment.filename}** {url}]"
                    )
            elif extension not in allowed_file_extensions:
                reply = (
                    f"It looks like you tried to attach a {extension} file which is not allowed, "
                    "as it could potentially contain malicious code."
                )

            if reply:
                await message.channel.send(f"Hey {message.author.mention}!", embed=warning(reply))
                await message.delete()
                return True

        # If we've come here we did not delete our message
        return False

    async def deal_with_long_code(self, message: Message) -> bool:
        """
        When someone sends long message containing code, bot will delete it and upload message content
        to our pastebin and reply with it's link.
        Guessing is quite CPU intensive so be sure to check it only for long messages (not for each).
        :param message: message to check
        :return: bool, was the passed message deleted or not?
        """
        if len(message.content) <= constants.max_message_length:
            return False

        await message.channel.trigger_typing()
        language = await self.bot.loop.run_in_executor(
            None, functools.partial(self.guess_language.language_name, source_code=message.content)
        )

        if not language:
            return False

        pastebin_link = await self.create_pastebin_link(message.content.encode())
        await message.delete()
        msg = (
            f"Hey {message.author}, I've uploaded your long **{language}** code to our pastebin: {pastebin_link}"
        )
        await message.channel.send(embed=info(msg, message.guild.me, ""))
        return True

    async def create_pastebin_link(self, content: bytes) -> str:
        """Creates link to our Pastebin with passed content."""
        async with self.session.post(url=tortoise_paste_endpoint, data=content) as resp:
            data = await resp.json()
        return f"{tortoise_paste_service_link}{data.get('key')}"

    @commands.Cog.listener()
    async def on_message(self, message):
        await self.security_check(message)

    @commands.Cog.listener()
    async def on_message_edit(self, msg_before, msg_after):
        if msg_before.content == msg_after.content:
            return
        elif self.skip_security(msg_after):
            return

        # Log that the message was edited for security reasons
        msg = (
            f"**Message edited in** {msg_before.channel.mention}\n\n"
            f"**Before:** {msg_before.content}\n"
            f"**After: **{msg_after.content}\n\n"
            f"[jump]({msg_after.jump_url})"
        )
        embed = info(msg, msg_before.guild.me)
        embed.set_footer(text=f"Author: {msg_before.author}", icon_url=msg_before.author.avatar_url)
        await self.log_channel.send(embed=embed)

        # Check if the new message violates our security
        await self.security_check(msg_after)

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.content == "":
            return  # if it had only attachment for example
        elif self.skip_security(message):
            return

        msg = (
            f"**Message deleted in** {message.channel.mention}\n\n"
            f"**Message: **{message.content}"
        )
        embed = info(msg, message.guild.me, "")
        embed.set_footer(text=f"Author: {message.author}", icon_url=message.author.avatar_url)
        await self.log_channel.send(embed=embed)

    @classmethod
    async def check_if_invite_is_our_guild(cls, full_link: str, guild: Guild):
        guild_invites = await guild.invites()
        for invite in guild_invites:
            if cls.get_invite_link_code(invite.url) == cls.get_invite_link_code(full_link):
                return True
        return False

    @classmethod
    def get_invite_link_code(cls, string: str):
        return string.split("/")[-1]


def setup(bot):
    bot.add_cog(Security(bot))
