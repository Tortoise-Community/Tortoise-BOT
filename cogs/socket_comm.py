import json
import socket
from discord.ext import commands


class SocketCommunication(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.tokens = ("abc", "test")
        self.verified_clients = set()
        self.bot.loop.create_task(self.run_server(self.get_server()))

    @classmethod
    def get_server(cls):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind(("localhost", 15555))
        server.listen(3)
        server.setblocking(False)
        return server

    def cog_unload(self):
        pass

    async def test(self, message):
        test_channel = self.bot.get_channel(581139962611892229)
        await test_channel.send(message)

    async def handle_client(self, client):
        request = None
        client_name = client.getpeername()
        while request != "quit":
            try:
                request = (await self.bot.loop.sock_recv(client, 255)).decode("utf8")
            except ConnectionResetError:
                # If the client disconnects without sending quit.
                print(f"{client_name} disconnected.")
                break

            try:
                request = json.loads(request)
            except json.JSONDecodeError:
                response = {"status": 400, "response": "Not a valid JSON formatted request."}
                await self.send_to_client(client, json.dumps(response))
                print(f"{client_name}:{response}\n{request}")
                continue

            print(f"Server got:\n{request}")

            if client_name not in self.verified_clients:
                token = request.get("Auth")
                if token is not None and token in self.tokens:
                    self.verified_clients.add(client_name)
                    response = {"status": 200}
                    await self.send_to_client(client, json.dumps(response))
                    print(f"{client_name}:{response}\n{request}")
                    continue
                else:
                    response = {"status": 401, "response": "Verification unsuccessful, closing conn."}
                    await self.send_to_client(client, json.dumps(response))
                    print(f"{client_name}:{response}\n{request}")
                    break

            await self.parse_request(request, client)
        print(f"Closing {client_name}")
        client.close()

    async def send_to_client(self, client, msg):
        try:
            await self.bot.loop.sock_sendall(client, msg.encode("utf8"))
        except BrokenPipeError:
            # If the client closes the connection too quickly or just does't even bother listening to response we'll
            # get this, so just ignore
            pass

    async def parse_request(self, request: dict, client):
        """
        Dict with possible keys:
        "Send" sends value to text channel
        """
        send = request.get("Send")
        if send is not None:
            await self.test(f"Client says:{send}")
            response = {"status": 200}
            await self.send_to_client(client, json.dumps(response))

    async def run_server(self, server: socket.socket):
        while True:
            client, _ = await self.bot.loop.sock_accept(server)
            print(f"{client.getpeername()} connected.")
            self.bot.loop.create_task(self.handle_client(client))


def setup(bot):
    bot.add_cog(SocketCommunication(bot))
