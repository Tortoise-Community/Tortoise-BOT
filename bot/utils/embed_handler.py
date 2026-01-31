import datetime
from typing import Union

import discord
from asyncpraw import models

from discord import Embed, Color, Member, User, Status, Message, TextChannel

from bot import constants
from bot.utils.misc import (
    get_badges, get_join_pos, has_verified_role, format_activity, get_device_status, format_date, get_user_avatar
)


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
        f"[Events]({constants.events_url}) | "
        f"[Rules]({constants.rules_url})"
    )
    message = f"{message}\n\n{content_footer}"
    embed = simple_embed(message, title, color=Color.dark_green())
    embed.set_image(url=constants.line_img_url)
    return embed


def welcome(member: discord.Member, message: str = None) -> Embed:
    """
    Constructs welcome embed with fixed title 'Welcome' and green color.
    :param member: member object
    :param message: embed description (Optional)
    :return: Embed object
    """
    message = message or f"{member} has joined {member.guild.name}!"
    embed = simple_embed(message, "Member Joined", color=Color.dark_green())
    embed.set_footer(text=f"ID: {member.id}", icon_url=get_user_avatar(member))
    return embed


def goodbye(member: discord.Member, message: str = None) -> Embed:
    """
    Constructs goodbye embed with fixed title 'Goodbye' and red color.
    :param member: member object
    :param message: embed description (Optional)
    :return: Embed object
    """
    message = message or f"{member} has left {member.guild.name}."
    embed =  simple_embed(message, "Member Left", color=Color.dark_red())
    embed.set_footer(text=f"ID: {member.id}", icon_url=get_user_avatar(member))
    return embed

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
    embed.set_author(name=f"{author}", icon_url=author.avatar.url)
    return embed


async def reddit_embed(ctx, submission: models.Submission, color=0x3498d) -> Embed:
    """
    Embeds a reddit post
    :param ctx: The invocation context
    :param submission: The submission to embed
    :param color: the color of the embed
    :return: Embed object
    """

    if submission.over_18:
        return await nsfw_warning_embed(ctx.author)

    await submission.subreddit.load()
    await submission.author.load()

    subreddit = submission.subreddit.display_name
    upvote_emoji = ctx.bot.get_emoji(constants.upvote_emoji_id)
    embed = Embed(title=submission.title, url=submission.url, colour=color)

    embed.description = (
        f"{submission.selftext}\n"
        f"{upvote_emoji} {submission.score}​​ ​​ ​​​​ ​💬 {submission.num_comments}"
    )
    embed.set_image(url=submission.url)
    embed.set_author(name=f"r/{subreddit}", icon_url=submission.subreddit.icon_img)
    embed.set_footer(text=f"u/{submission.author.name}", icon_url=submission.author.icon_img)
    embed.timestamp = datetime.datetime.fromtimestamp(submission.created_utc)
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
    return simple_embed(f"{constants.success_emoji}︱{message}", "",
                        get_top_role_color(member, fallback_color=Color.green()))


def warning(message: str) -> Embed:
    """
    Constructs warning embed with fixed title 'Warning' and color gold.
    :param message: embed description
    :return: Embed object
    """
    return simple_embed(f":warning:︱{message}", "", Color.dark_gold())


def failure(message: str) -> Embed:
    """
    Constructs failure embed with fixed title 'Failure' and color red
    :param message: embed description
    :return: Embed object
    """
    return simple_embed(f"{constants.failure_emoji}︱{message}", "", Color.red())


def authored(message: str, *, author: Union[Member, User]) -> Embed:
    """
    Construct embed and sets its author to passed param author.
    Embed color is based on passed author top role color.
    :param author: to whom the embed will be authored.
    :param message: message to display in embed.
    :return: discord.Embed
    """
    embed = Embed(description=message, color=get_top_role_color(author, fallback_color=Color.green()))
    embed.set_author(name=author.name, icon_url=author.avatar.url)
    return embed


def authored_sm(message: str, *, author: Union[Member, User]) -> Embed:
    """
    Construct small authored embed and sets its author to passed param author.
    Embed color is based on passed author top role color.
    :param author: to whom the embed will be authored.
    :param message: message to display in embed.
    :return: discord.Embed
    """
    embed = Embed(description="", color=get_top_role_color(author, fallback_color=Color.green()))
    embed.set_footer(text=message, icon_url=author.avatar.url)
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
    embed.set_thumbnail(url=str(member.avatar.url))
    return embed


def status_embed(ctx, member: Member) -> Embed:
    """
    Construct status embed for certain member.
    Status will have info such as member device, online status, activity, roles etc.
    :param ctx: context variable to get the member
    :param member: member to get data from
    :return: discord.Embed
    """

    color_dict = {
        Status.online: Color.green(),
        Status.offline: 0x000000,
        Status.idle: Color.orange(),
        Status.dnd: Color.red()
    }

    embed = Embed(title=str(member), color=color_dict[member.status])
    embed.description = get_badges(member)
    embed.set_thumbnail(url=member.avatar.url)

    bot = constants.tick_no
    nick = member.nick
    verified = constants.tick_no
    join_pos = get_join_pos(ctx, member)
    activities = ""

    if member.bot:
        bot = constants.tick_yes

    if has_verified_role(ctx, member):
        verified = constants.tick_yes

    if not nick:
        nick = constants.tick_no

    for activity in member.activities:

        clean_activity = format_activity(activity)
        activities += f"{clean_activity}\n"

    embed.add_field(name=f"{constants.pin_emoji} General info",
                    value=f"**Nick** : {nick}\n**Bot** : {bot}\n"
                          f"**Verified** : {verified}\n**Join position** : {join_pos}")
    embed.add_field(name=f"{constants.user_emoji} Status", value=get_device_status(member), inline=False)
    embed.add_field(name="📆 Dates",
                    value=f"**Join date** : {format_date(member.joined_at)}\n "
                          f"**Creation Date** : {format_date(member.created_at)}",
                    inline=False)

    if not activities == "":
        embed.add_field(name='Activities', value=activities, inline=False)
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
    embed.set_author(name="Tortoise Community", icon_url=ctx.me.avatar.url)

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


