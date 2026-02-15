import discord

from bot.constants import tortoise_developers, tortoise_guild_id, moderator_role, admin_role
from bot.utils.exceptions import TortoiseGuildCheckFailure, TortoiseBotDeveloperCheckFailure, TortoiseStaffCheckFailure


def check_if_it_is_tortoise_guild(ctx):
    """
    Works in DMs too - it will return False then.
    """
    if ctx.guild is None:
        return False
    elif ctx.guild.id != tortoise_guild_id:
        raise TortoiseGuildCheckFailure()
    else:
        return True


def tortoise_bot_developer_only(ctx):
    """
    Check for commands only usable by Tortoise bot developers.
    """
    if ctx.user.id in tortoise_developers:
        return True
    else:
        raise TortoiseBotDeveloperCheckFailure()


async def check_if_tortoise_staff(interaction: discord.Interaction):
    """
    Check if member is tortoise staff.
    """
    if not isinstance(interaction.user, discord.Member):
        raise TortoiseStaffCheckFailure()

    member = interaction.user
    role_ids = [role.id for role in member.roles]

    if moderator_role in member.roles or admin_role in role_ids:
        return True

    raise TortoiseStaffCheckFailure()
