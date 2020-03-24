import discord
from discord.ext import commands
from discord.errors import Forbidden
from .utils.embed_handler import success

deterrence_log_channel_id = 597119801701433357
moderation_channel_id = 581139962611892229
unverified_role_id = 605808609195982864
verification_channel_id = 602156675863937024
muted_role_id = 610126555867512870


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
                                              f"\nIf this happened by a mistake contact moderators."
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
    async def ban(self, ctx, member: discord.Member, *, reason="Reason not stated."):
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
                                 description=(f"{msg_description}"
                                              f"\nIf this happened by a mistake contact moderators."),
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
                              description=("If you are planning to repeat this again, "
                                           "the mods may administer punishment for the action."),
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

    @commands.command()
    @commands.bot_has_permissions(manage_roles=True)
    @commands.has_permissions(manage_messages=True, manage_roles=True)
    async def mute(self, ctx, member: discord.Member, *, reason="No reason stated."):
        muted_role = ctx.guild.get_role(muted_role_id)
        await member.add_roles(muted_role, reason=reason)

    @commands.command()
    @commands.cooldown(1, 300, commands.BucketType.guild)
    @commands.has_permissions(manage_messages=True)
    async def dm_unverified(self, ctx):
        verification_channel = self.bot.get_channel(verification_channel_id)
        unverified_role = ctx.guild.get_role(unverified_role_id)
        unverified_members = [member for member in ctx.guild.members if unverified_role in member.roles]
        count = 0

        for member in unverified_members:
            try:
                msg = (f"Hey {member.mention}!\n"
                       f"You've been in our guild **{ctx.guild.name}** for quite a long time.."
                       f"We noticed you still didn't verify so please go to our channel "
                       f"{verification_channel.mention} and verify.")
                await member.send(msg)
                count += 1
            except Forbidden:
                pass

        await ctx.send(embed=success(F"Successfully notified {count} users.", ctx.me))


def setup(bot):
    bot.add_cog(Admins(bot))