def suggestion_embed(author: User, suggestion: str, status: constants.SuggestionStatus) -> Embed:
    """
    Creates suggestion embed message with author thumbnail and suggestion status.
    :param author: Discord User from which to get name and avatar
    :param suggestion: str actual suggestion text
    :param status: constants.SuggestionStatus status for suggestion
    :return: discord.Embed
    """
    embed = Embed(
        title=f"{author}'s suggestion",
        description=suggestion,
        color=Color.gold()
    )
    embed.set_thumbnail(url=str(author.avatar.url))
    embed.add_field(name="Status", value=status.value)
    embed.set_footer(text=f"UID: {author.id} ◆ Powered by Tortoise Community.")
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


def black_jack_template(author: User, player, description: str, color: Color) -> Embed:
    """
    Creates black jack embed template.
    :param author: User discord user from which to get name and avatar
    :param player: player object
    :param description: embed description
    :param color: discord.Color
    :return: discord.Embed
    """
    embed = authored(description, author=author)
    embed.colour = color
    embed.set_thumbnail(
        url="https://www.vhv.rs/dpng/d/541-5416003_poker-club-icon-splash-diwali-coasters-black-background.png"
    )
    card_string = player.get_emote_string(hidden=False)
    embed.add_field(name="Your hand", value=f"{card_string}")
    embed.set_footer(
        text="BlackJack",
        icon_url="https://i.pinimg.com/originals/c3/5f/63/c35f630a4efb237206ec94f8950dcad5.png"
    )
    return embed


def black_jack_embed(user: User, player, outcome: str = None, hidden: bool = True) -> Embed:
    """
    Creates embed based on set of constraints for blackjack
    :param user:  discord.User
    :param player: player object for blackjack
    :param outcome: blackjack game outcome
    :param hidden: dealer card value
    :return: discord.Embed
    """
    embed = black_jack_template(user, player, "", Color.gold())
    embed.add_field(name="Dealer hand", value=player.game.dealer.get_emote_string(hidden=hidden))
    if outcome == "win":
        embed.colour = Color.dark_green()
        embed.description = "**Outcome:** You won!"
    elif outcome == "lose":
        embed.colour = Color.dark_red()
        embed.description = "**Outcome:** You lost!"
    elif outcome == "tie":
        embed.colour = Color.dark_grey()
        embed.description = "**Outcome:** It's a tie!"
    return embed


def project_embed(projects: dict, me):
    desc = f"▰▱▰▱▰▱▰▱▰▱▰▱▰▱▰▱▰▱\n\n**Active repositories: **{len(projects)-1}\n"
    embed = simple_embed(title="Tortoise Community", message=desc,
                         color=get_top_role_color(member=me, fallback_color=Color.light_grey()))
    embed.set_thumbnail(url=me.avatar.url)
    embed.set_author(name="Github Stats",
                     icon_url="https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png")
    embed.set_footer(text="Last updated: ")
    embed.timestamp = projects["last_updated"]
    for item in projects:
        if item == "last_updated":
            continue
        project = projects[item]
        embed.add_field(name=f"\n{constants.embed_space}\n{constants.git_repo_emoji} {project.name}",
                        value=f"• [repository]({project.link})\n"
                              f"• [web]({project.web_url})\n"
                              f"• [issues]({project.link+'/issues'})",
                        inline=False)
        embed.add_field(name="Commits", value=f"{constants.git_commit_emoji} {project.commits}")
        embed.add_field(name="Stars", value=f"{constants.git_start_emoji} {project.stars}")
        embed.add_field(name="Forks", value=f"{constants.git_fork_emoji} {project.forks}")

    return embed

def moderation_log_embed(
    *,
    title: str,
    channel: str,
    content: str,
    color: Color
) -> Embed:
    embed = Embed(title=title, color=color)
    embed.add_field(name="Channel", value=channel, inline=False)
    embed.add_field(name="Content", value=content[:1024], inline=False)
    return embed

def code_eval_embed(language: str, output: str, *, edited: bool = False) -> Embed:
    title = "Execution Result (edited)" if edited else "Execution Result"
    color = Color.orange() if edited else Color.blurple()

    if not output:
        output = "(no output)"

    if len(output) > 1900:
        output = output[:1900] + "\n... (truncated)"

    embed = Embed(title=title, color=color)
    embed.add_field(name="Language", value=language, inline=True)
    embed.add_field(name="Output", value=f"```{output}```", inline=False)
    embed.set_footer(text="Powered by EMKC Piston")
    return embed
