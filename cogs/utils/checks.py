from .exceptions import TortoiseGuildCheckFailure


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
