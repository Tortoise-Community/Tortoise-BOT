import logging
from typing import Iterable
from discord import Member, HTTPException
from discord.ext import commands
from .utils.checks import check_if_it_is_tortoise_guild
from .utils.embed_handler import welcome, welcome_dm
from bot import Bot


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
tortoise_guild_id = 577192344529404154
tortoise_bot_dev_channel_id = 692851221223964822
tortoise_log_channel_id = 593883395436838942
tortoise_successful_verification_channel_id = 581139962611892229
verified_role_id = 599647985198039050
unverified_role_id = 605808609195982864
verification_url = "https://www.tortoisecommunity.ml/verification/"


class TortoiseAPI(commands.Cog):
    """Commands using Tortoise API"""
    def __init__(self, bot: Bot):
        self.bot: Bot = bot
        self._database_role_update_lock = False

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    @commands.check(check_if_it_is_tortoise_guild)
    async def is_verified(self, ctx, member: Member):
        response = await self.bot.api_client.is_verified(member.id)
        await ctx.send(response)

    @commands.Cog.listener()
    async def on_member_join(self, member: Member):
        if member.guild.id != tortoise_guild_id:
            # Functionality only available in Tortoise guild
            return

        log_channel = self.bot.get_channel(tortoise_log_channel_id)
        logger.debug(f"New member joined {member}")

        if not await self.bot.api_client.does_member_exist(member.id):
            logger.debug(f"New member {member} does not exist in database, adding now.")
            await self.bot.api_client.insert_new_member(member)

            await log_channel.send(embed=welcome(f"{member} has joined the Tortoise Community."))
            msg = ("Welcome to Tortoise Community!\n"
                   "In order to proceed and join the community you will need to verify.\n\n"
                   f"Please head over to {verification_url}")
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

            await log_channel.send(embed=welcome(f"{member} has joined the Tortoise Community."))
            msg = ("Hi, welcome to Tortoise Community!\n"
                   "Seems like this is not your first time joining.\n\n"
                   f"Last time you didn't verify so please head over to {verification_url}")
            await member.send(embed=welcome_dm(msg))

    @commands.Cog.listener()
    async def on_member_remove(self, member: Member):
        if member.guild.id != tortoise_guild_id:
            # Functionality only available in Tortoise guild
            return

        logger.debug(f"Member {member} left, updating database accordingly.")
        await self.bot.api_client.member_left(member)

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        """
        We save all roles from member so he can get those roles back if he re-joins.
        """
        if after.guild.id != tortoise_guild_id:
            # Functionality only available in Tortoise guild
            return
        elif before.roles == after.roles or self._database_role_update_lock:
            return

        roles_ids = [role.id for role in after.roles]
        logger.debug(f"Roles from member {after} changed, changing database field to: {roles_ids}")
        await self.bot.api_client.edit_member_roles(after, roles_ids)

    async def add_verified_roles_to_member(self, member: Member, additional_roles: Iterable[int] = tuple()):
        guild = self.bot.get_guild(tortoise_guild_id)
        verified_role = guild.get_role(verified_role_id)
        unverified_role = guild.get_role(unverified_role_id)
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


def setup(bot):
    bot.add_cog(TortoiseAPI(bot))
