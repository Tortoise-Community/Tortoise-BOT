"""
Copyright (c)
    Original source code:   https://gist.github.com/EvieePy/ab667b74e9758433b3eb806c53a19f34
                  author:   https://github.com/EvieePy

The code has been changed to go along Tortoise needs.
You can check the commits to see change history.
"""

import logging
import asyncio
import itertools
import traceback
from functools import partial

import discord
from discord.ext import commands
from youtube_dl import YoutubeDL
from async_timeout import timeout

from bot.utils.checks import check_if_it_is_tortoise_guild
from bot.utils.exceptions import TortoiseGuildCheckFailure
from bot.utils.embed_handler import success, failure, info
from bot.constants import ytdl_format_options, ffmpeg_options


logger = logging.getLogger(__name__)
ytdl = YoutubeDL(ytdl_format_options)


class VoiceConnectionError(commands.CommandError):
    """Custom Exception class for connection errors."""


class InvalidVoiceChannel(VoiceConnectionError):
    """Exception for cases of invalid Voice Channels."""


class YTDLSource(discord.PCMVolumeTransformer):

    def __init__(self, source, *, data, requester):
        super().__init__(source)
        self.requester = requester

        self.title = data.get("title")
        self.web_url = data.get("webpage_url")

        # YTDL info dicts (data) have other useful information you might want
        # https://github.com/rg3/youtube-dl/blob/master/README.md

    def __getitem__(self, item: str):
        """Allows us to access attributes similar to a dict.
        This is only useful when you are NOT downloading.
        """
        return self.__getattribute__(item)

    @classmethod
    async def create_source(cls, ctx, search: str, *, loop, download=False):
        loop = loop or asyncio.get_event_loop()

        to_run = partial(ytdl.extract_info, url=search, download=download)
        data = await loop.run_in_executor(None, to_run)

        if "entries" in data:
            # take first item from a playlist
            data = data["entries"][0]

        await ctx.send(embed=info(f"```ini\n[Added {data['title']} to the queue.]```", ctx.me, ""))

        if download:
            source = ytdl.prepare_filename(data)
        else:
            return {"webpage_url": data["webpage_url"], "requester": ctx.author, "title": data["title"]}

        return cls(discord.FFmpegPCMAudio(source, **ffmpeg_options), data=data, requester=ctx.author)

    @classmethod
    async def regather_stream(cls, data, *, loop):
        """Used for preparing a stream, instead of downloading.
        Since Youtube Streaming links expire."""
        loop = loop or asyncio.get_event_loop()
        requester = data["requester"]

        to_run = partial(ytdl.extract_info, url=data["webpage_url"], download=False)
        data = await loop.run_in_executor(None, to_run)

        return cls(discord.FFmpegPCMAudio(data["url"], **ffmpeg_options), data=data, requester=requester)


class MusicPlayer:
    """A class which is assigned to each guild using the bot for Music.
    This class implements a queue and loop, which allows for different guilds to listen to different playlists
    simultaneously.
    When the bot disconnects from the Voice it's instance will be destroyed.
    """

    __slots__ = ("bot", "_guild", "_channel", "_cog", "queue", "next", "current", "now_playing", "volume")

    def __init__(self, ctx):
        self.bot = ctx.bot
        self._guild = ctx.guild
        self._channel = ctx.channel
        self._cog = ctx.cog

        self.queue = asyncio.Queue()
        self.next = asyncio.Event()
        self.now_playing = "Nothing."

        self.volume = .5
        self.current = None

        ctx.bot.loop.create_task(self.player_loop())

    async def player_loop(self):
        """Our main player loop."""
        await self.bot.wait_until_ready()

        while not self.bot.is_closed():
            self.next.clear()

            try:
                # Wait for the next song. If we timeout cancel the player and disconnect...
                async with timeout(300):
                    source = await self.queue.get()
            except asyncio.TimeoutError:
                return self.destroy(self._guild)

            if not isinstance(source, YTDLSource):
                # Source was probably a stream (not downloaded)
                # So we should regather to prevent stream expiration
                try:
                    source = await YTDLSource.regather_stream(source, loop=self.bot.loop)
                except Exception as e:
                    await self._channel.send(
                        embed=failure(
                            f"There was an error processing your song.\n"
                            f"```css\n[{e}]```"
                        )
                    )
                    continue

            source.volume = self.volume
            self.current = source

            self._guild.voice_client.play(source, after=lambda _: self.bot.loop.call_soon_threadsafe(self.next.set))
            self.now_playing = f"`{source.title}` requested by `{source.requester}`"
            await self._channel.send(
                embed=info(
                    self.now_playing,
                    self._guild.me,
                    title="Now playing"
                )
            )
            await self.next.wait()

            # Make sure the FFmpeg process is cleaned up.
            source.cleanup()
            self.current = None
            self.now_playing = "Nothing."

    def destroy(self, guild):
        """Disconnect and cleanup the player."""
        return self.bot.loop.create_task(self._cog.cleanup(guild))


