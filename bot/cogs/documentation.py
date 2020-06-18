import os
import re
import io
import zlib

import aiohttp
import discord
from discord.ext import commands

from bot.cogs.utils.embed_handler import info, failure


class Documentation(commands.Cog):
    """
    Taken from Danny bot: https://github.com/Rapptz/RoboDanny
    """
    def __init__(self, bot):
        self.bot = bot
        self._doc_cache = {}
        self.session = aiohttp.ClientSession()

    @classmethod
    def parse_object_inv(cls, stream, url):
        # key: URL
        # n.b.: key doesn't have `discord` or `discord.ext.commands` namespaces
        result = {}

        # first line is version info
        inv_version = stream.readline().rstrip()

        if inv_version != '# Sphinx inventory version 2':
            raise RuntimeError('Invalid objects.inv file version.')

        # next line is "# Project: <name>"
        # then after that is "# Version: <version>"
        projname = stream.readline().rstrip()[11:]
        _ = stream.readline().rstrip()[11:]  # represents version

        # next line says if it's a zlib header
        line = stream.readline()
        if 'zlib' not in line:
            raise RuntimeError('Invalid objects.inv file, not z-lib compatible.')

        # This code mostly comes from the Sphinx repository.
        entry_regex = re.compile(r'(?x)(.+?)\s+(\S*:\S*)\s+(-?\d+)\s+(\S+)\s+(.*)')
        for line in stream.read_compressed_lines():
            match = entry_regex.match(line.rstrip())
            if not match:
                continue

            name, directive, prio, location, dispname = match.groups()
            domain, _, subdirective = directive.partition(':')
            if directive == 'py:module' and name in result:
                """
                From the Sphinx Repository:
                due to a bug in 1.1 and below,
                two inventory entries are created
                for Python modules, and the first
                one is correct
                """
                continue

            # Most documentation pages have a label
            if directive == 'std:doc':
                subdirective = 'label'

            if location.endswith('$'):
                location = location[:-1] + name

            key = name if dispname == '-' else dispname
            prefix = f'{subdirective}:' if domain == 'std' else ''

            if projname == 'discord.py':
                key = key.replace('discord.ext.commands.', '').replace('discord.', '')

            result[f'{prefix}{key}'] = os.path.join(url, location)

        return result

    async def build_documentation_lookup_table(self, page_types):
        cache = {}
        for key, page in page_types.items():
            cache[key] = {}
            async with self.session.get(page + '/objects.inv') as resp:
                if resp.status != 200:
                    raise RuntimeError('Cannot build doc lookup table, try again later.')

                stream = SphinxObjectFileReader(await resp.read())
                cache[key] = self.parse_object_inv(stream, page)

        self._doc_cache = cache

    async def fetch_doc_links(self, ctx, key, obj):
        page_types = {
            'latest': 'https://discordpy.readthedocs.io/en/latest',
            'python': 'https://docs.python.org/3',
        }

        if obj is None:
            await ctx.send(page_types[key])
            return

        if not self._doc_cache:
            await ctx.trigger_typing()
            await self.build_documentation_lookup_table(page_types)

        obj = re.sub(r'^(?:discord\.(?:ext\.)?)?(?:commands\.)?(.+)', r'\1', obj)

        if key.startswith('latest'):
            # point the abc.Messageable types properly:
            q = obj.lower()
            for name in dir(discord.abc.Messageable):
                if name[0] == '_':
                    continue
                if q == name:
                    obj = f'abc.Messageable.{name}'
                    break

        cache = list(self._doc_cache[key].items())

        matches = Fuzzy.finder(obj, cache, key=lambda t: t[0], lazy=False)[:8]

        if len(matches) == 0:
            await ctx.send(embed=failure("Query didn't match any entity"))
            return

        embed_msg = "\n".join(f"[`{key}`]({url})" for key, url in matches)
        embed_msg = info(embed_msg, ctx.me, title="Links")

        await ctx.send(embed=embed_msg)

    @commands.command(aliases=['dpy'])
    async def discordpy(self, ctx, *, obj: str = None):
        """
        Gives you a documentation link for a discord.py entity.
        Events, objects, and functions are all supported through a
        a cruddy fuzzy algorithm.
        """
        await self.fetch_doc_links(ctx, 'latest', obj)

    @commands.command(aliases=['pydoc', 'py'])
    async def python(self, ctx, *, obj: str = None):
        """Gives you a documentation link for a Python entity."""
        await self.fetch_doc_links(ctx, 'python', obj)


class SphinxObjectFileReader:
    # Inspired by Sphinx's InventoryFileReader
    BUFFER_SIZE = 16 * 1024

    def __init__(self, buffer):
        self.stream = io.BytesIO(buffer)

    def readline(self):
        return self.stream.readline().decode('utf-8')

    def skipline(self):
        self.stream.readline()

    def read_compressed_chunks(self):
        decompressor = zlib.decompressobj()
        while True:
            chunk = self.stream.read(self.BUFFER_SIZE)
            if len(chunk) == 0:
                break
            yield decompressor.decompress(chunk)
        yield decompressor.flush()

    def read_compressed_lines(self):
        buf = b''
        for chunk in self.read_compressed_chunks():
            buf += chunk
            pos = buf.find(b'\n')
            while pos != -1:
                yield buf[:pos].decode('utf-8')
                buf = buf[pos + 1:]
                pos = buf.find(b'\n')


class Fuzzy:
    @staticmethod
    def finder(text, collection, *, key=None, lazy=True):
        suggestions = []
        text = str(text)
        pat = '.*?'.join(map(re.escape, text))
        regex = re.compile(pat, flags=re.IGNORECASE)
        for item in collection:
            to_search = key(item) if key else item
            r = regex.search(to_search)
            if r:
                suggestions.append((len(r.group()), r.start(), item))

        def sort_key(tup):
            if key:
                return tup[0], tup[1], key(tup[2])
            return tup

        if lazy:
            return (z for _, _, z in sorted(suggestions, key=sort_key))
        else:
            return [z for _, _, z in sorted(suggestions, key=sort_key)]


def setup(bot):
    bot.add_cog(Documentation(bot))
