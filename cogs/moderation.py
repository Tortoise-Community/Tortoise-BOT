import discord
from discord.ext import commands
from .utils.embed_handler import success
from .utils.checks import check_if_it_is_tortoise_guild

deterrence_log_channel_id = 597119801701433357
unverified_role_id = 605808609195982864
verification_channel_id = 602156675863937024
muted_role_id = 610126555867512870
verification_url = "https://www.tortoisecommunity.ml/verification/"


class Admins(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.bot_has_permissions(kick_members=True)
    @commands.has_permissions(kick_members=True)
    @commands.check(check_if_it_is_tortoise_guild)
    async def kick(self, ctx, member: discord.Member, *, reason="No specific reason"):
        """
        Kicks  member from the guild.
        You will require kick_members permissions to use this command.

        """
        msg_title = "**Infraction information**"
        msg_description = ("**TYPE:** Kick\n"
                           f"**REASON:** {reason}")

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

        await member.send(embed=dm_embed)
        await member.kick(reason=reason)
        await ctx.send(embed=success(f"{member.name} successfully kicked."))

    @commands.command()
    @commands.bot_has_permissions(ban_members=True)
    @commands.has_permissions(ban_members=True)
    @commands.check(check_if_it_is_tortoise_guild)
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

        await member.send(embed=dm_embed)
        await member.ban(reason=reason)
        await ctx.send(embed=success(f"{member.name} successfully banned."))

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    @commands.check(check_if_it_is_tortoise_guild)
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
    @commands.has_permissions(manage_roles=True)
    @commands.check(check_if_it_is_tortoise_guild)
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
    @commands.has_permissions(manage_messages=True)
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
    @commands.check(check_if_it_is_tortoise_guild)
    async def mute(self, ctx, member: discord.Member, *, reason="No reason stated."):
        muted_role = ctx.guild.get_role(muted_role_id)
        await member.add_roles(muted_role, reason=reason)

    @commands.command()
    @commands.cooldown(1, 300, commands.BucketType.guild)
    @commands.has_permissions(administrator=True)
    @commands.check(check_if_it_is_tortoise_guild)
    async def dm_unverified(self, ctx):
        unverified_role = ctx.guild.get_role(unverified_role_id)
        unverified_members = (member for member in unverified_role.members
                              if member.status == discord.Status.online)
        count = 0

        for member in unverified_members:
            msg = (f"Hey {member.mention}!\n"
                   f"You've been in our guild **{ctx.guild.name}** for some time..\n"
                   f"We noticed you still didn't verify so please go to our channel "
                   f"{verification_url} and verify.")
            await member.send(msg)
            count += 1

        await ctx.send(embed=success(f"Successfully notified {count} users.", ctx.me))

    @commands.command()
    @commands.cooldown(1, 300, commands.BucketType.guild)
    @commands.has_permissions(administrator=True)
    async def dm_members(self, ctx, role: discord.Role, *, message: str):
        members = (member for member in role.members
                   if not member.bot)
        count = 0

        for member in members:
            dm_embed = discord.Embed(title=f"Message for role {role}",
                                     description=message,
                                     color=role.color)
            dm_embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon_url)
            await member.send(embed=dm_embed)
            count += 1

        await ctx.send(embed=success(f"Successfully notified {count} users.", ctx.me))


def setup(bot):
    bot.add_cog(Admins(bot))
