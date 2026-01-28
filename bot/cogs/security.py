import logging

import discord
from discord.ext import commands
from discord import Member, Message

from bot import constants
from bot.utils.embed_handler import info
from bot.utils.message_handler import RemovableMessage
from bot.constants import allowed_file_extensions


logger = logging.getLogger(__name__)


class Security(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._guild = None
        self._trusted = None
        self._log_channel = None

    @property
    def guild(self):
        if self._guild is None:
            self._guild = self.bot.get_guild(constants.tortoise_guild_id)
        return self._guild

    @property
    def trusted(self):
        if self._trusted is None:
            self._trusted = self.guild.get_role(constants.trusted_role_id)
        return self._trusted

    @property
    def log_channel(self):
        if self._log_channel is None:
            self._log_channel = self.bot.get_channel(constants.bot_log_channel_id)
        return self._log_channel

    async def security_check(self, message: Message):
        """
        Runs security checks on message.
        Some checks can delete the message, so no need to run additional checks if message got deleted.
        :param message: message to run checks on
        """
        if self.is_security_whitelisted(message):
            return

        if len(message.attachments) != 0:
            await self.deal_with_attachments(message)

    def is_security_whitelisted(self, message: Message) -> bool:
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





    async def deal_with_attachments(self, message: Message) -> bool:
        """
        Will delete message if it has attachment that we don't allow.
        :param message: message to check for attachments
        :return: bool, was the passed message deleted or not?
        """
        reply = None
        delete_message_flag = False

        for attachment in message.attachments:
            try:
                extension = attachment.filename.rsplit('.', 1)[1]
            except IndexError:
                extension = ""  # file has no extension

            extension = extension.lower()

            if extension not in allowed_file_extensions:
                reply = (
                    f"Hey {message.author}, {extension} file extension is not allowed here.\n "
                    "If you believe this is a mistake please contact admins."
                )

            if reply:
                delete_message_flag = True
                msg = await message.channel.send(f"{message.author.mention}!", embed=info(reply, message.guild.me))
                self.bot.loop.create_task(RemovableMessage.create_instance(self.bot, msg, message.author))

        if delete_message_flag:
            await message.delete()

        # for return handler to know if og msg got deleted, so it doesn't run additional checks
        return delete_message_flag





    @commands.Cog.listener()
    async def on_message(self, message):
        await self.security_check(message)

    @commands.Cog.listener()
    async def on_message_edit(self, msg_before, msg_after):
        if msg_before.content == msg_after.content:
            return
        elif self.is_security_whitelisted(msg_after):
            return

        # Log that the message was edited for security reasons
        msg = (
            f"**Message edited in** {msg_before.channel.mention}\n\n"
            f"**Before:** {msg_before.content}\n"
            f"**After: **{msg_after.content}\n\n"
            f"[jump]({msg_after.jump_url})"
        )
        embed = info(msg, msg_before.guild.me)
        embed.set_footer(text=f"Author: {msg_before.author}", icon_url=msg_before.author.avatar.url)
        await self.log_channel.send(embed=embed)

        # Check if the new message violates our security
        await self.security_check(msg_after)

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.content == "":
            return  # if it had only attachment for example
        elif self.is_security_whitelisted(message):
            return

        msg = (
            f"**Message deleted in** {message.channel.mention}\n\n"
            f"**Message: **{message.content}"
        )
        embed = info(msg, message.guild.me, "")
        embed.set_footer(text=f"Author: {message.author}", icon_url=message.author.avatar.url)
        await self.log_channel.send(embed=embed)




async def setup(bot):
    await bot.add_cog(Security(bot))
