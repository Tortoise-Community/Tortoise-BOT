from __future__ import annotations

import logging
import discord
import aiohttp
import io
from discord.ext import commands
from discord import Member, Message

from bot import constants
from bot.utils.embed_handler import info, moderation_log_embed
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

        if message.attachments:
            deleted = await self.deal_with_attachments(message)
            if deleted:
                self.bot.suppressed_deletes.add(message.id)

    def is_security_whitelisted(self, message: Message) -> bool:
        """
        In which cases we will skip our security check for message.
        :param message: message on which we will potentially run security checks
        :return: bool whether we should skip security checks or not
        """
        if self.guild is None:
            return True
        if message.guild is None or message.author.bot:
            return True
        if message.guild.id != constants.tortoise_guild_id:
            return True
        if not isinstance(message.author, Member):
            return True
        if message.author.guild_permissions.administrator:
            return True
        if self.trusted and self.trusted in message.author.roles:
            return True
        return False


    async def archive_and_delete_message(
            self,
            message: discord.Message,
            *,
            reason: str,
            title: str = "Message Removed",
            delete: bool = True
    ):
        files_to_log = []

        async with aiohttp.ClientSession() as session:
            for attachment in message.attachments:
                async with session.get(attachment.url) as resp:
                    if resp.status == 200:
                        data = await resp.read()
                        files_to_log.append(
                            discord.File(
                                fp=io.BytesIO(data),
                                filename=attachment.filename
                            )
                        )

        # suppress recursive logging
        if hasattr(self.bot, "suppressed_deletes"):
            self.bot.suppressed_deletes.add(message.id)

        if delete:
            try:
                await message.delete()
            except discord.NotFound:
                pass

        if not self.log_channel:
            return

        content = self.extract_content(message)

        embed = moderation_log_embed(
            title=title,
            channel=message.channel.mention,
            content=f"{reason}\n\n{content}",
            color=discord.Color.red()
        )
        embed.set_footer(text=f"Author: {message.author}", icon_url=message.author.avatar.url)

        await self.log_channel.send(embed=embed, files=files_to_log)


    async def deal_with_attachments(self, message: Message) -> bool:
        """
        Will delete message if it has attachment that we don't allow.
        :param message: message to check for attachments
        :return: bool, was the passed message deleted or not?
        """
        async with aiohttp.ClientSession() as session:
            for attachment in message.attachments:
                try:
                    extension = attachment.filename.rsplit('.', 1)[1].lower()
                except IndexError:
                    extension = ""

                if extension not in allowed_file_extensions:

                    reply = (
                        "This file type is not permitted.\n"
                        "Use **Markdown** for code snippets and **Gist** or **Pastebin** for large files.\n"
                        "For formatting help, use **/markdown**."
                    )

                    msg = await message.channel.send(
                        f"{message.author.mention}",
                        embed=info(message=reply, title="File Blocked", member=message.guild.me)
                    )

                    self.bot.loop.create_task(
                        RemovableMessage.create_instance(self.bot, msg, message.author)
                    )

                    await self.archive_and_delete_message(
                        message,
                        reason="Blocked file upload",
                        title="File Blocked",
                        delete=True
                    )
                    return True

        return False


    @commands.Cog.listener()
    async def on_message(self, message):
        await self.security_check(message)

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):

        if self.is_security_whitelisted(message):
            return

        await self.archive_and_delete_message(
            message,
            reason="Raw message deletion",
            title="Message Deleted",
            delete=False
        )


    @commands.Cog.listener()
    async def on_bulk_message_delete(self, messages: list[discord.Message]):
        if not messages:
            return

        filtered = []
        for msg in messages:
            if msg.id in self.bot.suppressed_deletes:
                self.bot.suppressed_deletes.discard(msg.id)
                continue
            filtered.append(msg)

        if not filtered:
            return

        channel = self.log_channel
        if channel is None:
            return

        entries = []
        files_to_log = []

        for message in filtered:
            if message.author is None or message.author.bot:
                continue

            content = self.extract_content(message)
            entries.append(
                f"**{message.author}** in {message.channel.mention}:\n{content}"
            )

            for attachment in message.attachments:
                try:
                    data = await attachment.read()
                    files_to_log.append(
                        discord.File(
                            fp=io.BytesIO(data),
                            filename=attachment.filename
                        )
                    )
                except Exception:
                    pass

        if not entries:
            return

        MAX_CHARS = 3500
        chunks = []
        current = ""

        for entry in entries:
            if len(current) + len(entry) > MAX_CHARS:
                chunks.append(current)
                current = entry
            else:
                current += "\n\n" + entry if current else entry

        if current:
            chunks.append(current)

        for i, chunk in enumerate(chunks, start=1):
            embed = discord.Embed(
                title="Bulk Messages Deleted",
                description=chunk,
                color=discord.Color.dark_red(),
            )
            embed.set_footer(text=f"Batch {i}/{len(chunks)}")

            # upload files after embed
            if i == 1 and files_to_log:
                await channel.send(embed=embed, files=files_to_log)
            else:
                await channel.send(embed=embed)


    @staticmethod
    def extract_content(message: discord.Message) -> str:
        parts = []

        if message.content:
            parts.append(message.content.strip())

        for attachment in message.attachments:
            parts.append(f"[Attachment] {attachment.url}")

        for embed in message.embeds:
            if embed.url:
                parts.append(f"[Embed URL] {embed.url}")
            elif embed.title or embed.description:
                preview = (embed.title or embed.description or "").strip()
                if preview:
                    parts.append(f"[Embed] {preview[:200]}")

        if message.stickers:
            parts.append("[Sticker]")

        return " | ".join(parts) if parts else "[No content]"

    @commands.Cog.listener()
    async def on_message_edit(self, msg_before, msg_after):
        if msg_before.content == msg_after.content:
            return
        elif self.is_security_whitelisted(msg_after):
            return

        # Log that the message was edited for security reasons
        msg = (
            f"**Channel**\n{msg_before.channel.mention}\n\n"
            f"**Before**\n{msg_before.content}\n\n"
            f"**After**\n{msg_after.content}\n\n"
            f"[jump]({msg_after.jump_url})"
        )
        embed = info(msg, msg_before.guild.me, title="Message edited")
        embed.set_footer(text=f"Author: {msg_before.author}", icon_url=msg_before.author.avatar.url)
        await self.log_channel.send(embed=embed)

        # Check if the new message violates our security
        await self.security_check(msg_after)


async def setup(bot):
    await bot.add_cog(Security(bot))
