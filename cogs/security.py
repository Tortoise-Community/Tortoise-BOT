import re
from discord.ext import commands

banned_words = {
    "Swear":           ["fuck", "shit", "asshole", "dickhead", "motherfucker", "slut", "bastard", "belland", "cunt",
                        "dick", "shithole"],
    "Homophobic Slur": ["faggot", "dyke"],
    "Racial Slur":     ["nigga", "nigger"],
    "Racial Abuse":    ["blackslave", "black slave"]
}


class Security(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):

        ctx = message.channel
        if message.author == message.guild.me:
            return

        # Check for invites
        # For this to work bot needs to have manage_guild permission (so he can get guild invites)
        if "https:" in message.content or "http:" in message.content:
            base_url = re.findall(r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+", message.content)
            for invite in base_url:
                if not await Security.check_if_invite_is_our_guild(invite, message.guild):
                    await ctx.send(f"{message.author.mention} You are not allowed to post other guild invites!")
                    await message.delete()
                    # TODO give him warning points etc / send to deterrence channel

        # Check for baned words
        for word in message.content.lower().split():
            for key in banned_words:
                if word in banned_words[key]:
                    await ctx.send(f"Curse word detected from category {key}!")
                    await message.delete()
                    # TODO: give him warning points or smth

    @staticmethod
    async def check_if_invite_is_our_guild(full_link, guild):
        guild_invites = await guild.invites()
        for invite in guild_invites:
            if invite.url == full_link:
                return True
        return False


def setup(bot):
    bot.add_cog(Security(bot))
