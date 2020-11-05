from typing import List, Union
from asyncio import TimeoutError

from discord.abc import Messageable
from discord import ClientUser, User, Member, HTTPException
from discord.ext import commands

from bot.utils.embed_handler import info


class Paginator:
    ARROW_TO_BEGINNING = "⏪"
    ARROW_BACKWARD = "◀"
    ARROW_FORWARD = "▶"
    ARROW_TO_END = "⏩"
    PAGINATION_EMOJIS = (ARROW_TO_BEGINNING, ARROW_BACKWARD, ARROW_FORWARD, ARROW_TO_END)

    def __init__(
            self,
            *,
            page_size: int = 2000,
            separator: str = "\n",
            timeout: int = 120,
            prefix: str = "",
            suffix: str = ""
    ):
        """

        :param page_size: Maximum page string size for the page content.
        :param separator: Separator used to break large chunks of content to smaller ones, if needed.
        :param timeout: How long will the reactions be awaited for.
        :param prefix: Prefix for the message content.
        :param suffix: Suffix for the message content.
        """
        self._separator = separator
        self._timeout = timeout
        self._prefix = prefix
        self._suffix = suffix
        self._message = None
        self._page_index = 0
        self._content = []
        self._pages = []
        self._max_page_size = page_size - len(self.prefix) - len(self.suffix)

    def _make_pages(self) -> List[str]:
        pages = []
        chunks = self.content.split(self._separator)
        self.break_long_entries(chunks, self._max_page_size)

        temp_page = []
        for entry in chunks:
            # len(temp_chunk) is because we'll add separators in join
            if sum(map(len, temp_page)) + len(entry) + len(temp_page) >= self._max_page_size:
                pages.append(self._separator.join(temp_page))
                temp_page = [entry]
            else:
                temp_page.append(entry)

        # For leftovers
        pages.append(self._separator.join(temp_page))
        return pages

    @staticmethod
    def break_long_entries(chunk_list: List[str], max_chunk_size: int):
        """
        We further break down chunk_list in case any of the entries are larger than max_chunk_size.
        Modifies passed list in place!
        Will throw RecursionError if the string length in list is mega-huge.
        Basically when the entry is found just split it in half and re-add it in list without breaking order.
        Split in half will be done as many times as needed as long as resulting entry is larger than max_chunk_size
        :param chunk_list: list of strings
        :param max_chunk_size: integer, if chunk is larger that this we break it down
        """
        for i, entry in enumerate(chunk_list):
            if len(entry) > max_chunk_size:
                # Split string in 2 parts by the middle
                f, s = entry[:len(entry) // 2], entry[len(entry) // 2:]
                # Append them back to our list, not breaking order
                chunk_list[i] = s
                chunk_list.insert(i, f)
                # Keep doing that until there is no entries that are larger in length than max_msg_size
                Paginator.break_long_entries(chunk_list, max_chunk_size)
                break

    async def start(self, destination: Messageable, author: Union[User, Member], bot_reference):
        self._pages = self._make_pages()
        await self.create_message(destination)
        if len(self._pages) > 1:
            # No need to paginate if there are no pages.
            await self._add_all_reactions()
            await self._start_listener(author, bot_reference)

    def close_page(self):
        # Just to condone to standard paginator
        pass

    @property
    def prefix(self) -> str:
        return self._prefix

    @property
    def suffix(self) -> str:
        return f"{self._get_page_counter_message()}{self._suffix}"

    @property
    def max_size(self) -> int:
        return self._max_page_size

    @property
    def pages(self) -> List[str]:
        return self._pages

    @property
    def content(self) -> str:
        return "".join(self._content)

    def clear(self):
        self._pages = []
        self._page_index = 0

    def add_line(self, line: str = "", **kwargs):
        self._content.append(line)

    def _get_page_counter_message(self) -> str:
        return f"\n\nPage[{self._page_index + 1:<2}/{len(self._pages):<2}]"

    async def _add_all_reactions(self):
        for emoji in self.PAGINATION_EMOJIS:
            await self._message.add_reaction(emoji)

    async def clear_all_reactions(self):
        try:
            await self._message.clear_reactions()
        except HTTPException:
            # Silently ignore if no permission to remove reaction.
            pass

    async def create_message(self, destination: Messageable) -> None:
        self._message = await destination.send(self.get_message_content())

    async def update_message(self) -> None:
        await self._message.edit(content=self.get_message_content())

    def get_message_content(self) -> str:
        return f"{self.prefix}{self._pages[self._page_index]}{self.suffix}"

    async def _remove_reaction(self, reaction, author: Union[User, Member]):
        try:
            await self._message.remove_reaction(reaction, author)
        except HTTPException:
            # Silently ignore if no permission to remove reaction. (example DM)
            pass

    async def _start_listener(self, author: Union[User, Member], bot_reference):
        def react_check(reaction_, user_):
            return (
                str(reaction_) in self.PAGINATION_EMOJIS and
                user_.id == author.id and
                reaction_.message.id == self._message.id
            )

        while True:
            try:
                reaction, user = await bot_reference.wait_for("reaction_add", check=react_check, timeout=self._timeout)
            except TimeoutError:
                await self.clear_all_reactions()
                break

            if str(reaction) == self.ARROW_TO_BEGINNING:
                await self._remove_reaction(self.ARROW_TO_BEGINNING, author)
                if self._page_index > 0:
                    self._page_index = 0
                    await self.update_message()
            elif str(reaction) == self.ARROW_BACKWARD:
                await self._remove_reaction(self.ARROW_BACKWARD, author)
                if self._page_index > 0:
                    self._page_index -= 1
                    await self.update_message()
            elif str(reaction) == self.ARROW_FORWARD:
                await self._remove_reaction(self.ARROW_FORWARD, author)
                if self._page_index < len(self._pages) - 1:
                    self._page_index += 1
                    await self.update_message()
            elif str(reaction) == self.ARROW_TO_END:
                await self._remove_reaction(self.ARROW_TO_END, author)
                if self._page_index < len(self._pages) - 1:
                    self._page_index = len(self._pages) - 1
                    await self.update_message()


class EmbedPaginator(Paginator):
    def __init__(self, embed_title: str = "", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._embed_title = embed_title

    @classmethod
    def _get_bot_member_from_destination(cls, destination: Messageable) -> Union[Member, ClientUser]:
        try:
            # noinspection PyUnresolvedReferences
            return destination.guild.me
        except AttributeError:
            # noinspection PyUnresolvedReferences
            return destination.me

    async def create_message(self, destination) -> None:
        self._message = await destination.send(
            embed=info(
                self.get_message_content(),
                self._get_bot_member_from_destination(destination),
                title=self._embed_title
            )
        )

    async def update_message(self):
        await self._message.edit(
            embed=info(
                self.get_message_content(),
                self._get_bot_member_from_destination(self._message.channel),
                title=self._embed_title
            )
        )


class ListPaginator:
    """Constructs a Paginator when provided a list of Embeds/Messages"""
    def __init__(
            self, ctx: commands.Context, page_list,
            restart_button="⏮",
            back_button="◀",
            forward_button="⏭",
            next_button="▶",
            pause_button="⏸",
            stop_button="⏹"
    ):
        self.pages = page_list
        self.ctx = ctx
        self.bot = ctx.bot

        self.restart_button = restart_button
        self.back_button = back_button
        self.pause_button = pause_button
        self.forward_button = forward_button
        self.next_button = next_button
        self.stop_button = stop_button

    def get_next_page(self, page):
        pages = self.pages

        if page != pages[-1]:
            current_page_index = pages.index(page)
            next_page = pages[current_page_index+1]
            return next_page

        return pages[-1]

    def get_prev_page(self, page):
        pages = self.pages

        if page != pages[0]:
            current_page_index = pages.index(page)
            next_page = pages[current_page_index-1]
            return next_page

        return pages[0]

    async def start(self):
        pages = self.pages
        ctx = self.ctx

        embed = pages[0]

        msg = await ctx.send(embed=embed)

        emote_list = [self.restart_button, self.back_button, self.pause_button,
                      self.next_button, self.forward_button, self.stop_button]

        for emote in emote_list:
            await msg.add_reaction(emote)

        def check(_reaction, _user):
            return _user == ctx.author and str(_reaction.emoji) in emote_list and _reaction.message == msg

        current_page = embed

        try:
            while True:
                reaction, user = await self.bot.wait_for('reaction_add', timeout=60, check=check)

                if str(reaction.emoji) == self.restart_button:
                    await msg.edit(embed=pages[0])
                    current_page = pages[0]
                    await msg.remove_reaction(self.restart_button, ctx.author)
                elif str(reaction.emoji) == self.forward_button:

                    await msg.edit(embed=pages[-1])
                    current_page = pages[-1]

                    await msg.remove_reaction(self.forward_button, ctx.author)
                elif str(reaction.emoji) == self.next_button:
                    next_page = self.get_next_page(current_page)
                    await msg.edit(embed=self.get_next_page(current_page))
                    current_page = next_page

                    await msg.remove_reaction(self.next_button, ctx.author)

                elif str(reaction.emoji) == self.pause_button:
                    await msg.clear_reactions()
                    break

                elif str(reaction.emoji) == self.stop_button:
                    await msg.delete()
                    break

                elif str(reaction.emoji) == self.back_button:
                    prev_page = self.get_prev_page(current_page)
                    await msg.edit(embed=prev_page)
                    current_page = prev_page
                    await msg.remove_reaction(self.back_button, ctx.author)

        except TimeoutError:
            await msg.clear_reactions()
