import os
import json
import socket
import logging
import asyncio
from typing import List

from discord.ext import commands
from discord import HTTPException, Forbidden

from bot import constants
from bot.cogs.utils.embed_handler import info, thumbnail, success
from bot.cogs.utils.members import get_member_activity, get_member_status
from bot.cogs.utils.checks import check_if_it_is_tortoise_guild, tortoise_bot_developer_only
from bot.cogs.utils.exceptions import (
    EndpointNotFound, EndpointBadArguments, EndpointError, EndpointSuccess, InternalServerError, DiscordIDNotFound
)


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Keys are endpoint names, values are their functions to be called.
_endpoints_mapping = {}

buffer_size = 255
maximum_buffer = 10240


def endpoint_register(*, endpoint_key: str = None):
    """
    Decorator to register new socket endpoint.
    Both sync and async functions can be registered.
    If endpoint_key is not passed then the name of decorated function is used.

    Endpoint function return is optional, if there is a return then that return is passed back as
    key `data` to client, this is dealt in process_request function.
    Default return is EndpointSuccess().response , see process_request.

    In case of error, decorated function should raise one of the EndpointError sub-types.
    If it doesn't explicitly raise but error does happen it is handled in process_request and appropriate response
    code will be returned to client, this is dealt in process_request function.

    :param endpoint_key: optional name to use as endpoint key.
    """

    def decorator(function):
        nonlocal endpoint_key

        if not endpoint_key:
            endpoint_key = function.__name__

        if endpoint_key in _endpoints_mapping:
            raise Exception(f"Endpoint {endpoint_key} already registered.")

        _endpoints_mapping[endpoint_key] = function

        def wrapper(*args, **kwargs):
            # Both sync and async support.
            async_function = asyncio.coroutine(function)
            loop = asyncio.get_event_loop()
            loop.run_until_complete(async_function(*args, **kwargs))

        return wrapper
    return decorator


