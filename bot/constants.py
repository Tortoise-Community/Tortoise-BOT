from aenum import Enum, NoAlias

from discord import Color

tortoise_guild_id = 577192344529404154
website_url = "https://www.tortoisecommunity.com/"
privacy_url = "https://www.tortoisecommunity.com/pages/privacy"
rules_url = "https://www.tortoisecommunity.com/pages/rules"
verification_url = "https://www.tortoisecommunity.com/verification/"
github_repo_link = "https://github.com/Tortoise-Community/Tortoise-BOT"
tortoise_paste_service_link = "https://paste.tortoisecommunity.com/"
line_img_url = "https://cdn.discordapp.com/attachments/649868379372388352/723173852796158062/animated-line.gif"


# Channel IDs
welcome_channel_id = 738731842538176522
announcements_channel_id = 578197131526144024
react_for_roles_channel_id = 603651772950773761

mod_mail_report_channel_id = 693790120712601610
bug_reports_channel_id = 693790120712601610
code_submissions_channel_id = 610079185569841153
suggestions_channel_id = 708734512296624239

# Log Channel IDs
system_log_channel_id = 593883395436838942
deterrence_log_channel_id = 597119801701433357
bot_log_channel_id = 693090079329091615
successful_verifications_channel_id = 581139962611892229
verification_channel_id = 602156675863937024
website_log_channel_id = 649868379372388352
bot_dev_channel_id = 692851221223964822
error_log_channel_id = 690650346665803777
member_count_channel = 723526255495872566

# Roles
muted_role_id = 707007421066772530
verified_role_id = 599647985198039050
unverified_role_id = 605808609195982864
trusted_role_id = 703657957438652476
moderator_role = 577368219875278849
admin_role = 577196762691928065

# Keys are IDs of reaction emojis
# Values are role IDs which will get added if that reaction gets added/removed
self_assignable_roles = {
    582547250635603988: 589128905290547217,     # Python
    603276263414562836: 589129320480636986,     # Javascript
    723277556459241573: 591254311162347561,     # HTML/CSS
    723274176991068261: 589131126619111424,     # SQL
    603275563972689942: 589131022520811523,     # C
    603275529587654665: 589129873809735700,     # C++
    723280469122089131: 589130125208190991,     # C#
    723272019126255726: 589129070609039454,     # Java
    723276957810163731: 589129583375286415,     # R
    610825682070798359: 610834658267103262,     # events
    583614910215356416: 603157798225838101      # announcements
}


# Emoji IDs
mod_mail_emoji_id = 706195614857297970
event_emoji_id = 611403448750964746
bug_emoji_id = 723274927968354364
suggestions_emoji_id = 613185393776656384
verified_emoji_id = 610713784268357632
upvote_emoji_id = 741202481090002994
hit_emoji_id = 753975475910475926
stay_emoji_id = 753975899111555133
double_emoji_id = 753975477319893033
default_blank_emoji = "<:cardboard_box:754085498384810065>"


# Music Options
# For all options see:
# https://github.com/ytdl-org/youtube-dl/blob/3e4cedf9e8cd3157df2457df7274d0c842421945/youtube_dl/YoutubeDL.py#L137-L312
ytdl_format_options = {
    "format": "bestaudio/best",
    "outtmpl": "downloads/%(extractor)s-%(id)s-%(title)s.%(ext)s",
    "restrictfilenames": True,
    "noplaylist": True,
    "nocheckcertificate": True,
    "ignoreerrors": False,
    "logtostderr": False,
    "quiet": True,
    "no_warnings": True,
    "default_search": "auto",
    "source_address": "0.0.0.0"  # ipv6 addresses cause issues sometimes
}

ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn',
}

# Special
tortoise_developers = (197918569894379520, 612349409736392928)

# Embeds are not monospaced so we need to use spaces to make different lines "align"
# But discord doesn't like spaces and strips them down.
# Using a combination of zero width space + regular space solves stripping problem.
embed_space = "\u200b "

# After this is exceeded the link to tortoise paste service should be sent
max_message_length = 1000


class Infraction(Enum):
    _settings_ = NoAlias

    warning = Color.gold()
    kick = Color.gold()
    ban = Color.red()


class SuggestionStatus(Enum):
    under_review = "Under Review"
    denied = "Denied"
    approved = "Approved"


blackjack_player_limit = 4

black_emotes = {

    "A": "<:bA:623575870375985162>",
    "2": "<:b2:623564440574623774>",
    "3": "<:b3:623564440545263626>",
    "4": "<:b4:623564440624824320>",
    "5": "<:b5:623564440851316760>",
    "6": "<:b6:623564440679350319>",
    "7": "<:b7:623564440754978843>",
    "8": "<:b8:623564440826150912>",
    "9": "<:b9:623564440868225025>",
    "10": "<:b10:623564440620630057>",
    "K": "<:bK:623564440880807956>",
    "Q": "<:bQ:623564440851185679>",
    "J": "<:bJ:623564440951980084>"
}

red_emotes = {

    "A": "<:rA:623575868672835584>",
    "2": "<:r2:623564440989859851>",
    "3": "<:r3:623564440880545798>",
    "4": "<:r4:623564441103106058>",
    "5": "<:r5:623564440868225035>",
    "6": "<:r6:623564440759173121>",
    "7": "<:r7:623564440964694036>",
    "8": "<:r8:623564440901779496>",
    "9": "<:r9:623564440897454081>",
    "10": "<:r10:623564440863899663>",
    "K": "<:rK:623564441073614848>",
    "Q": "<:rQ:623564440880807936>",
    "J": "<:rJ:623564440582881282>"
}
