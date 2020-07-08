from typing import List, Union

from discord.ext.commands import Bot
from discord import User, Member, HTTPException


class Paginator:
    PAGE_SIZE = 500
    ARROW_TO_BEGINNING = "⏪"
    ARROW_BACKWARD = "◀"
    ARROW_FORWARD = "▶"
    ARROW_TO_END = "⏩"
    PAGINATION_EMOJIS = (ARROW_TO_BEGINNING, ARROW_BACKWARD, ARROW_FORWARD, ARROW_TO_END)

    def __init__(
            self,
            content: str,
            author: Union[User, Member],
            bot_reference: Bot,
            *,
            separator: str = "\n",
            timeout: int = 120,
            prefix: str = "",
            suffix: str = ""
    ):
        self._bot_ref = bot_reference
        self._author = author
        self._separator = separator
        self._timeout = timeout
        self._prefix = prefix
        self._suffix = suffix
        self._message = None
        self._page_index = 0
        self._pages = []
        self._max_page_size = self.PAGE_SIZE - len(self.get_prefix()) - len(self.get_suffix())
        self._pages = self.make_pages(content)

    def make_pages(self, content: str) -> List[str]:
        constructed_chunks = []
        chunk_list = content.split(self._separator)
        self.break_long_entries(chunk_list, self.PAGE_SIZE)

        temp_chunk = []
        for entry in chunk_list:
            # len(temp_chunk) is because we'll add separators in join
            if sum(map(len, temp_chunk)) + len(entry) + len(temp_chunk) >= self._max_page_size:
                constructed_chunks.append(self._separator.join(temp_chunk))
                temp_chunk = [entry]
            else:
                temp_chunk.append(entry)

        # For leftovers
        constructed_chunks.append(self._separator.join(temp_chunk))
        return constructed_chunks

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

    async def start(self, output):
        self._message = await output.send(self.get_message_content())
        if len(self._pages) > 1:
            # No need to paginate if there are no pages.
            await self._add_all_reactions()
            await self._start_listener()

    def get_prefix(self) -> str:
        return self._prefix

    def get_suffix(self) -> str:
        return f"{self._get_page_counter_message()}{self._suffix}"

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

    async def update_message(self):
        await self._message.edit(content=self.get_message_content())

    def get_message_content(self) -> str:
        return f"{self.get_prefix()}{self._pages[self._page_index]}{self.get_suffix()}"

    async def _remove_reaction(self, reaction):
        try:
            await self._message.remove_reaction(reaction, self._author)
        except HTTPException:
            # Silently ignore if no permission to remove reaction. (example DM)
            pass

    async def _start_listener(self):
        def react_check(reaction_, user_):
            return (
                str(reaction_) in self.PAGINATION_EMOJIS and
                user_.id == self._author.id and
                reaction_.message.id == self._message.id
            )

        while True:
            try:
                reaction, user = await self._bot_ref.wait_for("reaction_add", check=react_check, timeout=self._timeout)
            except TimeoutError:
                await self.clear_all_reactions()
                break

            if str(reaction) == self.ARROW_TO_BEGINNING:
                await self._remove_reaction(self.ARROW_TO_BEGINNING)
                if self._page_index > 0:
                    self._page_index = 0
                    await self.update_message()
            elif str(reaction) == self.ARROW_BACKWARD:
                await self._remove_reaction(self.ARROW_BACKWARD)
                if self._page_index > 0:
                    self._page_index -= 1
                    await self.update_message()
            elif str(reaction) == self.ARROW_FORWARD:
                await self._remove_reaction(self.ARROW_FORWARD)
                if self._page_index < len(self._pages) - 1:
                    self._page_index += 1
                    await self.update_message()
            elif str(reaction) == self.ARROW_TO_END:
                await self._remove_reaction(self.ARROW_TO_END)
                if self._page_index < len(self._pages) - 1:
                    self._page_index = len(self._pages) - 1
                    await self.update_message()