class Music(commands.Cog):
    """Music related commands."""

    __slots__ = ("bot", "players")

    def __init__(self, bot):
        self.bot = bot
        self.players = {}

    async def cleanup(self, guild):
        try:
            await guild.voice_client.disconnect()
        except AttributeError:
            pass

        try:
            del self.players[guild.id]
        except KeyError:
            pass

    async def cog_check(self, ctx):
        """A local check which applies to all commands in this cog."""
        if not ctx.guild:
            raise commands.NoPrivateMessage
        else:
            return check_if_it_is_tortoise_guild(ctx)

    async def cog_command_error(self, ctx, error):
        """A local error handler for all errors arising from commands in this cog."""
        if isinstance(error, commands.NoPrivateMessage):
            try:
                return await ctx.send(embed=failure("This command can not be used in private messages."))
            except discord.HTTPException:
                pass
        elif isinstance(error, InvalidVoiceChannel):
            await ctx.send(
                embed=failure(
                    "Error connecting to Voice Channel. "
                    "Please make sure you are in a valid channel or provide me with one"
                )
            )
        elif isinstance(error, TortoiseGuildCheckFailure):
            await ctx.send(embed=failure(f"{error}"))
        else:
            traceback_msg = traceback.format_exception(etype=type(error), value=error, tb=error.__traceback__)
            logger.error(traceback_msg)
            await self.bot.log_error(traceback_msg)

    def get_player(self, ctx):
        """Retrieve the guild player, or generate one."""
        try:
            player = self.players[ctx.guild.id]
        except KeyError:
            player = MusicPlayer(ctx)
            self.players[ctx.guild.id] = player

        return player

    @commands.command(name="connect", aliases=["join"])
    async def connect_(self, ctx, *, channel: discord.VoiceChannel = None):
        """Connect to voice.
        Parameters
        ------------
        channel: discord.VoiceChannel [Optional]
            The channel to connect to. If a channel is not specified, an attempt to join the voice channel you are in
            will be made.
        This command also handles moving the bot to different channels.
        Note - The channel has to have 'music' in it's name. This is to avoid spamming music in general voice chats.
        """
        if not channel:
            try:
                channel = ctx.author.voice.channel
            except AttributeError:
                raise InvalidVoiceChannel("No channel to join. Please either specify a valid channel or join one.")

        if "music" not in channel.name.lower():
            raise InvalidVoiceChannel("Can't join channel - channel has to have 'music' in it's name.")

        vc = ctx.voice_client

        if vc:
            if vc.channel.id == channel.id:
                return
            try:
                await vc.move_to(channel)
            except asyncio.TimeoutError:
                raise VoiceConnectionError(f"Moving to channel: <{channel}> timed out.")
        else:
            try:
                await channel.connect()
            except asyncio.TimeoutError:
                raise VoiceConnectionError(f"Connecting to channel: <{channel}> timed out.")

        await ctx.send(embed=success(f"Connected to: **{channel}**", ctx.me))

    @commands.command(name="play", aliases=["sing"])
    async def play_(self, ctx, *, search: str):
        """Request a song and add it to the queue.
        This command attempts to join a valid voice channel if the bot is not already in one.
        Uses YTDL to automatically search and retrieve a song.
        Parameters
        ------------
        search: str [Required]
            The song to search and retrieve using YTDL. This could be a simple search, an ID or URL.
        """
        await ctx.trigger_typing()

        vc = ctx.voice_client

        if not vc:
            await ctx.invoke(self.connect_)

        player = self.get_player(ctx)

        # If download is False, source will be a dict which will be used later to regather the stream.
        # If download is True, source will be a discord.FFmpegPCMAudio with a VolumeTransformer.
        source = await YTDLSource.create_source(ctx, search, loop=self.bot.loop, download=False)

        await player.queue.put(source)

    @commands.command(name="pause")
    async def pause_(self, ctx):
        """Pause the currently playing song."""
        vc = ctx.voice_client

        if not vc or not vc.is_playing():
            return await ctx.send(embed=failure("I am not currently playing anything!"))
        elif vc.is_paused():
            return

        vc.pause()
        await ctx.send(embed=info(f"**`{ctx.author}`** paused the song.", ctx.me, title="Song paused"))

    @commands.command(name="resume")
    async def resume_(self, ctx):
        """Resume the currently paused song."""
        vc = ctx.voice_client

        if not vc or not vc.is_connected():
            return await ctx.send(embed=failure("I am not currently playing anything!"))
        elif not vc.is_paused():
            return

        vc.resume()
        await ctx.send(embed=info(f"**`{ctx.author}`** resumed the song.", ctx.me, title="Song resumed"))

    @commands.command(name="skip")
    async def skip_(self, ctx):
        """Skip the song."""
        vc = ctx.voice_client

        if not vc or not vc.is_connected():
            return await ctx.send(embed=failure("I am not currently playing anything!"))

        if vc.is_paused():
            pass
        elif not vc.is_playing():
            return

        vc.stop()
        await ctx.send(embed=info(f"**`{ctx.author}`** skipped the song.", ctx.me, title="Skipping song"))

    @commands.command(name="queue", aliases=["q", "playlist"])
    async def queue_info(self, ctx):
        """Retrieve a basic queue of upcoming songs."""
        vc = ctx.voice_client

        if not vc or not vc.is_connected():
            return await ctx.send(embed=failure("I am not currently connected to voice!"))

        player = self.get_player(ctx)
        if player.queue.empty():
            return await ctx.send(embed=failure("There are currently no more queued songs."))

        # Grab up to 5 entries from the queue...
        upcoming = list(itertools.islice(player.queue._queue, 0, 5))

        fmt = "\n".join(f"**`{_['title']}`**" for _ in upcoming)
        embed = discord.Embed(title=f"Upcoming - Next {len(upcoming)}", description=fmt)

        await ctx.send(embed=embed)

    @commands.command(name="now_playing", aliases=["np", "current", "currentsong", "playing"])
    async def now_playing_(self, ctx):
        """Display information about the currently playing song."""
        vc = ctx.voice_client

        if not vc or not vc.is_connected():
            return await ctx.send(embed=failure("I am currently not connected to voice!"))

        player = self.get_player(ctx)
        if not player.current:
            return await ctx.send(embed=failure("I am currently not playing anything."))

        await ctx.send(
            embed=info(
                f"`{vc.source.title}` requested by `{vc.source.requester}`",
                ctx.me,
                title="Now playing"
            )
        )

    @commands.command(name="volume", aliases=["vol"])
    async def change_volume(self, ctx, *, volume: float):
        """Change the player volume.
        Parameters
        ------------
        volume: float or int [Required]
            The volume to set the player to in percentage. This must be between 1 and 100.
        """
        vc = ctx.voice_client

        if not vc or not vc.is_connected():
            return await ctx.send(embed=failure("I am not currently connected to voice!"))

        if not 0 < volume < 101:
            return await ctx.send(embed=failure("Please enter a value between 1 and 100."))

        player = self.get_player(ctx)

        if vc.source:
            vc.source.volume = volume / 100

        player.volume = volume / 100
        await ctx.send(
            embed=info(
                f"**`{ctx.author}`** set the volume to **{volume}%**", ctx.me, title="Volume update"
            )
        )

    @commands.command(name="stop")
    async def stop_(self, ctx):
        """Stop the currently playing song and destroy the player.
        !Warning!
            This will destroy the player assigned to your guild, also deleting any queued songs and settings.
        """
        vc = ctx.voice_client

        if not vc or not vc.is_connected():
            return await ctx.send(embed=failure("I am not currently playing anything!"))

        await self.cleanup(ctx.guild)


def setup(bot):
    bot.add_cog(Music(bot))
