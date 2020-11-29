from typing import Tuple, Any
from asyncio import TimeoutError
from abc import ABC, abstractmethod

from discord import PartialEmoji
from discord.errors import NotFound
from discord.ext.commands import Bot
from discord import Member, Message, RawReactionActionEvent


class ReactionMessage(ABC):
    __slots__ = ("bot", "message", "action_member", "timeout", "silence_timeout_error")
    EMOJIS: Tuple[PartialEmoji, ...] = ()

    @classmethod
    async def create_instance(
            cls,
            bot: Bot,
            message: Message,
            action_member: Member,
            *,
            timeout: int = 120,
            silence_timeout_error: bool = True
    ) -> Any:
        """You need to await this class method to successfully initialize this class,
        you cannot directly initialize it as usual.

        :param bot: instance of bot
        :param message: message on which we will wait for reactions
        :param action_member: we will listen for reactions only from this member
        :param timeout: after how many second to stop listening to reactions
        :param silence_timeout_error: Should TimeOutError be re-raised or silently ignored?
        :return: whatever is returned by method react_action which you need to implement.
        """
        self = RemovableMessage()

        self.bot = bot
        self.message = message
        self.action_member = action_member
        self.timeout = timeout
        self.silence_timeout_error = silence_timeout_error

        for emoji in cls.EMOJIS:
            await self.message.add_reaction(emoji)

        return await self._listen()

    def _check(self, payload: RawReactionActionEvent) -> bool:
        return (
            payload.emoji in self.EMOJIS and
            payload.message_id == self.message.id and
            payload.user_id == self.action_member.id and
            payload.user_id != self.bot.user.id
        )

    async def _listen(self) -> Any:
        try:
            partial_emoji = await self.bot.wait_for("raw_reaction_add", check=self._check, timeout=self.timeout)
            return await self.react_action(partial_emoji)
        except TimeoutError as timeout_error:
            for emoji in self.EMOJIS:
                try:
                    await self.message.remove_reaction(emoji=emoji, member=self.bot.user)
                except NotFound:
                    pass  # If the message got deleted by user in the meantime

            if not self.silence_timeout_error:
                raise timeout_error

    @abstractmethod
    async def react_action(self, reacted_emoji: PartialEmoji) -> Any:
        """Implement what will happen when member reacts to message.
        This will get triggered if anyone reacted to this message with any of the emojis in EMOJIS.

        :param reacted_emoji: PartialEmoji that the member reacted with.
        :return: return anything you'd like if you're going to use it
        """
        pass


class RemovableMessage(ReactionMessage):
    EMOJIS: Tuple[PartialEmoji, ...] = (PartialEmoji(name="❌"), )

    async def react_action(self, reacted_emoji: PartialEmoji) -> None:
        await self.message.delete()


class ConfirmationMessage(ReactionMessage):
    EMOJIS: Tuple[PartialEmoji, ...] = (PartialEmoji(name="❌"), PartialEmoji(name="✅"))

    async def react_action(self, reacted_emoji: PartialEmoji) -> bool:
        return reacted_emoji == self.EMOJIS[1]
