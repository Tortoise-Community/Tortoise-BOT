from typing import Union
from discord import Embed, Colour, Member, User


def simple_embed(message: str, title: str, color: Colour) -> Embed:
    embed = Embed(title=title, description=message, color=color)
    return embed


def info(message: str, member: Union[Member, User], title: str = Embed.Empty) -> Embed:
    """
    Constructs success embed with custom title and description.
    Color depends on passed member top role color.
    :param message: embed description
    :param member: member object to get the color of it's top role from
    :param title: title of embed
    :return: Embed object

    """
    embed = Embed(title=title, description=message, color=get_top_role_color(member))
    return embed


def success(message: str, member: Union[Member, User]) -> Embed:
    """
    Constructs success embed with fixed title:Success and color depending
    on passed member top role color.
    This will be used quite common so no sense to hard-code green colour since
    we want most of the messages the bot sends to be the color of it's top role.
    :param message: embed description
    :param member: member object to get the color of it's top role from,
                   usually our bot member object from the specific guild.
    :return: Embed object

    """
    return simple_embed(message, "Success", get_top_role_color(member))


def warning(message: str) -> Embed:
    """
    Constructs warning embed with fixed title:Warning and color:gold
    :param message: embed description
    :return: Embed object

    """
    return simple_embed(message, "Warning", Colour.dark_gold())


def failure(message: str) -> Embed:
    """
    Constructs failure embed with fixed title:Failure and color:red
    :param message: embed description
    :return: Embed object

    """
    return simple_embed(message, "Failure", Colour.red())


def get_top_role_color(member: Union[Member, User]):
    """
    Tries to get member top role color and if fails return Embed.Empty - This makes it work in DMs.
    If the top role has default role color then returns green color (marking success)

    """
    try:
        color = member.top_role.color
        if color == Colour.default():
            return Colour.green()
        else:
            return member.top_role.color
    except AttributeError:
        # Fix for DMs
        return Embed.Empty
