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
    if ctx.author.id in tortoise_developers:
        return True
    else:
        raise TortoiseBotDeveloperCheckFailure()


def check_if_tortoise_staff(ctx):
    """
    Check if member is tortoise staff.
    """
    if moderator_role in ctx.user.roles or admin_role in ctx.user.roles:
        return True
    else:
        raise TortoiseStaffCheckFailure()