import asyncio
from discord.ext import commands


class SocketCommunication(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.socket_server = asyncio.start_server(self.handle_client, "localhost", 15555)
        self.server_task = self.bot.loop.create_task(self.socket_server)
        #self.cog_loaded = True

    def cog_unload(self):
        """
        Stop socket task so new socket connection could be opened when the cog gets loaded again.

        """
        #self.server_task.cancel()
        #self.socket_server.close()
        #self.cog_loaded = False
        # unload it and the server will burn
        pass

    async def test(self, message):
        test_channel = self.bot.get_channel(581139962611892229)
        await test_channel.send(message)

    async def handle_client(self, reader, writer):
        print("Socket connection established, listening...")
        while True:
            try:
                request = (await reader.read(255)).decode("utf8")
            except ConnectionResetError:
                print("Connection lost.. closing.")
                writer.close()
                return

            """if not self.cog_loaded:
                # Quick fix for unloading/loading cogs
                print("Cog not loaded, exiting loop")
                writer.close()
                return"""

            await self.test(request)
            response = "Successfully got: " + request
            writer.write(response.encode("utf8"))
            await writer.drain()


def setup(bot):
    bot.add_cog(SocketCommunication(bot))
