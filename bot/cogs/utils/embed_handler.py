from typing import Union

from discord import Embed, Color, Member, User, Status

from bot import constants
from bot.cogs.utils.members import get_member_status, get_member_roles_as_mentions, get_member_activity


def simple_embed(message: str, title: str, color: Color) -> Embed:
    embed = Embed(title=title, description=message, color=color)
    return embed


def welcome_dm(message: str) -> Embed:
    """
    Constructs welcome embed to be sent when user joins,
    with fixed  green color and fixed footer showing privacy url and rules url.
    :param message: embed description
    :return: Embed object
    """
    content_footer = (f"Links: [Website]({constants.website_url}) | "
                      f"[Privacy statement]({constants.privacy_url}) | "
                      f"[Rules]({constants.rules_url})")
    message = f"{message}\n\n{content_footer}"
    welcome_dm_embed = simple_embed(message, "Welcome", color=Color.dark_green())
    welcome_dm_embed.set_image(url=constants.line_img_url)
    return welcome_dm_embed


def welcome(message: str) -> Embed:
    """
    Constructs welcome embed with fixed title 'Welcome' and green color.
    :param message: embed description
    :return: Embed object
    """
    return simple_embed(message, "Welcome!", color=Color.dark_green())


def goodbye(message: str) -> Embed:
    """
    Constructs goodbye embed with fixed title 'Goodbye' and red color.
    :param message: embed description
    :return: Embed object
    """
    return simple_embed(message, "Goodbye", color=Color.dark_red())


def info(message: str, member: Union[Member, User], title: str = "Info") -> Embed:
    """
    Constructs success embed with custom title and description.
    Color depends on passed member top role color.
    :param message: embed description
    :param member: member object to get the color of it's top role from
    :param title: title of embed, defaults to "Info"
    :return: Embed object
    """
    return Embed(title=title, description=message, color=get_top_role_color(member, fallback_color=Color.green()))


def success(message: str, member: Union[Member, User] = None) -> Embed:
    """
    Constructs success embed with fixed title 'Success' and color depending
    on passed member top role color.
    If member is not passed or if it's a User (DMs) green color will be used.
    :param message: embed description
    :param member: member object to get the color of it's top role from,
                   usually our bot member object from the specific guild.
    :return: Embed object
    """
    return simple_embed(message, "Success", get_top_role_color(member, fallback_color=Color.green()))


def warning(message: str) -> Embed:
    """
    Constructs warning embed with fixed title 'Warning' and color gold.
    :param message: embed description
    :return: Embed object
    """
    return simple_embed(message, "Warning", Color.dark_gold())


def failure(message: str) -> Embed:
    """
    Constructs failure embed with fixed title 'Failure' and color red
    :param message: embed description
    :return: Embed object
    """
    return simple_embed(message, "Failure", Color.red())


def authored(message: str, *, author: Union[Member, User]) -> Embed:
    """
    Construct embed and sets its author to passed param author.
    Embed color is based on passed author top role color.
    :param author: to whom the embed will be authored.
    :param message: message to display in embed.
    :return: discord.Embed
    """
    embed = Embed(description=message, color=get_top_role_color(author, fallback_color=Color.green()))
    embed.set_author(name=author.name, icon_url=author.avatar_url)
    return embed


def thumbnail(message: str, member: Union[Member, User], title: str = None) -> Embed:
    """
    Construct embed and sets thumbnail based on passed param member avatar image..
    Embed color is based on passed author top role color.
    :param message: message to display in embed.
    :param member: member from which to get thumbnail from
    :param title: str title of embed
    :return: discord.Embed
    """
    embed = Embed(title=title, description=message, color=get_top_role_color(member, fallback_color=Color.green()))
    embed.set_thumbnail(url=str(member.avatar_url))
    return embed


def status_embed(member, *, description="") -> Embed:
    """
    Construct status embed for certain member.
    Status will have info such as member device, online status, activity, roles etc.
    :param member: member to get data from
    :param description: optional, description to use as embed description
    :return: discord.Embed
    """
    embed = Embed(
        title=member.display_name,
        description=description,
        color=get_top_role_color(member, fallback_color=Color.green())
    )

    if member.status == Status.offline:
        embed.add_field(name="DEVICE", value=":no_entry:")
    elif member.is_on_mobile():
        embed.add_field(name="**DEVICE**", value="Phone: :iphone:")
    else:
        embed.add_field(name="**DEVICE**", value="PC: :desktop:")

    embed.add_field(name="**Status**", value=get_member_status(member=member), inline=False)
    embed.add_field(name="**Joined server at**", value=member.joined_at, inline=False)
    embed.add_field(name="**Roles**", value=get_member_roles_as_mentions(member.roles), inline=False)
    embed.add_field(name="**Activity**", value=get_member_activity(member=member), inline=False)
    embed.set_thumbnail(url=member.avatar_url)
    return embed


def infraction_embed(
        ctx,
        infracted_member,
        infraction_type: constants.Infraction,
        reason: str
) -> Embed:
    """
    :param ctx: context to get mod member from (the one who issued this infraction) and
                bot so we can get it's image.
    :param infracted_member: member who got the infraction
    :param infraction_type: infraction type
    :param reason: str reason for infraction
    :return: discord Embed
    """

    embed = Embed(title="**Infraction information**", color=infraction_type.value)
    embed.set_author(name="Tortoise Community", icon_url=ctx.me.avatar_url)

    embed.add_field(name="**Member**", value=f"{infracted_member}", inline=False)
    embed.add_field(name="**Type**", value=infraction_type.name, inline=False)
    embed.add_field(name="**Reason**", value=reason, inline=False)
    return embed


def get_top_role_color(member: Union[Member, User], *, fallback_color) -> Color:
    """
    Tries to get member top role color and if fails returns fallback_color - This makes it work in DMs.
    Also if the top role has default role color then returns fallback_color.
    :param member: Member to get top role color from. If it's a User then default discord color will be returned.
    :param fallback_color: Color to use if the top role of param member is default color or if param member is
                           discord.User (DMs)
    :return: discord.Color
    """
    try:
        color = member.top_role.color
    except AttributeError:
        # Fix for DMs
        return fallback_color

    if color == Color.default():
        return fallback_color
    else:
        return color
