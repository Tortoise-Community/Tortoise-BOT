import logging
from typing import Iterable

import discord
from discord.ext import commands
from discord.errors import HTTPException

import constants
from .utils.checks import check_if_it_is_tortoise_guild
from .utils.embed_handler import success, failure, authored, welcome, welcome_dm


logger = logging.getLogger(__name__)


class TortoiseServer(commands.Cog):
    """These commands will only work in the tortoise discord server."""
    def __init__(self, bot):
        self.bot = bot
        self._database_role_update_lock = False

    @commands.Cog.listener()
    @commands.check(check_if_it_is_tortoise_guild)
    async def on_member_join(self, member: discord.Member):
        log_channel = self.bot.get_channel(constants.system_log_channel_id)
        logger.debug(f"New member joined {member}")

        if not await self.bot.api_client.does_member_exist(member.id):
            logger.debug(f"New member {member} does not exist in database, adding now.")

            await self.bot.api_client.insert_new_member(member)

            unverified_role = member.guild.get_role(constants.unverified_role_id)
            await member.add_roles(unverified_role)

            await log_channel.send(embed=welcome(f"{member} has joined the Tortoise Community."))
            msg = ("Welcome to Tortoise Community!\n"
                   "In order to proceed and join the community you will need to verify.\n\n"
                   f"Please head over to {constants.verification_url}")
            await member.send(embed=welcome_dm(msg))
            return

        verified = await self.bot.api_client.is_verified(member.id)
        if verified:
            logger.debug(f"Member {member} is verified in database, adding roles.")

            previous_roles = await self.bot.api_client.get_member_roles(member.id)
            await self.add_verified_roles_to_member(member, previous_roles)

            logger.debug(f"Updating database as member re-joined.")
            await self.bot.api_client.member_rejoined(member)

            await log_channel.send(embed=welcome(f"{member} has returned to Tortoise Community."))
            msg = ("Welcome back to Tortoise Community!\n\n"
                   "The roles you had last time will be restored and added back to you.\n")
            await member.send(embed=welcome_dm(msg))
        else:
            logger.debug(f"Member {member} re-joined but is not verified in database, waiting for him to verify.")

            await self.bot.api_client.member_rejoined(member)

            unverified_role = member.guild.get_role(constants.unverified_role_id)
            await member.add_roles(unverified_role)

            await log_channel.send(embed=welcome(f"{member} has joined the Tortoise Community."))
            msg = ("Hi, welcome to Tortoise Community!\n"
                   "Seems like this is not your first time joining.\n\n"
                   f"Last time you didn't verify so please head over to {constants.verification_url}")
            await member.send(embed=welcome_dm(msg))

    @commands.Cog.listener()
    @commands.check(check_if_it_is_tortoise_guild)
    async def on_member_update(self, before, after):
        """
        We save all roles from member so he can get those roles back if he re-joins.
        """
        if before.roles == after.roles or self._database_role_update_lock:
            return

        roles_ids = [role.id for role in after.roles]
        logger.debug(f"Roles from member {after} changed, changing database field to: {roles_ids}")
        await self.bot.api_client.edit_member_roles(after, roles_ids)

    async def add_verified_roles_to_member(self, member: discord.Member, additional_roles: Iterable[int] = tuple()):
        guild = self.bot.get_guild(constants.tortoise_guild_id)
        verified_role = guild.get_role(constants.verified_role_id)
        unverified_role = guild.get_role(constants.unverified_role_id)
        try:
            await member.remove_roles(unverified_role)
        except HTTPException:
            logger.debug(f"Bot could't remove unverified role {unverified_role}")

        self._database_role_update_lock = True
        # In case additional_roles are fetched from database, they can be no longer existing due to not removing roles
        # that got deleted, so just catch Exception and ignore.
        roles = [guild.get_role(role_id) for role_id in additional_roles]
        roles.append(verified_role)
        for role in roles:
            try:
                await member.add_roles(role)
            except HTTPException:
                continue
        self._database_role_update_lock = False

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.channel_id == constants.react_for_roles_channel_id:
            guild = self.bot.get_guild(payload.guild_id)
            member = guild.get_member(payload.user_id)
            role = self.get_assignable_role(payload, guild)
            if role is not None:
                await member.add_roles(role)
                embed = success(f"`{role.name}` has been assigned to you in the Tortoise community.")
                await member.send(embed=embed)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        if payload.channel_id == constants.react_for_roles_channel_id:
            guild = self.bot.get_guild(payload.guild_id)
            member = guild.get_member(payload.user_id)
            role = self.get_assignable_role(payload, guild)
            if role is not None:
                await member.remove_roles(role)

    @classmethod
    def get_assignable_role(cls, payload, guild):
        role_id = constants.self_assignable_roles.get(payload.emoji.id)
        if role_id is not None:
            role = guild.get_role(role_id)
            if role is not None:
                return role
            else:
                logger.critical(f"Emoji id found in dictionary but role id {role_id} not found in guild!")
        else:
            logger.critical(f"No mapping for emoji {payload.emoji.id} in self_assignable_roles!")

    @commands.command()
    @commands.check(check_if_it_is_tortoise_guild)
    async def submit(self, ctx):
        """Initializes process of submitting code for event."""
        dm_msg = ("Submitting process has begun.\n\n"
                  "Please reply with 1 message below that either contains your full code or, "
                  "if it's too long, contains a link to code (pastebin/hastebin..)\n"
                  "If using those services make sure to set code to private and "
                  "expiration date to at least 30 days.")
        await ctx.author.send(embed=authored(ctx.guild.me, dm_msg))

        def check(msg):
            return msg.author == ctx.author and msg.guild is None

        try:
            code_msg = await self.bot.wait_for("message", check=check, timeout=300)
        except TimeoutError:
            await ctx.send(embed=failure("You took too long to reply."))
            return

        code_submissions_channel = self.bot.get_channel(constants.code_submissions_channel_id)

        title = f"Submission from {ctx.author}"
        embed = discord.Embed(title=title, description=code_msg.content, color=ctx.me.top_role.color)
        embed.set_thumbnail(url=ctx.author.avatar_url)

        await code_submissions_channel.send(embed=embed)

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    @commands.check(check_if_it_is_tortoise_guild)
    async def announce(self, ctx, *, arg):
        announcements_channel = self.bot.get_channel(constants.announcements_channel_id)
        await announcements_channel.send(arg)
        await ctx.send(success("Announced ✅"))

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    @commands.check(check_if_it_is_tortoise_guild)
    async def welcome(self, ctx, *, arg):
        channel = self.bot.get_channel(constants.welcome_channel_id)
        await channel.send(arg)
        await ctx.send(success("Added in Welcome ✅"))


def setup(bot):
    bot.add_cog(TortoiseServer(bot))
