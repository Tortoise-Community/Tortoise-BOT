import re
from datetime import datetime

from dateutil.relativedelta import relativedelta

from discord.ext.commands import BadArgument, Context, Converter, MemberConverter


class Duration(Converter):
    """
    Convert duration strings into UTC datetime.datetime objects.
    Source: https://github.com/python-discord/bot/blob/master/bot/converters.py
    """

    duration_parser = re.compile(
        r"((?P<years>\d+?) ?(years|year|Y|y) ?)?"
        r"((?P<months>\d+?) ?(months|month|m) ?)?"
        r"((?P<weeks>\d+?) ?(weeks|week|W|w) ?)?"
        r"((?P<days>\d+?) ?(days|day|D|d) ?)?"
        r"((?P<hours>\d+?) ?(hours|hour|H|h) ?)?"
        r"((?P<minutes>\d+?) ?(minutes|minute|M) ?)?"
        r"((?P<seconds>\d+?) ?(seconds|second|S|s))?"
    )

    async def convert(self, ctx: Context, duration: str) -> datetime:
        """
        Converts a `duration` string to a datetime object that's `duration` in the future.
        The converter supports the following symbols for each unit of time:
        - years: `Y`, `y`, `year`, `years`
        - months: `m`, `month`, `months`
        - weeks: `w`, `W`, `week`, `weeks`
        - days: `d`, `D`, `day`, `days`
        - hours: `H`, `h`, `hour`, `hours`
        - minutes: `M`, `minute`, `minutes`
        - seconds: `S`, `s`, `second`, `seconds`
        The units need to be provided in descending order of magnitude.
        """
        match = self.duration_parser.fullmatch(duration)
        if not match:
            raise BadArgument(f"`{duration}` is not a valid duration string.")

        duration_dict = {unit: int(amount) for unit, amount in match.groupdict(default=0).items()}
        delta = relativedelta(**duration_dict)
        now = datetime.utcnow()

        return now + delta


class DatabaseMember(MemberConverter):
    """
    Database deals with IDs only.
    However, for convenience, we want the commands to be able to work with member names/mentions.
    If we used regular MemberConverter/UserConverter we would be limited to existing users.
    This converter allows passing any discord ID or, for existing members, member name/mention.
    """
    async def convert(self, ctx, id_or_member: str) -> int:
        """
        :param id_or_member: str argument coming from discord.
                             Can be id, name, nick, mention etc lookup MemberConverter for more info.
                             Note that ID will be string as it's coming from discord message.
        """
        try:
            return int(id_or_member)
        except ValueError:
            member = await super().convert(ctx, id_or_member)
            return member.id
