from collections import defaultdict
import discord
from discord.ext import commands, tasks
from discord import app_commands

from bot import constants
from bot.utils.embed_handler import info, success, failure
from bot.utils.checks import check_if_tortoise_staff


class RoleProgression(commands.Cog):

    def __init__(self, bot):

        self.bot = bot
        self.db = bot.progression_manager

        self._guild = None
        self._log_channel = None

        # message tracking
        self.message_cache = defaultdict(int)
        self.message_totals = defaultdict(int)

        self.flush_cache.start()

    def cog_unload(self):
        self.flush_cache.cancel()


    def role(self, role_id):
        return self.guild.get_role(role_id)

    @property
    def guild(self):
        if self._guild is None:
            self._guild = self.bot.get_guild(constants.tortoise_guild_id)
        return self._guild

    @property
    def log_channel(self):
        if self._log_channel is None:
            self._log_channel = self.bot.get_channel(constants.system_log_channel_id)
        return self._log_channel

    @property
    def boot_role(self):
        return self.role(constants.boot_role_id)

    @property
    def apprentice_role(self):
        return self.role(constants.apprentice_role_id)

    @property
    def fellow_role(self):
        return self.role(constants.fellow_role_id)

    @property
    def wizard_role(self):
        return self.role(constants.wizard_role_id)

    @property
    def trusted_role(self):
        return self.role(constants.trusted_role_id)

    @property
    def contributor_role(self):
        return self.role(constants.contributor_role_id)

    @property
    def mod_role(self):
        return self.role(constants.moderator_role_id)

    @property
    def active_role(self):
        return self.role(constants.active_role_id)

    @property
    def active_plus_role(self):
        return self.role(constants.active_plus_role_id)


    @tasks.loop(seconds=5)
    async def flush_cache(self):

        if not self.message_cache:
            return

        await self.db.add_messages_bulk(
            self.guild.id,
            dict(self.message_cache)
        )

        self.message_cache.clear()

    @flush_cache.before_loop
    async def before_flush(self):
        await self.bot.wait_until_ready()


    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):

        if not message.guild:
            return

        if message.guild.id != constants.tortoise_guild_id:
            return

        if message.author.bot:
            return

        if len(message.content) < 5:
            return

        member = message.author
        uid = member.id

        # increment caches
        self.message_cache[uid] += 1
        self.message_totals[uid] += 1

        total = self.message_totals[uid]


        if total == 50 and self.active_role not in member.roles:

            await member.add_roles(self.active_role)

            try:
                await member.send(
                    embed=info(
                        "You have earned the **Active** badge.\n" + constants.automatically_assigned_roles[self.active_role.id],
                         self.bot.user,
                        "Achievement Unlocked ✨",
                        "Issued only to the active members in the server!")
                )
            except discord.Forbidden:
                pass

            await self.log_channel.send(
                embed=info(f"{member.mention} reached **Active** milestone.", self.bot.user, "")
            )

        elif total == 500 and self.active_plus_role not in member.roles:

            await member.add_roles(self.active_plus_role)

            try:
                await member.send(
                    embed=info(
                        "You have earned the **Active+** badge.\n" + constants.automatically_assigned_roles[self.active_plus_role.id],
                         self.bot.user,
                        "You Rock 🌟",
                        "Issued only to the most active members!")
                )
            except discord.Forbidden:
                pass

            await self.log_channel.send(
                embed=info(f"{member.mention} reached **Active+** milestone.", self.bot.user, "")
            )

    def determine_stage(self, member: discord.Member):

        if self.boot_role not in member.roles:
            return "boot"

        if self.apprentice_role not in member.roles:
            return "apprentice"

        if self.fellow_role not in member.roles:
            return "fellow"

        return None

    def nominator_role(self, member: discord.Member):

        if self.mod_role in member.roles:
            return "moderator"

        if self.fellow_role in member.roles:
            return "fellow"

        if self.apprentice_role in member.roles:
            return "apprentice"

        return None

    def can_nominate(self, role_used: str, stage: str):

        if stage == "boot":
            return role_used in {"apprentice", "fellow", "moderator"}
        if stage == "apprentice":
            return role_used in {"fellow", "moderator"}
        if stage == "fellow":
            return role_used == "moderator"
        return False

    async def stage_passed(self, member, stage):

        apprentices, fellows, mods = await self.db.get_stage_counts(member.id, stage)

        if stage == "boot":
            if mods >= 1:
                return True
            if fellows >= 1:
                return True
            if apprentices >= 2:
                return True
            return False

        if stage == "apprentice":
            if mods >= 1:
                return True
            if fellows >= 2:
                return True
            return False

        if stage == "fellow":
            return mods >= 2

        return False


    async def promote_user(self, member, stage):

        role = getattr(self, stage)

        await member.add_roles(role)

        await self.db.clear_stage(member.id, stage)

        try:
            await member.send(
                embed=info(
                    f"You have been promoted to **{role.name}**.\n\n" + constants.progression_roles[role.id],
                    self.bot.user,
                    "Congratulations 🎉",
                    "Community nominations unlocked this progression."
                )
            )
        except discord.Forbidden:
            pass

        await self.log_channel.send(
            embed=info(f"{member.mention} was promoted to **{role.mention}**", self.bot.user, "")
        )

    @app_commands.command()
    @app_commands.checks.bot_has_permissions(manage_roles=True)
    @app_commands.check(check_if_tortoise_staff)
    async def promote(self, interaction: discord.Interaction, member: discord.Member, role: discord.Role):
        """Promote member to role."""
        if role.id not in constants.promotable_roles:

            if role.id in constants.progression_roles.keys():
                await interaction.response.send_message(
                    embed=failure(
                        "Direct promotion is not allowed.\n"
                        "Use `/nominate` to nominate this user instead."
                    ),
                    ephemeral=True
                )
                return

            if role.id in constants.automatically_assigned_roles.keys():
                await interaction.response.send_message(
                    embed=failure(
                        "This role is assigned automatically and cannot be promoted manually."
                    ),
                    ephemeral=True
                )
                return

            await interaction.response.send_message(
                embed=failure("You cannot promote users to this role."),
                ephemeral=True
            )
            return

        if role >= interaction.user.top_role:
            await interaction.response.send_message(
                embed=failure("Role needs to be below you in hierarchy."),
                ephemeral=True
            )
            return

        if role in member.roles:
            await interaction.response.send_message(
                embed=failure(f"{member.mention} already has role {role.mention}!"),
                ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        await member.add_roles(role)

        dm_embed = info(
            (
                f"You’ve been promoted to **{role.name}** role.\n\n"
                + constants.promotable_roles[role.id]
            ),
            self.bot.user,
            "You just got promoted!",
            f"Given by: {interaction.user}  |  Tortoise Programming Community"
        )
        try:
            await member.send(embed=dm_embed)
        except discord.Forbidden:
            pass
        await interaction.followup.send(
            embed=success(f"{member.mention} is promoted to {role.mention}", interaction.client.user), ephemeral=True)


    @app_commands.command(name="nominate")
    async def nominate(self, interaction: discord.Interaction, member: discord.Member):

        if interaction.user.id == member.id:
            await interaction.response.send_message(
                embed=failure("You cannot nominate yourself <:pomf:766290682087735347>"),
                ephemeral=True
            )

        stage = self.determine_stage(member)

        if stage is None:
            await interaction.response.send_message(
                embed=failure(f"{member.mention} already has the highest role."),
                ephemeral=True
            )
            return

        if stage == "boot" and self.active_role not in member.roles:
            await interaction.response.send_message(
                embed=failure(
                    f"User must have {self.active_role.mention} role before they could be nominated."
                ),
                ephemeral=True
            )
            return

        role_used = self.nominator_role(interaction.user)

        if role_used is None:
            await interaction.response.send_message(
                embed=failure(f"You need to be an {self.apprentice_role.mention} or above to nominate."),
                ephemeral=True
            )
            return

        if not self.can_nominate(role_used, stage):
            await interaction.response.send_message(
                embed=failure("You cannot nominate for this role level."),
                ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        inserted = await self.db.add_nomination(
            member.id,
            interaction.user.id,
            stage,
            role_used
        )

        if not inserted:
            await interaction.followup.send(
                embed=failure(f"You already nominated {member.mention} for this stage."),
                ephemeral=True
            )
            return

        await self.log_channel.send(
            embed=info(
                f"{interaction.user} nominated {member.mention} for **{stage}**."
            , self.bot.user, "")
        )

        if await self.stage_passed(member, stage):

            await self.promote_user(member, stage)

        else:

            apprentices, fellows, mods = await self.db.get_stage_counts(
                member.id,
                stage
            )

            progress = ""

            if stage == "boot":
                progress = (
                    "**Boot Promotion Progress**\n"
                    "━━━━━━━━━━━━━━━━━━━━\n\n"
                    "You can be promoted by **either** of the following:\n\n"
                    f"• Apprentice nominations: **{apprentices}/2**\n"
                    f"• Fellow nomination: **{fellows}/1**\n"
                    f"• Moderator nomination: **{mods}/1**"
                )

            elif stage == "apprentice":
                progress = (
                    "**Apprentice Promotion Progress**\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    "You can be promoted by **either** of the following:\n\n"
                    f"• Fellow nominations: **{fellows}/2**\n"
                    f"• Moderator nomination: **{mods}/1**"
                )

            elif stage == "fellow":
                progress = (
                    "**Fellow Promotion Progress**\n"
                    "━━━━━━━━━━━━━━━━━━━━━\n\n"
                    "Required nominations:\n\n"
                    f"• Moderator nominations: **{mods}/2**"
                )
            try:
                await member.send(
                    embed=info(
                        f"You were nominated for **{stage.capitalize()}** role.\n\n"
                        f"{progress}\n",
                        self.bot.user,
                        "Nominated 🎖️",
                        f"Nominated by {interaction.user}"
                    )
                )
            except discord.Forbidden:
                pass

        await interaction.followup.send(
            embed=success(f"You have successfully nominated {member.mention}."),
            ephemeral=True
        )

    @app_commands.command(name="progression", description="Learn about role progression and activity milestones.")
    async def progression_info(self, interaction: discord.Interaction):

        msg = (
            "## Server Role Progression\n\n"
            "Roles in this server recognize **activity, contribution, and trust within the community**. "
            "Some roles are earned automatically through participation, some are awarded through "
            "**community nominations**, and a few are **granted directly for special achievements or contributions**.\n\n"

            "### Activity Roles\n"
            "Earn these automatically by being active in chat.\n\n"

            f"{self.active_role.mention} - This marks you as an active community member\n\n"
            f"{self.active_plus_role.mention} - Shows consistent participation in discussions.\n\n"

            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

            "### Community Progression Roles\n"
            "These roles are awarded through **community nominations**.\n"
            "Members vote for users who contribute meaningfully to the server.\n\n"

            f"{self.boot_role.mention} - Entry level progression role.\n\n"
            "Requirements:\n"
            f"• Must already have **{self.active_role.name}**\n"
            "• Can be obtained through nominations from:\n"
            "  • **2 Apprentices**, OR\n"
            "  • **1 Fellow**, OR\n"
            "  • **1 Moderator**\n\n"

            f"{self.apprentice_role.mention} - Represents trusted and helpful members.\n\n"
            "Requirements:\n"
            "• Must already have **Boot**\n"
            "• Can be obtained through nominations from:\n"
            "  • **2 Fellows**, OR\n"
            "  • **1 Moderator**\n\n"

            f"{self.fellow_role.mention} - A respected member of the community.\n\n"
            "Requirements:\n"
            "• Must already have **Apprentice**\n"
            "• Can be obtained through nominations from:\n"
            "  • **2 Moderators**\n\n"

            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

            "### Special Recognition Roles\n"
            "These roles are **directly awarded** by staff for notable achievements or contributions "
            "to the community and its projects.\n\n"

            f"{self.wizard_role.mention} - Awarded to the member currently **#1 on the challenges leaderboard**, "
            "representing exceptional problem-solving skill and mastery.\n\n"

            f"{self.trusted_role.mention} - Given to long-standing members who have consistently "
            "demonstrated reliability and trust within the community.\n\n"

            f"{self.contributor_role.mention} - Recognizes members who contribute to our "
            "**GitHub repositories** through code, fixes, improvements, or development work.\n\n"

            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

            "**How Nominations Work**\n"
            "• Members nominate others using `/nominate`.\n"
            "• Each person can nominate **once per stage per role level**.\n"
            "• If someone gets promoted, previous nominations for that stage are cleared.\n"
            "• When enough nominations are collected, the promotion happens automatically.\n\n"

            "**What Makes Someone Worthy of Nomination?**\n"
            "• Helping other members\n"
            "• Positive community engagement\n"
            "• Sharing useful knowledge\n"
            f"• Being active and constructive\n\n{constants.embed_space}"
        )

        await interaction.response.send_message(
            embed=info(
                msg,
                self.bot.user,
                "",
                "💡 Roles in this server are meant to recognize "
                "genuine participation and contributions to the community. "
                "They are not something you should actively try to grind or chase.\n\n"
                "Tortoise Programming Community"
            ),
            ephemeral=False
        )



async def setup(bot):
    await bot.add_cog(RoleProgression(bot))