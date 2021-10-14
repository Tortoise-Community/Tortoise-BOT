from discord import Invite, Member
from discord.ext import commands

from bot.utils import invite_help, embed_handler
from bot.constants import tortoise_guild_id, successful_verifications_channel_id


class InviteTracker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.tracker = invite_help.GuildInviteTracker(self.bot.get_guild(tortoise_guild_id))
        self.log_channel = self.bot.get_channel(successful_verifications_channel_id)
        self.bot.loop.create_task(self.tracker.refresh_invite_cache())

    @commands.Cog.listener()
    async def on_invite_create(self, invite: Invite):
        await self.tracker.add_new_invite(invite)

    @commands.Cog.listener()
    async def on_invite_delete(self, invite: Invite):
        await self.tracker.remove_invite(invite)

    @commands.Cog.listener()
    async def on_member_join(self, member: Member):
        inviter = await self.tracker.track_invite()
        if inviter:
            await self.log_channel.send(embed=embed_handler.info(
                f"New member {member} was invited by {inviter}",
                member=member,
                title=""
            ))


def setup(bot):
    bot.add_cog(InviteTracker(bot))
