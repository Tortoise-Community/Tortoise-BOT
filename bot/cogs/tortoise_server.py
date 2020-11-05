import logging
from types import SimpleNamespace
from typing import Iterable, Union

import discord
from discord.ext import commands, tasks
from discord.errors import HTTPException

from bot import constants
from bot.api_client import ResponseCodeError
from bot.utils.misc import get_utc0_time_until
from bot.utils.checks import check_if_it_is_tortoise_guild
from bot.utils.embed_handler import (
    success, warning, failure, welcome, footer_embed, info, RemovableMessage
)


logger = logging.getLogger(__name__)


class TortoiseServer(commands.Cog):
    """These commands will only work in the tortoise discord server."""
    def __init__(self, bot):
        self.bot = bot

        self.tortoise_guild = bot.get_guild(constants.tortoise_guild_id)
        self.verified_role = self.tortoise_guild.get_role(constants.verified_role_id)
        self.unverified_role = self.tortoise_guild.get_role(constants.unverified_role_id)
        self.member_count_channel = bot.get_channel(constants.member_count_channel)
        self.log_channel = bot.get_channel(constants.system_log_channel_id)
        self.verification_channel = bot.get_channel(constants.verification_channel_id)
        self.welcome_channel = bot.get_channel(constants.welcome_channel_id)
        self.announcements_channel = bot.get_channel(constants.announcements_channel_id)
        self.code_submissions_channel = bot.get_channel(constants.code_submissions_channel_id)

        self._database_role_update_lock = False
        self._rules = None
        self.update_member_count_channel.start()
        self.bot.loop.create_task(self.refresh_rules_helper())
        self.SUGGESTION_MESSAGE_CONTENT = "React to this message to add new suggestion"

    async def create_new_suggestion_message(self) -> int:
        suggestions_channel = self.bot.get_channel(constants.suggestions_channel_id)
        suggestion_embed = info(
            self.SUGGESTION_MESSAGE_CONTENT,
            suggestions_channel.guild.me,
            "New suggestion"
        )
        msg = await suggestions_channel.send(embed=suggestion_embed)
        suggestion_emoji = self.bot.get_emoji(constants.suggestions_emoji_id)
        await msg.add_reaction(suggestion_emoji)
        return msg.id

    @commands.Cog.listener()
    @commands.check(check_if_it_is_tortoise_guild)
    async def on_message(self, message):
        if message.guild is None:
            return
        elif message.guild.id != constants.tortoise_guild_id:
            return

        if not message.author.bot and len(message.content) > constants.max_message_length:
            # Below part is when someone sends too long message, bot will recommend them to use our pastebin
            # TODO we are skipping message deletion for now until we implement system to check
            #  if sent message is code or not
            msg = (
                "Your message is quite long.\n"
                f"You should consider using our paste service {constants.tortoise_paste_service_link}"
            )
            await message.channel.send(embed=warning(msg))

        if message.channel.id == constants.suggestions_channel_id:
            if (
                message.author == self.bot.user and
                message.embeds and
                message.embeds[0].description == self.SUGGESTION_MESSAGE_CONTENT
            ):
                await self.bot.api_client.edit_suggestion_message_id(message.id)
            else:
                old_suggestion_msg_id = await self.bot.api_client.get_suggestion_message_id()
                try:
                    old_message = await message.channel.fetch_message(old_suggestion_msg_id)
                except discord.NotFound:
                    pass
                else:
                    await old_message.delete()

                await self.create_new_suggestion_message()

    async def refresh_rules_helper(self):
        try:
            self._rules = await self.bot.api_client.get_all_rules()
        except Exception as e:
            msg = f"Failed to fetch rules from API:{e}"
            logger.critical(msg)
            await self.bot.log_error(msg)

    @tasks.loop(minutes=60)
    async def update_member_count_channel(self):
        guild = self.member_count_channel.guild
        await self.member_count_channel.edit(name=f"Member count {len(guild.members)}")

    @commands.command()
    @commands.check(check_if_it_is_tortoise_guild)
    async def deadline(self, ctx):
        try:
            time_until_string = get_utc0_time_until(year=2020, month=11, day=17, hour=23, minute=59, second=59)
            await ctx.send(embed=info(time_until_string, ctx.me, title="Code Jam ends in:"))
        except ValueError:
            await ctx.send(embed=info("Code Jam is over!", member=ctx.me, title="Finished"))

    @commands.command()
    @commands.check(check_if_it_is_tortoise_guild)
    async def rule(self, ctx, alias: Union[int, str]):
        """
        Shows rule based on number order or alias.
        """
        if isinstance(alias, int):
            rule_dict = self._get_rule_by_value(alias)
        else:
            rule_dict = self._get_rule_by_alias(alias)

        if rule_dict is None:
            await ctx.send(embed=failure("No such rule."), delete_after=5)
        else:
            await ctx.send(embed=info(rule_dict["statement"], ctx.guild.me, f"Rule: {rule_dict['name']}"))

    def _get_rule_by_value(self, number: int) -> Union[dict, None]:
        for rule_dict in self._rules:
            if rule_dict["number"] == number:
                return rule_dict

    def _get_rule_by_alias(self, alias: str) -> Union[dict, None]:
        for rule_dict in self._rules:
            if alias.lower() in rule_dict["alias"]:
                return rule_dict

    @commands.command()
    @commands.check(check_if_it_is_tortoise_guild)
    async def rules(self, ctx):
        """
        Shows all rules info.
        """
        embed_body = []
        for rule_dict in self._rules:
            rule_entry = (
                f"**{rule_dict['number']}. {rule_dict['name']}**\n"
                f"{rule_dict['statement']}\n"
                f"[**aliases: **{', '.join(rule_dict['alias'])}]"
            )
            embed_body.append(rule_entry)

        rules_embed = info("\n\n".join(embed_body), ctx.guild.me, f"{ctx.guild.name} Rules")
        rules_embed.set_footer(text="Tortoise Community")
        rules_embed.set_thumbnail(url=ctx.guild.icon_url)

        message = await ctx.send(embed=rules_embed)
        await RemovableMessage.create_instance(self.bot, message, ctx.author)

    @commands.Cog.listener()
    @commands.check(check_if_it_is_tortoise_guild)
    async def on_member_join(self, member: discord.Member):
        logger.info(f"New member joined {member}")
        try:
            member_meta = await self.bot.api_client.get_member_meta(member.id)
        except ResponseCodeError:
            await self._new_member_register_in_database(member)
        else:
            if member_meta["leave_date"] is None and member_meta["verified"]:
                pass
            else:
                await self._new_member_re_joined(member, member_meta["verified"])

    async def _new_member_register_in_database(self, member: discord.Member):
        logger.info(f"New member {member} does not exist in database, adding now.")
        await self.bot.api_client.insert_new_member(member)
        await member.add_roles(self.unverified_role)
        # Ghost ping the member so he takes note of verification channel where all info is
        await self.verification_channel.send(member.mention, delete_after=1)
        await self.log_channel.send(embed=welcome(f"{member} has joined the Tortoise Community."))
        dm_msg = (
            "Welcome to Tortoise Community!\n"
            "In order to proceed and join the community you will need to verify.\n\n"
            f"Please head over to\n{constants.verification_url}"
        )
        await member.send(embed=footer_embed(dm_msg, "Welcome"))

    async def _new_member_direct_access(self, member: discord.Member):
        logger.info(f"Member {member} joined directly from website, giving access to guild.")
        await self.add_verified_roles_to_member(member)
        await self.bot.api_client.member_rejoined(member)
        await self.log_channel.send(embed=welcome(f"{member} has joined to Tortoise Community."))
        msg = (
            "Welcome to Tortoise Community!\n\n"
            "We see you've come directly from our website after verification,\n"
            "you've been given access to our server, enjoy your stay."
        )
        await member.send(embed=footer_embed(msg, "Welcome"))

    async def _new_member_re_joined(self, member: discord.Member, verified: bool):
        if verified:
            logger.info(f"Member {member} re-joined and is verified in database, adding previous roles..")
            previous_roles = await self.bot.api_client.get_member_roles(member.id)
            await self.add_verified_roles_to_member(member, previous_roles)
            await self.bot.api_client.member_rejoined(member)
            await self.log_channel.send(embed=welcome(f"{member} has returned to Tortoise Community."))
            msg = (
                "Welcome back to Tortoise Community!\n\n"
                "The roles you had last time will be restored and added back to you.\n"
            )
            await member.send(embed=footer_embed(msg, "Welcome"))
        else:
            logger.info(f"Member {member} re-joined but is not verified in database, waiting for him to verify.")
            await self.bot.api_client.member_rejoined(member)
            await member.add_roles(self.unverified_role)
            await self.log_channel.send(embed=welcome(f"{member} has joined the Tortoise Community."))
            # Ghost ping the member so he takes note of verification channel where all info is
            await self.verification_channel.send(member.mention, delete_after=1)
            msg = (
                "Hi, welcome to Tortoise Community!\n"
                "Seems like this is not your first time joining.\n\n"
                f"Last time you didn't verify so please head over to {constants.verification_url}"
            )
            await member.send(embed=footer_embed(msg, "Welcome"))

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
        try:
            await member.remove_roles(self.unverified_role)
        except HTTPException:
            logger.debug(f"Bot could't remove unverified role {self.unverified_role}")

        self._database_role_update_lock = True
        # In case additional_roles are fetched from database, they can be no longer existing due to not removing roles
        # that got deleted, so just catch Exception and ignore.
        roles = [self.tortoise_guild.get_role(role_id) for role_id in additional_roles]
        roles.append(self.verified_role)

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

            if member.id == self.bot.user.id:
                return  # Ignore the bot
            elif role is not None:
                await member.add_roles(role)
                embed = success(f"`{role.name}` has been assigned to you in the Tortoise community.")
                await member.send(embed=embed)

        elif payload.channel_id == constants.suggestions_channel_id:
            if payload.emoji.id == constants.suggestions_emoji_id:
                await self.bot.get_cog("TortoiseDM").on_raw_reaction_add_helper(payload)

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
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def submit(self, ctx):
        """Initializes process of submitting code for event."""
        fake_payload = SimpleNamespace()
        fake_payload.user_id = ctx.author.id
        fake_payload.emoji = self.bot.get_emoji(constants.event_emoji_id)
        await self.bot.get_cog("TortoiseDM").on_raw_reaction_add_helper(fake_payload)
        await ctx.send(embed=info(
            "Check your DMs.\n"
            "Note: if you already have active DM option nothing will happen.",
            ctx.me)
        )


def setup(bot):
    bot.add_cog(TortoiseServer(bot))