class SocketCommunication(commands.Cog):
    """
    Cog dealing with socket communication between the bot and website server.

    How to register new endpoint:
        Just decorate it with @endpoint_register
        Read the docstring of that decorator to know what your endpoint should return/raise.
    """
    def __init__(self, bot):
        self.bot = bot
        self.tortoise_guild = bot.get_guild(constants.tortoise_guild_id)
        self.verified_role = self.tortoise_guild.get_role(constants.verified_role_id)
        self.unverified_role = self.tortoise_guild.get_role(constants.unverified_role_id)
        self.successful_verifications_channel = bot.get_channel(constants.successful_verifications_channel_id)
        self.welcome_channel = bot.get_channel(constants.welcome_channel_id)
        self.verified_emoji = bot.get_emoji(constants.verified_emoji_id)
        self.verified_clients = set()
        self.auth_token = os.getenv("SOCKET_AUTH_TOKEN")
        self._socket_server = SocketCommunication.create_server()
        self.task = self.bot.loop.create_task(self.run_server(self._socket_server))

    def cog_unload(self):
        logger.debug("Unloading socket comm, closing connections.")
        self.task.cancel()

        for client in self.verified_clients:
            try:
                client.close()
            except OSError:
                # Not supported on Windows
                pass

        try:
            self._socket_server.shutdown(socket.SHUT_RDWR)
            self._socket_server.close()
        except OSError:
            # Not supported on Windows
            pass

        logger.debug("Socket com unloaded.")

    @commands.command()
    @commands.check(check_if_it_is_tortoise_guild)
    @commands.check(tortoise_bot_developer_only)
    async def show_endpoints(self, ctx):
        await ctx.send(" ,".join(_endpoints_mapping))

    @staticmethod
    def create_server():
        logger.debug("Starting socket comm server...")
        server = socket.socket()
        server.bind(("0.0.0.0", 15555))
        server.listen(3)
        server.setblocking(False)
        logger.debug("Socket comm server started.")
        return server

    async def run_server(self, server: socket.socket):
        while True:
            client, _ = await self.bot.loop.sock_accept(server)
            client_name = client.getpeername()
            logger.info(f"{client_name} connected.")
            self.bot.loop.create_task(self.handle_client(client, client_name))

    async def handle_client(self, client, client_name: str):
        while True:  # keep receiving client requests until he closes/disconnects
            request = ""

            while True:  # buffer client request in case of long message
                try:
                    buffer = (await self.bot.loop.sock_recv(client, buffer_size)).decode("utf8")
                    request += buffer
                except ConnectionResetError:
                    # If the client disconnects without sending quit.
                    logger.debug(f"{client_name} disconnected.")
                    return

                if len(buffer) < buffer_size:
                    break
                elif len(request) > maximum_buffer:
                    response = EndpointError(400, "Buffer size exceeded.").response
                    await self.send_to_client(client, json.dumps(response))
                    client.close()
                    return

            if not request:
                logger.debug("Empty, closing.")
                break

            try:
                request = json.loads(request)
            except json.JSONDecodeError:
                response = EndpointError(400, "Not a valid JSON formatted request.").response
                await self.send_to_client(client, json.dumps(response))
                logger.debug(f"{client_name}:{response}:{request}")
                continue

            logger.debug(f"Server got:{request}")

            # TODO
            # temporal hardcoded fix to make ping endpoint public
            endpoint_key = request.get("endpoint")

            if client not in self.verified_clients and endpoint_key != "ping":
                token = request.get("auth")
                if token is not None and token == self.auth_token:
                    self.verified_clients.add(client)
                    response = EndpointSuccess().response
                    await self.send_to_client(client, json.dumps(response))
                    logger.info(f"{client_name} successfully authorized.")
                    continue
                else:
                    response = EndpointError(401, "Verification unsuccessful, closing conn..").response
                    await self.send_to_client(client, json.dumps(response))
                    logger.debug(f"{client_name}:{response}:{request}")
                    break

            response = await self.process_request(request)
            logger.debug(f"Request processed, response:{response}")
            await self.send_to_client(client, json.dumps(response))

        logger.info(f"Closing {client_name}")
        self.verified_clients.discard(client)
        client.close()

    async def send_to_client(self, client, msg: str):
        """
        Send response message to specified client.
        """
        try:
            await self.bot.loop.sock_sendall(client, bytes(msg.encode("unicode_escape")))
        except BrokenPipeError:
            # If the client closes the connection too quickly or just does't even bother listening to response we'll
            # get this, so just ignore
            pass

    async def process_request(self, request: dict) -> dict:
        """
        This should be called for each client request.

        Parses requests and deals with any errors and responses to client.
        :param request: dict which has to be formatted as follows:
            {
              "endpoint": "string which endpoint to use",
              "data": [optional] data to be used on endpoint function (list of member IDs etc)
            }
            Endpoint is available if it was decorated with @endpoint_register
        """
        if not isinstance(request, dict):
            logger.critical("Error processing socket comm, request is not a dict.")
            return InternalServerError().response

        endpoint_key = request.get("endpoint")

        if not endpoint_key:
            return EndpointError(400, "No endpoint specified.").response
        elif not isinstance(endpoint_key, str):
            return EndpointError(400, "Endpoint name has to be a string.").response

        function = _endpoints_mapping.get(endpoint_key)

        if function is None:
            return EndpointNotFound().response

        endpoint_data = request.get("data")

        try:
            # Key data is optional
            if not endpoint_data:
                endpoint_returned_data = await function(self)
            else:
                endpoint_returned_data = await function(self, endpoint_data)
        except TypeError as e:
            logger.critical(f"Bad arguments for endpoint {endpoint_key} {endpoint_data} {e}")
            return EndpointBadArguments().response
        except EndpointError as e:
            # If endpoint function raises then return it's response
            return e.response
        except Exception as e:
            logger.critical(f"Error processing socket endpoint: {endpoint_key} , data:{endpoint_data} {e}")
            return InternalServerError().response

        # If we've come all the way here then no errors occurred and endpoint function executed correctly.
        server_response = EndpointSuccess().response

        # Endpoint return data is optional
        if endpoint_returned_data is None:
            return server_response
        else:
            server_response.update({"data": endpoint_returned_data})
            return endpoint_returned_data

    @endpoint_register(endpoint_key="send")
    async def send(self, data: dict):
        """
        Makes the bot send requested message channel or user or both.
        :param data: dict in format
        {
        "channel_id": 123,
        "user_id": 123,
        "message": "Test"
        }

        Where both channel_id and user_id are optional but at least one has to be passed.
        Message is the message to send.
        """
        message = data.get("message")
        if message is None:
            raise EndpointBadArguments()

        channel_id = data.get("channel_id")
        user_id = data.get("user_id")

        if channel_id is None and user_id is None:
            raise EndpointBadArguments()

        channel = self.bot.get_channel(channel_id)
        user = self.bot.get_user(user_id)

        if channel is None and user is None:
            raise DiscordIDNotFound()

        if channel is not None:
            await channel.send(embed=thumbnail(message, self.bot.user))

        if user is not None:
            try:
                await user.send(embed=thumbnail(message, self.bot.user, "A message just for you!"))
            except Forbidden:
                logger.info(f"Skipping send endpoint to {user} as he blocked DMs.")

    @endpoint_register(endpoint_key="member_activities")
    async def get_member_data(self, members: List[int]) -> dict:
        """
        Gets activities and top role from all members passed in param members.
        :param members: list of member ids to get activity and top role from
        :return: dict in form:
        {
          'status': 200,
          'data': {
            'member_id':  {"activity": "bla_bla", "top_role": "role name"},
            ...
          }
        }
        """
        response_data = {}
        logger.debug(f"Processing members: {members}")

        for member_id in members:
            member = self.tortoise_guild.get_member(member_id)
            member_data = {"activity": "NOT FOUND", "top_role": "NOT FOUND"}

            if member is None:
                logger.debug(f"Member {member_id} not found.")
                response_data[member_id] = member_data
                continue

            activity = get_member_activity(member)
            if activity is None:
                activity = get_member_status(member)

            member_data["activity"] = activity

            member_data["top_role"] = member.top_role.name
            response_data[member_id] = member_data

        return_data = {"data": response_data}
        return return_data

    @endpoint_register(endpoint_key="verify")
    async def verify_member(self, member_id: str):
        """
        Verifies the member, adds him the role and marks him as verified in the database,
        also sends success messages.
        :param member_id: str member id to verify
        """
        try:
            member_id = int(member_id)
        except ValueError:
            raise EndpointBadArguments()

        none_checks = (
            self.tortoise_guild, self.verified_role, self.unverified_role, self.successful_verifications_channel
            )

        for check_none in none_checks:
            if check_none is None:
                logger.info(f"One of necessary IDs was not found {none_checks}")
                raise DiscordIDNotFound()

        member = self.tortoise_guild.get_member(member_id)

        if member is None:
            logger.critical(f"Can't verify, member is not found in guild {member} {member_id}")
            raise DiscordIDNotFound()

        try:
            await member.remove_roles(self.unverified_role)
        except HTTPException:
            logger.warning(f"Bot could't remove unverified role {self.unverified_role}")

        await member.add_roles(self.verified_role)
        await self.successful_verifications_channel.send(embed=info(
            f"{member} is now verified.", member.guild.me, title="")
        )

        msg = (
            f"You are now verified {self.verified_emoji}\n\n"
            f"Make sure to read {self.welcome_channel.mention}"
        )
        await member.send(embed=success(msg))

    @endpoint_register()
    async def contact(self, data: dict):
        """
        Sends request data to website log channel.
        :param data: dict data from the request
        """
        guild = self.bot.get_guild(constants.tortoise_guild_id)
        website_log_channel = guild.get_channel(constants.website_log_channel_id)

        for check_none in (guild, website_log_channel):
            if check_none is None:
                raise DiscordIDNotFound()

        await website_log_channel.send(f"{data}")

    @endpoint_register()
    async def signal_update(self, signal: str):
        """
        Signals the bot it should update something locally like cache by fetching it from database.
        :param signal: can be:
                       'rules' signals updating rules
                       'server_meta' signals updating server meta
        """
        if signal == "rules":
            # TODO
            pass
        elif signal == "server_meta":
            # Don't await as API is waiting for response, (for some reason it sends signal and updates db after)
            self.bot.loop.create_task(self.bot.reload_tortoise_meta_cache())
        else:
            raise EndpointBadArguments()

    @endpoint_register()
    async def ping(self):
        if self.bot.is_closed():
            raise EndpointError(503, "VPS online but Discord websocket closed.")


def setup(bot):
    bot.add_cog(SocketCommunication(bot))
