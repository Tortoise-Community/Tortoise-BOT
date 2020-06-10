import re
import io
import zlib


def construct_load_bar_string(percent, message=None, size=None):

    # Taken from albertopoljak's Licensy Bot coded in discord.py
    # Original source: https://github.com/albertopoljak/Licensy
    if size is None:
        size = 10
    else:
        if size < 8:
            size = 8

    limiters = "|"
    element_emtpy = "▱"
    element_full = "▰"
    constructed = ""

    if percent > 100:
        percent = 100
    progress = int(round(percent / size))

    constructed += limiters
    for x in range(0, progress):
        constructed += element_full
    for x in range(progress, size):
        constructed += element_emtpy
    constructed += limiters
    if message is None:
        constructed = f"{constructed} {percent:.2f}%"
    else:
        constructed = f"{constructed} {message}"
    return constructed


class SphinxObjectFileReader:
    # Inspired by Sphinx's InventoryFileReader
    BUFSIZE = 16 * 1024

    def __init__(self, buffer):
        self.stream = io.BytesIO(buffer)

    def readline(self):
        return self.stream.readline().decode('utf-8')

    def skipline(self):
        self.stream.readline()

    def read_compressed_chunks(self):
        decompressor = zlib.decompressobj()
        while True:
            chunk = self.stream.read(self.BUFSIZE)
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
