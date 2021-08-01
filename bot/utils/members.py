from typing import Union

import discord


def get_member_status(member: discord.Member) -> str:

    if member.status == discord.Status.dnd:
        return "DND"
    elif member.status == discord.Status.online:
        return f"ONLINE"
    elif member.status == discord.Status.idle:
        return "IDLE"
    elif member.status == discord.Status.offline:
        return "OFFLINE"
    else:
        return "UNKNOWN"


def get_member_roles_as_mentions(member: discord.Member) -> str:
    role_mentions = [role.mention for role in member.roles]
    return " ".join(role_mentions)


def get_member_activity(member: discord.Member) -> Union[None, str]:
    if member.activity is None:
        return None
    elif member.activity.type != discord.ActivityType.custom:
        return f"{member.activity.type.name} {member.activity.name}"
    else:
        return member.activity.name
