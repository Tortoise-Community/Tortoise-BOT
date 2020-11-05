import logging

from discord.ext import commands

from bot.constants import embed_space
from bot.utils.paginator import EmbedPaginator


logger = logging.getLogger(__name__)


class PrettyHelpCommand(commands.MinimalHelpCommand):
    def __init__(self):
        super().__init__()
        self.paginator = EmbedPaginator(page_size=1000)

    def get_opening_note(self):
        return None

    def add_bot_commands_formatting(self, commands_, heading):
        if commands_:
            max_length = 19
            outputs = [f"`{c.name}{embed_space * (max_length - len(c.name))}{c.short_doc}`" for c in commands_]
            joined = "\n".join(outputs)
            self.paginator.add_line(f"\n\n**__{heading}__**\n")
            self.paginator.add_line(joined)

    async def send_pages(self):
        destination = self.get_destination()
        await self.paginator.start(destination, self.context.author, self.context.bot)


class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._original_help_command = bot.help_command
        bot.help_command = PrettyHelpCommand()
        bot.help_command.cog = self

    def cog_unload(self):
        """Revert to default help command in case cog is unloaded."""
        self.bot.help_command = self._original_help_command


def setup(bot):
    bot.add_cog(Help(bot))
