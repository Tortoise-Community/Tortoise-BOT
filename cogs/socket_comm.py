import socket
from discord.ext import commands


class SocketCommunication(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.verified_clients = set()
        self.bot.loop.create_task(self.run_server(self.get_server()))

    @classmethod
    def get_server(cls):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind(("localhost", 15555))
        server.listen(8)
        server.setblocking(False)
        return server

    def cog_unload(self):
        pass

    async def test(self, message):
        test_channel = self.bot.get_channel(581139962611892229)
        await test_channel.send(message)

    async def handle_client(self, client):
        request = None
        while request != "quit":
            try:
                request = (await self.bot.loop.sock_recv(client, 255)).decode("utf8")
            except ConnectionResetError:
                # If the client disconnects without sending quit.
                print(f"{client.getpeername()} disconnected.")
                break

            print(f"Server got:{request}")
            await self.test(f"Client says:{request}")
            response = f"Okay: '{request}'"

            try:
                await self.bot.loop.sock_sendall(client, response.encode("utf8"))
            except BrokenPipeError:
                # If the client closes the connection too quickly or just does't even bother listening to response we'll
                # get this, so just ignore
                pass
        client.close()

    async def run_server(self, server: socket.socket):
        while True:
            client, _ = await self.bot.loop.sock_accept(server)
            print(f"{client.getpeername()} connected.")
            self.bot.loop.create_task(self.handle_client(client))


def setup(bot):
    bot.add_cog(SocketCommunication(bot))
