
import discord
from discord.ext import commands
from discord import app_commands

from bot.constants import (
    accepting_team_invites_role_id, system_log_channel_id, success_emoji,
    teams_dashboard_message_id, join_a_team_channel_id
)
from bot.utils.embed_handler import success, failure, warning, info, authored_sm
from bot.utils.checks import tortoise_bot_developer_only



class CreateTeamModal(discord.ui.Modal, title="Create Team"):

    name = discord.ui.TextInput(label="Team Name", max_length=50)
    timezone = discord.ui.TextInput(label="Timezone (e.g. IST, EST)")
    description = discord.ui.TextInput(
        label="Description",
        placeholder="What does this team do? Goals, activities. \n\n"
                    "NOTE: This will be sent when you invite members",
        style=discord.TextStyle.paragraph,
        max_length=300
    )

    def __init__(self, cog, guild_id):
        super().__init__()
        self.cog = cog
        self.guild_id = guild_id

    async def on_submit(self, interaction: discord.Interaction):

        existing = await self.cog.team.get_user_team(self.guild_id, interaction.user.id)

        if existing:
            return await interaction.response.send_message(
                embed=warning("You are already in a team."),
            )

        await interaction.response.defer(thinking=True)

        guild = self.cog.bot.get_guild(self.guild_id)
        if not guild:
            return await interaction.followup.send(embed=failure("Guild not found."))

        name = self.name.value
        timezone = self.timezone.value
        description = self.description.value

        leader = guild.get_member(interaction.user.id)
        if not leader:
            return await interaction.followup.send(embed=failure("Member not found."))

        try:

            role = await guild.create_role(name=name)
            category = await guild.create_category(f"Team - {name}")

            overwrites = {
                guild.default_role: discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=False,
                    connect=False
                ),
                role: discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    connect=True
                )
            }

            text = await guild.create_text_channel(
                name="team-chat",
                category=category,
                overwrites=overwrites
            )

            voice = await guild.create_voice_channel(
                name="team-voice",
                category=category,
                overwrites=overwrites
            )


            team_id = await self.cog.team.create_team(
                guild.id,
                name,
                description,
                timezone,
                role.id,
                category.id,
                text.id,
                voice.id,
                leader.id
            )
            await self.cog.team.add_member(
                team_id,
                guild.id,
                leader.id
            )
            await leader.add_roles(role)

        except Exception as e:
            return await interaction.followup.send(
                embed=failure(f"Failed to create team.\n{e}")
            )

        await self.cog.log_channel.send(
            embed=info(
                f"**Leader:** {leader.mention}\n"
                f"**Timezone:** {timezone}\n"
                f"**Role:** {role.mention}\n"
                f"**Description:** {description}\n"
                f"**Created by:** {interaction.user.mention}\n",
                self.cog.bot.user, "Team Created!"
            )
        )

        await text.send(
            embed=info(f"**Lead: **{leader.mention}\n"
                       f"**Timezone:** {timezone}\n"
                       f"**Role:** {role.mention}\n\n"
                       f"{description}\n",
                       self.cog.bot.user,
                       f"{success_emoji} Team Setup Complete!")
        )

        await self.cog.update_dashboard(guild.id)
        
        await interaction.followup.send(
            embed=success("Team setup complete!")
        )
        return None


class TeamCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.team = bot.team_manager
        self.log_channel = None

    async def _handle_team_invite(self, interaction: discord.Interaction, custom_id: str):

        action, invite_id = custom_id.split(":")
        invite_id = int(invite_id)

        try:
            await interaction.message.edit(view=None)
        except discord.Forbidden:
            pass

        invite = await self.team.get_invite(invite_id)
        if not invite:
            return await interaction.response.send_message(
                embed=failure("Invite not found."),
                ephemeral=True
            )

        if invite["status"] != "pending":
            return await interaction.response.send_message(
                embed=failure("Invite already handled."),
                ephemeral=True
            )

        if interaction.user.id != invite["invitee_id"]:
            return await interaction.response.send_message(
                embed=failure("This invite is not for you."),
                ephemeral=True
            )

        guild = self.bot.get_guild(invite["guild_id"])
        if not guild:
            return await interaction.response.send_message(embed=failure("Guild not found."), ephemeral=True)

        member = guild.get_member(interaction.user.id)
        if not member:
            return await interaction.response.send_message(embed=failure("Member not found."), ephemeral=True)

        team = await self.team.get_team(invite["team_id"])
        if not team:
            return await interaction.response.send_message(embed=failure("Team not found."), ephemeral=True)

        await interaction.response.defer(ephemeral=True)

        role = guild.get_role(team["role_id"])
        if not role:
            return await interaction.followup.send(embed=failure("Team role not found."), ephemeral=True)

        team_channel = guild.get_channel(team["text_channel_id"])

        if action == "team_accept":
            await member.add_roles(role)
            await self.team.update_invite_status(invite_id, "accepted")

            await self.team.add_member(
                invite["team_id"],
                invite["guild_id"],
                interaction.user.id
            )

            await interaction.followup.send(embed=success("Invitation accepted."), ephemeral=True)
            if team_channel:
                await team_channel.send(
                    embed=authored_sm(f"{member} has joined the team.", author=member)
                )
            await self.log_channel.send(
                embed=authored_sm(f"{member} has joined team {team['name']}", author=member)
            )

        else:
            await self.team.update_invite_status(invite_id, "rejected")

            await interaction.followup.send(embed=warning("Invitation rejected."), ephemeral=True)
            if team_channel:
                await team_channel.send(
                    embed=authored_sm(f"{member} has rejected the invitation to join the team", author=member)
                )
            await self.log_channel.send(
                embed=authored_sm(
                    f"{member} rejected the invitation from team {team['name']}", author=member
                )
            )

        return None

    async def _handle_team_setup(self, interaction: discord.Interaction, custom_id: str):

        _, invite_id = custom_id.split(":")
        invite_id = int(invite_id)

        invite = await self.team.get_setup_invite(invite_id)

        if not invite:
            return await interaction.response.send_message(
                embed=failure("Invite not found."),
                ephemeral=True
            )

        if invite["status"] != "pending":
            return await interaction.response.send_message(
                embed=warning("Invite already used."),
                ephemeral=True
            )

        if interaction.user.id != invite["user_id"]:
            return await interaction.response.send_message(
                embed=failure("This invite is not for you."),
                ephemeral=True
            )

        guild = self.bot.get_guild(invite["guild_id"])
        if not guild:
            return await interaction.response.send_message(
                embed=failure("Guild not found."),
                ephemeral=True
            )

        await interaction.response.send_modal(
            CreateTeamModal(self, guild.id)
        )

        await self.team.update_setup_invite(invite_id, "used")

        try:
            await interaction.message.edit(view=None)
        except discord.Forbidden:
            pass

    @commands.Cog.listener()
    async def on_ready(self):
        self.log_channel = self.bot.get_channel(system_log_channel_id)

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):

        if not interaction.data:
            return

        custom_id = interaction.data.get("custom_id")
        if not custom_id:
            return

        if custom_id.startswith(("team_accept", "team_reject")):
            try:
                await self._handle_team_invite(interaction, custom_id)
            except Exception as e:
                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        embed=failure("Something went wrong."),
                        ephemeral=True
                    )
            return

        if custom_id.startswith("team_setup"):
            try:
                await self._handle_team_setup(interaction, custom_id)
            except Exception as e:
                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        embed=failure("Something went wrong."),
                        ephemeral=True
                    )
            return


    # @app_commands.command(name="create_team")
    # @app_commands.check(tortoise_bot_developer_only)
    # async def create_team(
    #         self,
    #         interaction: discord.Interaction,
    #         leader: discord.Member
    # ):
    #     if await self.team.leader_has_team(interaction.guild.id, leader.id):
    #         return await interaction.followup.send(
    #             embed=warning("This user is already leading a team."),
    #             ephemeral=True
    #         )
    #     await interaction.response.send_modal(
    #         CreateTeamModal(self, leader)
    #     )

    @app_commands.command(name="send_team_setup")
    @app_commands.check(tortoise_bot_developer_only)
    async def send_team_setup(self, interaction, member: discord.Member):

        existing = await self.team.get_user_team(interaction.guild.id, member.id)
        if existing:
            return await interaction.response.send_message(
                embed=warning("User is already in a team."),
                ephemeral=True
            )

        pending = await self.team.get_setup_invite_by_user(interaction.guild.id, member.id)
        if pending:
            return await interaction.response.send_message(
                embed=warning("User already has a pending setup invite."),
                ephemeral=True
            )

        await interaction.response.defer(thinking=True)

        try:

            msg = await member.send(
                embed=info(
                    "You have been invited to create a team.\n\n"
                    "Click below to begin setup.",
                    self.bot.user,
                    "Team Setup Invitation"
                )
            )
        except discord.Forbidden:
            return await interaction.followup.send(
                embed=failure("User has DMs disabled."),
                ephemeral=True
            )

        await self.team.create_setup_invite(
            msg.id,
            interaction.guild.id,
            member.id
        )

        view = discord.ui.View(timeout=None)

        view.add_item(discord.ui.Button(
            label="Start Setup",
            style=discord.ButtonStyle.green,
            custom_id=f"team_setup:{msg.id}"
        ))

        await msg.edit(view=view)

        await interaction.followup.send(
            embed=success("Setup invite sent."),
            ephemeral=True
        )

    @app_commands.command(name="delete_team")
    @app_commands.check(tortoise_bot_developer_only)
    async def delete_team(self, interaction, role: discord.Role):

        guild = interaction.guild
        team = await self.team.delete_team(guild.id, role.id)

        if not team:
            return await interaction.response.send_message(embed=failure("Team not found."), ephemeral=True)

        await interaction.response.defer(thinking=True)

        for cid in ["text_channel_id", "voice_channel_id", "category_id"]:
            ch = guild.get_channel(team[cid])
            if ch:
                await ch.delete()

        await role.delete()

        await self.log_channel.send(
            embed=info(f"Team **{team['name']}** was deleted by {interaction.user.mention}", self.bot.user, "")
        )
        await self.update_dashboard(guild.id)

        await interaction.followup.send(embed=success("Team deleted successfully."), ephemeral=True)


    @app_commands.command(name="invite")
    async def invite(self, interaction, member: discord.Member):

        if member.id == interaction.user.id:
            return await interaction.response.send_message(
                embed=warning("You cannot invite yourself."),
                ephemeral=True
            )

        guild = interaction.guild

        team = await self.team.get_team_by_leader(guild.id, interaction.user.id)

        if not team:
            return await interaction.response.send_message(embed=failure("You are not a team leader."), ephemeral=True)

        accept_role = guild.get_role(accepting_team_invites_role_id)
        if accept_role not in member.roles:
            return await interaction.response.send_message(
                embed=warning("User is not accepting invites. Ask them to turn on invitations."),
                ephemeral=True
            )

        team_role = guild.get_role(team["role_id"])
        if team_role and team_role in member.roles:
            return await interaction.response.send_message(
                embed=warning(
                    "User is already a team member.",
                )
            )


        await interaction.response.defer(thinking=True)

        existing = await self.team.get_user_team(guild.id, member.id)

        if existing:
            return await interaction.followup.send(
                embed=warning("User is already in a team."),
                ephemeral=True
            )

        if not await self.team.can_invite(team["team_id"], interaction.user.id):
            return await interaction.followup.send(
                embed=failure("Daily invite limit reached."),
                ephemeral=True
            )

        try:

            if await self.team.has_pending_invite_for_team(team["team_id"], member.id):
                return await interaction.followup.send(
                    embed=warning("You have already invited this person."),
                    ephemeral=True
                )

            msg = await member.send(
                embed=info(
                    f"You are invited to join team **{team['name']}**.\n\n"
                    f"**Lead:** `{interaction.user}`\n"
                    f"**Timezone:** `{team['timezone']}`\n\n"
                    f"{team['description']}\n",
                    self.bot.user,
                    "Team Invitation Received!",
                    "You may choose to accept or reject this invitation."
                )
            )

            await self.team.create_invite(
                msg.id,
                team["team_id"],
                interaction.user.id,
                member.id,
                interaction.guild.id,
            )

            view = discord.ui.View(timeout=None)

            view.add_item(discord.ui.Button(
                label="Accept",
                style=discord.ButtonStyle.green,
                custom_id=f"team_accept:{msg.id}"
            ))

            view.add_item(discord.ui.Button(
                label="Reject",
                style=discord.ButtonStyle.red,
                custom_id=f"team_reject:{msg.id}"
            ))

            await msg.edit(view=view)

            await self.log_channel.send(
                embed=info(
                    f"{interaction.user.mention} invited {member.mention} to join **{team['name']}**",
                    self.bot.user, ""
                )
            )
            await interaction.followup.send(embed=success("Invitation sent successfully."), ephemeral=True)
            return None

        except discord.Forbidden:
            return await interaction.followup.send(
                embed=failure("User DMs disabled."),
                ephemeral=True
            )

    async def _remove_member_core(
            self,
            guild: discord.Guild,
            team: dict,
            member: discord.Member,
            actor: discord.Member | None = None,
            reason: str = "removed"
    ):
        role = guild.get_role(team["role_id"])
        if not role:
            return False, "Team role not found."

        await self.team.remove_member(team["team_id"], member.id)

        await member.remove_roles(role)

        team_channel = guild.get_channel(team["text_channel_id"])

        if team_channel:
            message = f"{member} has been {reason} from the team {team['name']}."
            if reason != "removed":
                message = f"{member} has {reason} the team {team['name']}."
            await team_channel.send(
                embed=authored_sm(
                    message=message,
                    author=member
                )
            )

        try:
            if reason == "removed":
                await member.send(
                    embed=info(f"You have been {reason} from team **{team['name']}**.", self.bot.user,"")
                )
        except discord.Forbidden:
            pass

        if self.log_channel:
            if actor:
                msg = f"{actor.mention} {reason} {member.mention} from **{team['name']}**"
            else:
                msg = f"{member.mention} {reason} **{team['name']}**"

            await self.log_channel.send(
                embed=info(msg, self.bot.user, "")
            )

        return True, None

    @app_commands.command(name="remove_member")
    async def remove_member(self, interaction, member: discord.Member):

        guild = interaction.guild
        team = await self.team.get_team_by_leader(guild.id, interaction.user.id)

        if not team:
            return await interaction.response.send_message(
                embed=failure("Only leaders can remove members."),
                ephemeral=True
            )

        if member.id == interaction.user.id:
            return await interaction.response.send_message(
                embed=warning("You cannot remove yourself."),
                ephemeral=True
            )

        role = guild.get_role(team["role_id"])
        if not role or role not in member.roles:
            return await interaction.response.send_message(
                embed=warning("User not in team."),
                ephemeral=True
            )

        await interaction.response.defer(thinking=True)

        success_flag, err = await self._remove_member_core(
            guild, team, member,
            actor=interaction.user,
            reason="removed"
        )

        if not success_flag:
            return await interaction.followup.send(embed=failure(err))

        await interaction.followup.send(
            embed=success(f"{member.mention} removed from team.")
        )

    @app_commands.command(name="leave_team")
    async def leave_team(self, interaction: discord.Interaction):

        guild = interaction.guild

        record = await self.team.get_user_team(guild.id, interaction.user.id)
        if not record:
            return await interaction.response.send_message(
                embed=warning("You are not in a team."),
                ephemeral=True
            )

        team = await self.team.get_team(record["team_id"])
        if not team:
            return await interaction.response.send_message(
                embed=failure("Team not found."),
                ephemeral=True
            )

        if team["leader_id"] == interaction.user.id:
            return await interaction.response.send_message(
                embed=warning("Leader cannot leave the team."),
                ephemeral=True
            )

        await interaction.response.defer(thinking=True)

        success_flag, err = await self._remove_member_core(
            guild, team, interaction.user,
            actor=None,
            reason="left"
        )

        if not success_flag:
            return await interaction.followup.send(embed=failure(err))

        await interaction.followup.send(
            embed=success("You left the team.")
        )

    async def _build_team_embed(self, guild: discord.Guild):

        teams = await self.team.get_all_teams(guild.id)

        if not teams:
            return info("No teams created yet.", self.bot.user, "Teams Dashboard")

        desc = ""

        for team in teams:
            leader = guild.get_member(team["leader_id"])
            members = await self.team.get_team_members(team["team_id"])

            desc += (
                f"**{team['name']}**\n"
                f"Lead: {leader.mention if leader else 'Unknown'}\n"
                f"Timezone: `{team['timezone']}`\n"
                f"Members: {len(members)}\n\n"
            )

        return info(desc, self.bot.user, "Teams Dashboard", "powered by Tortoise Programming Community")

    async def update_dashboard(self, guild: discord.Guild):

        channel = self.bot.get_channel(join_a_team_channel_id)
        if not channel:
            return

        try:
            msg = await channel.fetch_message(teams_dashboard_message_id)
        except:
            return

        embed = await self._build_team_embed(guild)
        await msg.edit(embed=embed)

    @app_commands.command(name="update_team_dashboard")
    @app_commands.check(tortoise_bot_developer_only)
    async def update_team_dashboard(self, interaction: discord.Interaction):
        await self.update_dashboard(interaction.guild)
        await interaction.response.send_message(
            embed=success("Dashboard updated."),
            ephemeral=True
        )

async def setup(bot):
    await bot.add_cog(TeamCog(bot))