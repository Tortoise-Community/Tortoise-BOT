from collections import defaultdict
import discord
from discord.ext import commands, tasks
from discord import app_commands

from bot import constants
from bot.utils.embed_handler import info, success, failure


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
    def boot(self):
        return self.role(constants.boot_role_id)

    @property
    def apprentice(self):
        return self.role(constants.apprentice_role_id)

    @property
    def fellow(self):
        return self.role(constants.fellow_role_id)

    @property
    def mod(self):
        return self.role(constants.moderator_role_id)

    @property
    def active(self):
        return self.role(constants.active_role_id)

    @property
    def active_plus(self):
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


        if total == 5 and self.active not in member.roles:

            await member.add_roles(self.active)

            try:
                await member.send(
                    embed=info(
                        "You have earned the **Active** badge.\n"
                        "Thank you for staying active and engaging in the server.\n\n"
                        "Next milestone: **Active+**",
                         self.bot.user,
                        "Achievement Unlocked ✨",
                        "Issued only to the active users in the server!")
                )
            except discord.Forbidden:
                pass

            await self.log_channel.send(
                embed=info(f"{member.mention} reached **Active** milestone.", self.bot.user, "")
            )

        elif total == 7 and self.active_plus not in member.roles:

            await member.add_roles(self.active_plus)

            try:
                await member.send(
                    embed=info(
                        "You have earned the **Active+** badge.\n"
                        "Your activity and engagement place you among the server's top contributors.\n"
                        "We appreciate the energy you bring to the community\n",
                         self.bot.user,
                        "You Rock 🌟",
                        "Issued only to the most active users!")
                )
            except discord.Forbidden:
                pass

            await self.log_channel.send(
                embed=info(f"{member.mention} reached **Active+** milestone.", self.bot.user, "")
            )

    def determine_stage(self, member: discord.Member):

        if self.boot not in member.roles:
            return "boot"

        if self.apprentice not in member.roles:
            return "apprentice"

        if self.fellow not in member.roles:
            return "fellow"

        return None

    def nominator_role(self, member: discord.Member):

        if self.mod in member.roles:
            return "moderator"

        if self.fellow in member.roles:
            return "fellow"

        if self.apprentice in member.roles:
            return "apprentice"

        return None

    async def stage_passed(self, member, stage):

        apprentices, fellows, mods = await self.db.get_stage_counts(
            member.id,
            stage
        )

        if stage == "boot":
            return mods >= 1 or fellows >= 1 or apprentices >= 2

        if stage == "apprentice":
            return mods >= 1 or fellows >= 2

        if stage == "fellow":
            return mods >= 2

        return False


    async def promote(self, member, stage):

        role = getattr(self, stage)

        await member.add_roles(role)

        await self.db.clear_stage(member.id, stage)

        try:
            await member.send(
                embed=info(
                    f"You have been promoted to **{role.name}**.\n\n",
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


    @app_commands.command(name="nominate")
    async def nominate(self, interaction: discord.Interaction, member: discord.Member):

        if interaction.user.id == member.id:
            await interaction.response.send_message(
                embed=failure("You cannot nominate yourself."),
                ephemeral=True
            )

        stage = self.determine_stage(member)

        if stage is None:
            await interaction.response.send_message(
                embed=failure(f"{member.mention} already has the highest role."),
                ephemeral=True
            )
            return

        if stage == "boot" and self.active not in member.roles:
            await interaction.response.send_message(
                embed=failure(
                    f"User must have {self.active.mention} role before they could be nominated."
                ),
                ephemeral=True
            )
            return

        role_used = self.nominator_role(interaction.user)

        if role_used is None:
            await interaction.response.send_message(
                embed=failure(f"You need to be an {self.apprentice.mention} or above to nominate."),
                ephemeral=True
            )
            return

        await interaction.response.defer()

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

            await self.promote(member, stage)

        else:

            apprentices, fellows, mods = await self.db.get_stage_counts(
                member.id,
                stage
            )

            progress = ""

            if stage == "boot":
                progress = f"Apprentice nominations: **{apprentices}/2**"
            elif stage == "apprentice":
                progress = f"Fellow nominations: **{fellows}/2**"
            elif stage == "fellow":
                progress = f"Moderator nominations: **{mods}/2**"

            try:
                await member.send(
                    embed=info(
                        f"You were nominated for **{stage.capitalize()}**.\n\n"
                        f"{progress}\n",
                        self.bot.user,
                        "You have received a message 📩",
                        f"Nominated by **{interaction.user}**."
                    )
                )
            except discord.Forbidden:
                pass

        await interaction.followup.send(
            embed=success(f"You have successfully nominated {member.mention}."),
            ephemeral=True
        )




async def setup(bot):
    await bot.add_cog(RoleProgression(bot))