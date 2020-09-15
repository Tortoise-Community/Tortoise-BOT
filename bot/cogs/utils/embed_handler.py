import datetime
from typing import Union
from asyncio import TimeoutError

import discord
from discord.errors import NotFound
from discord.ext.commands import Bot
from discord import Embed, Color, Member, User, Status, Message, RawReactionActionEvent, TextChannel

from bot import constants
from bot.cogs.utils.members import get_member_status, get_member_roles_as_mentions, get_member_activity
# from bot.cogs.utils.gambling_backend import Pl


def simple_embed(message: str, title: str, color: Color) -> Embed:
    embed = Embed(title=title, description=message, color=color)
    return embed


def footer_embed(message: str, title) -> Embed:
    """
    Constructs embed with fixed  green color and fixed footer showing website, privacy url and rules url.
    :param message: embed description
    :param title: title of embed
    :return: Embed object
    """
    content_footer = (
        f"Links: [Website]({constants.website_url}) | "
        f"[Privacy statement]({constants.privacy_url}) | "
        f"[Rules]({constants.rules_url})"
    )
    message = f"{message}\n\n{content_footer}"
    embed = simple_embed(message, title, color=Color.dark_green())
    embed.set_image(url=constants.line_img_url)
    return embed


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


async def nsfw_warning_embed(author: Member, additional_msg: str = "") -> Embed:
    """
    Constructs a warning embed if a nsfw post is invoked.
    :param author: Member who tried to use nsfw.
    :param additional_msg: The additional message to add
    :return: Embed object
    """

    embed = Embed(
        title="⚠️Warning",
        description=f"**NSFW** posts are not allowed inside the tortoise community\n{additional_msg}",
        colour=Color.red()
    )
    embed.set_author(name=f"{author}", icon_url=author.avatar_url)
    return embed


async def reddit_embed(ctx, post, color=0x3498d) -> Embed:
    """
    Embeds a reddit post
    :param ctx: The invocation context
    :param post: The post to embed
    :param color: the color of the embed
    :return: Embed object
    """

    if post.over_18:
        return await nsfw_warning_embed(ctx.author)

    subreddit = post.subreddit.display_name
    upvote_emoji = ctx.bot.get_emoji(constants.upvote_emoji_id)
    embed = Embed(title=post.title, url=post.url, colour=color)

    embed.description = (
        f"{post.selftext}\n"
        f"{upvote_emoji} {post.score}​​ ​​ ​​​​ ​💬 {len(post.comments)}"
    )
    embed.set_image(url=post.url)
    embed.set_author(name=f"r/{subreddit}", icon_url=post.subreddit.icon_img)
    embed.set_footer(text=f"u/{post.author.name}", icon_url=post.author.icon_img)
    embed.timestamp = datetime.datetime.fromtimestamp(post.created_utc)
    return embed


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


def status_embed(member: Member, *, description: str = "") -> Embed:
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
        embed.add_field(name="**DEVICE**", value=":no_entry:")
    elif member.is_on_mobile():
        embed.add_field(name="**DEVICE**", value="Phone: :iphone:")
    else:
        embed.add_field(name="**DEVICE**", value="PC: :desktop:")

    embed.add_field(name="**Status**", value=get_member_status(member=member), inline=False)
    embed.add_field(name="**Joined server at**", value=member.joined_at, inline=False)
    embed.add_field(name="**Roles**", value=get_member_roles_as_mentions(member), inline=False)
    embed.add_field(name="**Activity**", value=get_member_activity(member=member), inline=False)
    embed.set_thumbnail(url=member.avatar_url)

    return embed


def infraction_embed(
        ctx,
        infracted_member: Union[Member, User],
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


class RemovableMessage:
    emoji_remove = "❌"

    @classmethod
    async def create_instance(cls, bot: Bot,  message: Message, action_member: Member, *, timeout: int = 120):
        self = RemovableMessage()

        self.bot = bot
        self.message = message
        self.action_member = action_member
        self.timeout = timeout

        await self.message.add_reaction(cls.emoji_remove)
        await self._listen()

    def __init__(self):
        self.bot = None
        self.message = None
        self.action_member = None
        self.timeout = None

    def _check(self, payload: RawReactionActionEvent):
        return (
            str(payload.emoji) == self.emoji_remove and
            payload.message_id == self.message.id and
            payload.user_id == self.action_member.id and
            payload.user_id != self.bot.user.id
        )

    async def _listen(self):
        try:
            await self.bot.wait_for("raw_reaction_add", check=self._check, timeout=self.timeout)
            await self.message.delete()
        except TimeoutError:
            try:
                await self.message.remove_reaction(self.emoji_remove, self.bot.user)
            except NotFound:
                pass  # If the message got deleted by user in the meantime


def suggestion_embed(author: User, suggestion: str, status: constants.SuggestionStatus) -> Embed:
    """
    Creates suggestion embed message with author thumbnail and suggestion status.
    :param author: User discord user from which to get name and avatar
    :param suggestion: str actual suggestion text
    :param status: constants.SuggestionStatus status for suggestion
    :return: discord.Embed
    """
    embed = Embed(
        title=f"{author}'s suggestion",
        description=suggestion,
        color=Color.gold()
    )
    embed.set_thumbnail(url=str(author.avatar_url))
    embed.add_field(name="Status", value=status.value)
    embed.set_footer(text="Powered by Tortoise Community.")
    return embed


async def create_suggestion_msg(channel: TextChannel, author: User, suggestion: str) -> Message:
    """
    Creates suggestion embed with up-vote and down-vote reactions.
    :param channel: TextChannel channel where to sent created suggestion embed
    :param author: User discord user from which to get name and avatar
    :param suggestion: str actual suggestion text
    :return: discord.Message
    """
    thumbs_up_reaction = "\U0001F44D"
    thumbs_down_reaction = "\U0001F44E"

    embed = suggestion_embed(author, suggestion, constants.SuggestionStatus.under_review)

    suggestion_msg = await channel.send(embed=embed)
    await suggestion_msg.add_reaction(thumbs_up_reaction)
    await suggestion_msg.add_reaction(thumbs_down_reaction)

    return suggestion_msg


def bj_template_embed(author: User, player, description: str, color: discord.Color):
    embed = authored(description, author=author)
    embed.colour = color
    embed.set_thumbnail(url="https://www.vhv.rs/dpng/d/541-5416003_poker-club-ic"
                            "on-splash-diwali-coasters-black-background.png")
    card_string = player.get_emote_string(hidden=False)
    embed.add_field(name="Your hand", value=f"{card_string}")
    embed.set_footer(text="BlackJack",
                     icon_url="https://i.pinimg.com/originals/c3/5f/63/c35f630a4efb237206ec94f8950dcad5.png")
    return embed


def black_jack_embed(user: discord.User, player, outcome=None, hidden=True):
    embed = bj_template_embed(user, player, f"**Your bet: **{player.bet_amount}", discord.Color.gold())
    embed.add_field(name="Dealer hand", value=player.game.get_emote_string(hidden=hidden))
    # if outcome is None:
    #     embed.colour = discord.Color.gold()
    if outcome == "win":
        embed.colour = discord.Color.dark_green()
    elif outcome == "lose":
        embed.colour = discord.Color.dark_red()
        embed.title = "lost!"
    elif outcome == "tie":
        embed.colour = discord.Color.dark_grey()
    return embed
