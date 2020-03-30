from .exceptions import TortoiseGuildCheckFailure, TortoiseBotDeveloperCheckFailure


def check_if_it_is_tortoise_guild(ctx):
    """
    Works in DMs too - it will return False then.
    """
    if ctx.guild is None:
        return False
    elif ctx.guild.id != 577192344529404154:
        raise TortoiseGuildCheckFailure()
    else:
        return True


def tortoise_bot_developer_only(ctx):
    """
    Check for commands only usable by Tortoise bot developers..
    """
    tortoise_developers = (197918569894379520, 612349409736392928)
    if ctx.author.id in tortoise_developers:
        return True
    else:
        raise TortoiseBotDeveloperCheckFailure()
