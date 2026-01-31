import logging
import datetime
from types import SimpleNamespace
from typing import Iterable

import discord
from discord import app_commands
from discord.ext import commands, tasks
from discord.errors import HTTPException

from bot import constants
from bot.api_client import ResponseCodeError
from bot.utils.misc import get_utc_time_until
from bot.utils.checks import check_if_it_is_tortoise_guild
from bot.utils.embed_handler import success, failure, welcome, footer_embed, info


logger = logging.getLogger(__name__)


ALIAS_MAP = {}
for num, rule in constants.RULES.items():
    for alias in rule["aliases"]:
        ALIAS_MAP[alias.lower()] = num


class TortoiseServer(commands.Cog):
    """These commands will only work in the tortoise discord server."""
    def __init__(self, bot):
        self.bot = bot
        self._tortoise_guild = None
        self._verified_role = None
        self._new_member_role = None
        self._member_count_channel = None
        self._log_channel = None
        self._verification_channel = None
        self._announcements_channel = None
        self._code_submissions_channel = None

    @property
    def tortoise_guild(self):
        if self._tortoise_guild is None:
            self._tortoise_guild = self.bot.get_guild(constants.tortoise_guild_id)
        return self._tortoise_guild

    @property
    def verified_role(self):
        if self._verified_role is None:
            self._verified_role = self.tortoise_guild.get_role(constants.verified_role_id)
        return self._verified_role

    @property
    def new_member_role(self):
        if self._new_member_role is None:
            self._new_member_role = self.tortoise_guild.get_role(constants.new_member_role)
        return self._new_member_role

    @property
    def member_count_channel(self):
        if self._member_count_channel is None:
            self._member_count_channel = self.bot.get_channel(constants.member_count_channel_id)
        return self._member_count_channel

    @property
    def log_channel(self):
        if self._log_channel is None:
            self._log_channel = self.bot.get_channel(constants.system_log_channel_id)
        return self._log_channel

    @property
    def verification_channel(self):
        if self._verification_channel is None:
            self._verification_channel = self.bot.get_channel(constants.verification_channel_id)
        return self._verification_channel

    @property
    def announcements_channel(self):
        if self._announcements_channel is None:
            self._announcements_channel = self.bot.get_channel(constants.announcements_channel_id)
        return self._announcements_channel

    @property
    def code_submissions_channel(self):
        if self._code_submissions_channel is None:
            self._code_submissions_channel = self.bot.get_channel(constants.code_submissions_channel_id)
        return self._code_submissions_channel

        self._database_role_update_lock = False
        self.SUGGESTION_MESSAGE_CONTENT = "React to this message to add new suggestion"


    async def _new_member_register_in_database(self, member: discord.Member):
        logger.info(f"New member {member} does not exist in database, adding now.")
        await self.bot.api_client.insert_new_member(member)
        await member.add_roles(self.new_member_role)
        await self.log_channel.send(embed=welcome(member))
        dm_msg = (
            "Welcome to Tortoise Community!\n\n"
            f"By joining the server you agree to our [rules]({constants.rules_url}).\n"
            f"You can read about our server from <#{constants.welcome_channel_id}> and "
            f"add roles to yourself from <#{constants.react_for_roles_channel_id}>\n\n"
            f"We hope you enjoy your stay!"
        )
        await member.send(embed=footer_embed(dm_msg, "Welcome"))

    async def _member_re_joined(self, member: discord.Member):
        logger.info(f"Member {member} re-joined and is verified in database, adding previous roles..")
        previous_roles = await self.bot.api_client.get_member_roles(member.id)
        await self.add_verified_roles_to_member(member, previous_roles)
        await self.bot.api_client.member_rejoined(member)
        await self.log_channel.send(embed=welcome(member))
        msg = (
            "Welcome back to Tortoise Community!\n\n"
            "The roles you had last time will be restored and added back to you.\n"
        )
        await member.send(embed=footer_embed(msg, "Welcome"))

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

    # @commands.Cog.listener()
    # @commands.check(check_if_it_is_tortoise_guild)
    async def on_message(self, message):
        if message.guild is None:
            return
        elif message.guild.id != constants.tortoise_guild_id:
            return

        # Suggestion message handler
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


    @tasks.loop(hours=24)
    async def remove_new_member_role(self):
        utc0 = datetime.timezone(offset=datetime.timedelta(hours=0))
        for member in self.new_member_role.members:
            if member.joined_at is None:
                continue

            join_duration = abs(datetime.datetime.now(tz=utc0).date() - member.joined_at.date())
            if join_duration.days >= 10:
                try:
                    await member.remove_roles(self.new_member_role, reason="New member role expired")
                except HTTPException:
                    logger.warning(f"Bot could't remove new member role from {member} {member.id}")


    @commands.command(enabled=False)
    @commands.check(check_if_it_is_tortoise_guild)
    async def deadline(self, ctx):
        """Shows how much time until Code Jam is over."""
        try:
            time_until_string = get_utc_time_until(year=2020, month=11, day=17, hour=23, minute=59, second=59)
            await ctx.send(embed=info(time_until_string, ctx.me, title="Code Jam ends in:"))
        except ValueError:
            await ctx.send(embed=info("Code Jam is over!", member=ctx.me, title="Finished"))




    # @commands.Cog.listener()
    # @commands.check(check_if_it_is_tortoise_guild)
    async def on_member_update(self, before, after):
        """
        We save all roles from member so he can get those roles back if he re-joins.
        """
        if before.pending is True and after.pending is False:

            logger.info(f"New member verified from discord {after}")
            try:
                member_meta = await self.bot.api_client.get_member_meta(after.id)
            except ResponseCodeError:
                await self._new_member_register_in_database(after)
            else:
                if member_meta["leave_date"] is None and member_meta["verified"]:
                    # Could be put to use for new website
                    pass
                else:
                    await self._member_re_joined(after)

        if before.roles == after.roles or self._database_role_update_lock:
            return

        roles_ids = [role.id for role in after.roles]
        logger.debug(f"Roles from member {after} changed, changing database field to: {roles_ids}")
        await self.bot.api_client.edit_member_roles(after, roles_ids)

    async def add_verified_roles_to_member(self, member: discord.Member, additional_roles: Iterable[int] = tuple()):
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

    # @commands.Cog.listener()
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
                await member.send(embed=embed, delete_after=10)

        elif payload.channel_id == constants.suggestions_channel_id:
            if payload.emoji.id == constants.suggestions_emoji_id:
                await self.bot.get_cog("TortoiseDM").on_raw_reaction_add_helper(payload)

    # @commands.Cog.listener()
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

    @commands.command(enabled=False)
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

    @app_commands.command(
        name="rules",
        description="Show all rules or a specific rule using alias"
    )
    @app_commands.describe(alias="Optional rule alias (e.g. dm, nsfw, ping, tos)")
    async def rules(self, interaction: discord.Interaction, alias: str | None = None):

        if alias:
            key = alias.lower().strip()
            rule_num = ALIAS_MAP.get(key)

            if not rule_num:
                await interaction.response.send_message(
                    embed=failure(f"Unknown rule alias: `{alias}`"),
                    ephemeral=True
                )
                return

            rule = constants.RULES[rule_num]

            embed = discord.Embed(
                title=f"Rule {rule_num}: {rule['title']}",
                color=discord.Color.dark_grey()
            )

            embed.description = (
                f"{rule['text']}\n"
            )
            embed.set_footer(text=f"Aliases: [{', '.join(rule['aliases'])}]")
            await interaction.response.send_message(embed=embed)
            return

        embed = discord.Embed(
            title="Tortoise - Programming Community Rules",
            color=discord.Color.dark_grey()
        )

        blocks = []
        for num in sorted(constants.RULES.keys()):
            rule = constants.RULES[num]
            block = (
                f"**{num}. {rule['title']}**"
                f"{rule['text']}\n"
                f"[aliases: {', '.join(rule['aliases'])}]"
            )
            blocks.append(block)

        embed.description = "\n\n".join(blocks) + "\n\n"
        embed.set_footer(text="Tortoise Community")
        await interaction.response.send_message(embed=embed)

    @commands.Cog.listener()
    async def on_ready(self):
        await self.remove_new_member_role.start()


async def setup(bot):
    await bot.add_cog(TortoiseServer(bot))
