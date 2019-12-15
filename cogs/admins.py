import discord
from discord.ext import commands
from discord.errors import Forbidden

support_admin_id = 125759308515246080
deterrence_log_channel_id = 597119801701433357


class Admins(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.bot_has_permissions(kick_members=True)
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason="No specific reason"):
        """
        Kicks  member from the guild.
        You will require kick_members permissions to use this command.

        """
        msg_title = "**Infraction information**"
        msg_description = ("**TYPE:** Kick\n"
                           f"**REASON:** {reason}\n"
                           "**DURATION:** 24 hours")

        deterrence_embed = discord.Embed(title=msg_title,
                                         description=(f"**NAME:** {member.name}\n"
                                                      f"{msg_description}"),
                                         color=0xFF0000)
        deterrence_embed.set_author(name="Tortoise Community", icon_url=ctx.me.avatar_url)
        deterrence_log_channel = self.bot.get_channel(deterrence_log_channel_id)
        await deterrence_log_channel.send(embed=deterrence_embed)

        dm_embed = discord.Embed(title=msg_title,
                                 description=(f"{msg_description}"
                                              f"\nIf this happened by a mistake contact <@{support_admin_id}>"
                                              "\nYou can rejoin the server after the cooldown from here"),
                                 color=0xFF0000)
        dm_embed.set_author(name="Tortoise Community", icon_url=ctx.me.avatar_url)
        try:
            await member.send(embed=dm_embed)
        except Forbidden:
            # Ignore exception in case user had blocked DMs
            pass

        await member.kick(reason=reason)

    @commands.command()
    @commands.bot_has_permissions(ban_members=True)
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member, *, reason="No specific reason"):
        """
        Bans  member from the guild.
        You will require ban_members permissions to use this command.

        """
        msg_title = "**Infraction information**"
        msg_description = ("**TYPE:** Ban\n"
                           f"**REASON:** {reason}\n"
                           "**DURATION:** Permanent")

        deterrence_embed = discord.Embed(title=msg_title,
                                         description=(f"**NAME:** {member.name}\n"
                                                      f"{msg_description}"),
                                         color=0xFF0000)
        deterrence_embed.set_author(name="Tortoise Community", icon_url=ctx.me.avatar_url)
        deterrence_log_channel = self.bot.get_channel(deterrence_log_channel_id)
        await deterrence_log_channel.send(embed=deterrence_embed)

        dm_embed = discord.Embed(title=msg_title,
                                 description=(f"{msg_description}",
                                              f"\nIf this happened by a mistake contact <@{support_admin_id}>"),
                                 color=0xFF0000)
        dm_embed.set_author(name="Tortoise Community", icon_url=ctx.me.avatar_url)
        try:
            await member.send(embed=dm_embed)
        except Forbidden:
            # Ignore exception in case user had blocked DMs
            pass

        await member.ban(reason=reason)

    @commands.command()
    @commands.has_any_role("Admin", "Moderator", "Helpers")
    async def warn(self, ctx, member: discord.Member, *, reason):
        """
        Warns a member.
        You will require appropriate role to use this command.

        """
        deterrence_log_channel = self.bot.get_channel(deterrence_log_channel_id)
        embed = discord.Embed(title=f"**{member.name} You have been warned for {reason}**",
                              description=f"If you are planning to repeat this again, "
                                          f"the mods may administer punishment for the action.",
                              color=0xF4D03F)
        await ctx.message.delete()
        await deterrence_log_channel.send(f"{member.mention}", delete_after=0.5)
        await deterrence_log_channel.send(embed=embed)

    @commands.command()
    @commands.bot_has_permissions(manage_roles=True)
    @commands.has_any_role("Admin", "Moderator", "Helpers")
    async def role(self, ctx, role: discord.Role, member: discord.Member):
        """
        Adds role to a member.
        You will require appropriate role to use this command.

        """

        await member.add_roles(role)
        embed = discord.Embed(title=f"Role Added!",
                              description=f"{member.mention} now has the role {role.mention}",
                              color=0x1ADB43)
        await ctx.send(embed=embed)

        dm_embed = discord.Embed(
            title=(f"**Congratulations!** \n\n"
                   f"You are now promoted to role **{role.name}** in our community.\n"
                   f"`'With great power comes great responsibility'`\n"
                   f"Be active and keep the community safe."),
            color=0xFFC300)
        dm_embed.set_footer(text="Tortoise community")
        await member.send(embed=dm_embed)

    @commands.command()
    @commands.bot_has_permissions(manage_messages=True)
    @commands.has_any_role("Admin", "Moderator", "Helpers")
    async def clear(self, ctx, amount: int):
        """
        Clears last X amount of messages.
        You will require appropriate role to use this command.

        """
        await ctx.channel.purge(limit=amount + 1)
        await ctx.send(f"**MESSAGES CLEARED** {ctx.author.mention}", delete_after=3)


def setup(bot):
    bot.add_cog(Admins(bot))
