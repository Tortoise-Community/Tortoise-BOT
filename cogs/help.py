import logging
import discord
from discord.ext import commands
from utils.embed_handler import embed_space

logger = logging.getLogger(__name__)


class PrettyHelpCommand(commands.MinimalHelpCommand):
    def get_ending_note(self):
        command_name_ = self.invoked_with
        return ("Type {0}{1} <command> for more info on a command.\n"
                "You can also type {0}{1} <category> for more info on a category.").format(self.clean_prefix, command_name_)

    def add_bot_commands_formatting(self, commands_, heading):
        if commands_:
            max_length = 19
            outputs = [f"`  {c.name}{embed_space * (max_length - len(c.name))}{c.short_doc}`" for c in commands_]
            joined = "\n".join(outputs)
            self.paginator.add_line(f"\n**__{heading}__**")
            self.paginator.add_line(joined)

    async def send_pages(self):
        destination = self.get_destination()
        for page in self.paginator.pages:
            embed = discord.Embed(title=discord.Embed.Empty, description=page, color=self.context.me.top_role.color)
            await destination.send(embed=embed)


class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._original_help_command = bot.help_command
        bot.help_command = PrettyHelpCommand()
        bot.help_command.cog = self

    def cog_unload(self):
        """
        Revert to default help command in case cog is unloaded.

        """
        self.bot.help_command = self._original_help_command


def setup(bot):
    bot.add_cog(Help(bot))
