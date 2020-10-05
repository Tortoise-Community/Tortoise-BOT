import logging
import datetime

from discord import Member, Activity, Game, Spotify, CustomActivity, Status

from bot import constants


logger = logging.getLogger(__name__)


def get_badges(member: Member) -> str:
    """
    Convenience function that fetches all the badges a member has
    :param member: Member to fetch the badges from
    :return: str emotes of badges
    """
    badge_dict = {
        'staff': constants.staff,
        'partner': constants.partner,
        'hypesquad': constants.hs_ev,
        'bug_hunter': constants.bg_1,
        'hypesquad_bravery': constants.hs_brav,
        'hypesquad_brilliance': constants.hs_bril,
        'hypesquad_balance': constants.hs_bal,
        'early_supporter': constants.ear_supp,
        'bug_hunter_level_2': constants.bg_2,
        'verified_bot_developer': constants.verified_bot_dev

    }

    badges = ""

    for flag in member.public_flags:
        if flag[1]:
            try:
                badges += badge_dict[flag[0]]
            except Exception as e:
                logger.critical(e)

    if member.is_avatar_animated():
        badges += constants.nitro

    return badges


def get_join_pos(ctx, member: Member) -> int:
    """
    Convenience function to get the join position of a member
    :param ctx: The invocation context
    :param member: The member
    :return: int position of a member
    """
    join_pos = 1
    for member_ in ctx.guild.members:
        if member_.joined_at < member.joined_at:
            join_pos += 1
    return join_pos


def has_verified_role(ctx, member: Member) -> bool:
    """
    Convenience function to check if a member has the verified role
    :param ctx: The invocation context
    :param member: The member
    :return: Bool which depends on whether the member has the verified role
    """
    role = ctx.guild.get_role(599647985198039050)
    return role in member.roles


def format_activity(activity) -> str:
    """
    Convenience function to format an activity
    :param activity: The activity
    :return: str of formatted activity
    """

    if isinstance(activity, Activity) or isinstance(activity, Game):
        return f"🎮 Playing **{activity.name}**"

    elif isinstance(activity, Spotify):
        music_name = activity.title
        artists = ""

        for artist in activity.artists:
            artists += f"{artist}, "

        return f"{constants.spotify_emoji} Listening to **{music_name}** - {artists}"

    elif isinstance(activity, CustomActivity):
        title = activity.name
        emoji = activity.emoji

        if emoji:
            return f"{emoji} {title}"
        else:
            return f"⚫ {title}"


def get_device_status(member: Member):
    """
    Convenience function to get the status of member on all discord clients
    :param member: The member to get the status from
    :return: str containing all the status
    """
    stat_dict = {
        Status.online: constants.online,
        Status.idle: constants.idle,
        Status.offline: constants.offline,
        Status.dnd: constants.dnd
    }

    mobile_status = stat_dict[member.mobile_status]
    web_status = stat_dict[member.web_status]
    pc_status = stat_dict[member.desktop_status]

    return f"{mobile_status} **Mobile Client**\n{web_status} **Web Client**\n{pc_status} **Desktop Client**"


def format_date(date: datetime.datetime) -> str:
    """
    Convenience function to format a date
    :param date: The date to format
    :return: str of formatted date
    """
    today = datetime.date.today()
    days = date.date() - today
    year = int(days.days / 365)

    if year == 0:
        return f"{date.day} {date.strftime('%B')},{date.year}"

    return f"{date.day} {date.strftime('%B')}, {date.year}"
