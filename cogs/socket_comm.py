import os
import json
import socket
import logging
import asyncio
from datetime import datetime, timezone
from typing import List, Dict, Iterable
from discord.ext import commands
from discord import HTTPException, ActivityType, Member
from api_client import ResponseCodeError
from .utils.exceptions import (EndpointNotFound, EndpointBadArguments, EndpointError, EndpointSuccess,
                               InternalServerError, DiscordIDNotFound)
from .utils.checks import check_if_it_is_tortoise_guild
from .utils.embed_handler import welcome, welcome_dm

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
tortoise_guild_id = 577192344529404154
tortoise_bot_dev_channel_id = 581139962611892229
tortoise_log_channel_id = 593883395436838942
verified_role_id = 599647985198039050
unverified_role_id = 605808609195982864
verification_url = "https://www.tortoisecommunity.ml/verification/"

# Keys are endpoint names, values are their functions to be called.
_endpoints_mapping = {}


def endpoint_register(*, endpoint_key: str = None):
    """
    Decorator to register new socket endpoint.
    Both sync and async functions can be registered.
    If endpoint_key is not passed then the name of decorated function is used.

    Endpoint function return is optional, if there is a return then that return is passed back as
    key `data` to client, this is dealt in process_request function.

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
        self.auth_token = os.getenv("SOCKET_AUTH_TOKEN")
        self.verified_clients = set()
        self._database_role_update_lock = False
        self._socket_server = SocketCommunication.create_server()
        self.task = self.bot.loop.create_task(self.run_server(self._socket_server))

    def cog_unload(self):
        logger.debug("Unloading socket comm, closing connections.")
        logger.debug(f"Canceling server task..")
        self.task.cancel()
        for client in self.verified_clients:
            try:
                logger.debug(f"Closing client {client}")
                client.close()
            except OSError:
                # Not supported on Windows
                pass
        try:
            logger.debug("Server shutdown..")
            self._socket_server.shutdown(socket.SHUT_RDWR)
            logger.debug("Server closing..")
            self._socket_server.close()
        except OSError:
            # Not supported on Windows
            pass

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    @commands.check(check_if_it_is_tortoise_guild)
    async def test_is_verified(self, ctx, member_id: int):
        try:
            data = await self.bot.api_client.get(f"verify-confirmation/{member_id}/")
        except ResponseCodeError:
            await ctx.send("Does not exist")
            return
        await ctx.send(data)

    @commands.command()
    @commands.has_permissions(administrator=True)
    @commands.check(check_if_it_is_tortoise_guild)
    async def show_data(self, ctx, member: Member):
        data = await self.bot.api_client.get(f"members/edit/{member.id}/")
        await ctx.send(f"{data}")

    @commands.command(enabled=False)
    @commands.is_owner()
    @commands.cooldown(1, 600, commands.BucketType.guild)
    @commands.check(check_if_it_is_tortoise_guild)
    async def mass_member_database_add(self, ctx):
        if ctx.guild.id != tortoise_guild_id:
            await ctx.send("Has to be used in Tortoise guild.")

        logger.debug(f"Starting database mass update.")
        for member in ctx.guild.members:
            try:
                await self.bot.api_client.get(f"verify-confirmation/{member.id}/")
            except ResponseCodeError:
                joined_date = member.joined_at
                if joined_date is None:
                    joined_date = datetime.now(timezone.utc).isoformat(),  # UTC time
                else:
                    joined_date = joined_date.replace(tzinfo=timezone.utc).isoformat()
                
                # User doesn't exist in database, add him
                data = {"user_id": member.id,
                        "guild_id": member.guild.id,
                        "join_date": joined_date,
                        "name": member.display_name,
                        "tag": int(member.discriminator),
                        "member": True}
                await self.bot.api_client.post("members/", json=data)

        logger.debug(f"Database mass update done.")

    @commands.command()
    @commands.has_permissions(administrator=True)
    @commands.check(check_if_it_is_tortoise_guild)
    async def show_endpoints(self, ctx):
        await ctx.send(" ,".join(_endpoints_mapping))

    @commands.Cog.listener()
    async def on_member_join(self, member: Member):
        if member.guild.id != tortoise_guild_id:
            # Functionality only available in Tortoise guild
            return

        logger.debug(f"Checking new member {member.name}")

        try:
            # TODO move this functionality to api client class
            data = await self.bot.api_client.get(f"verify-confirmation/{member.id}/")
        except ResponseCodeError:
            # User doesn't exist in database, add him
            data = {"user_id": member.id,
                    "guild_id": member.guild.id,
                    "join_date": datetime.now(timezone.utc).isoformat(),
                    "name": member.display_name,
                    "tag": int(member.discriminator),
                    "member": True}
            logger.debug(f"Doesn't exist, updating database {data}")
            await self.bot.api_client.post("members/", json=data)
            logger.debug("Database update done.")

            msg = ("Welcome to Tortoise Community!\n"
                   "In order to proceed and join the community you will need to verify.\n\n"
                   f"Please head over to {verification_url}")
            await member.send(embed=welcome_dm(msg))
            return

        verified = data.get("verified")
        log_channel = self.bot.get_channel(tortoise_log_channel_id)
        if verified:
            logger.debug(f"Member {member.id} is verified in database, adding roles..")
            previous_roles = await self.bot.api_client.get(f"members/{member.id}/roles/")
            await self.add_verified_roles_to_member(member, previous_roles["roles"])

            await log_channel.send(embed=welcome(f"{member.mention} has returned to Tortoise Community."))

            logger.debug(f"Adding him as member=True in database")
            data = {"user_id": member.id, "guild_id": member.guild.id, "member": True}
            await self.bot.api_client.put(f"members/edit/{member.id}/", json=data)

            msg = ("Welcome back to Tortoise Community!\n\n"
                   "The roles you had last time will be restored and added back to you.\n")
            await member.send(embed=welcome_dm(msg))
        else:
            await log_channel.send(embed=welcome(f"{member.mention} has joined the Tortoise Community."))
            logger.debug(f"Member {member.id} is not verified in database. Waiting for him to verify.")
            msg = ("Hi, welcome to Tortoise Community!\n"
                   "Seems like this is not your first time joining.\n\n"
                   f"Last time you didn't verify so please head over to {verification_url}")
            await member.send(embed=welcome_dm(msg))

    @commands.Cog.listener()
    async def on_member_remove(self, member: Member):
        if member.guild.id != tortoise_guild_id:
            # Functionality only available in Tortoise guild
            return

        logger.debug(f"Member {member} left, setting member=False in db")
        data = {"user_id": member.id,
                "guild_id": member.guild.id,
                "leave_date": datetime.now(timezone.utc).isoformat(),
                "member": False}
        await self.bot.api_client.put(f"members/edit/{member.id}/", json=data)

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        """
        We save all roles from member so he can get those roles back if he re-joins.
        """
        if after.guild.id != tortoise_guild_id:
            # Functionality only available in Tortoise guild
            return
        elif before.roles == after.roles or self._database_role_update_lock:
            return

        roles_ids = [role.id for role in after.roles]
        logger.debug(f"Roles from member {after} changed, changing db field to: {roles_ids}")
        await self.bot.api_client.put(f"members/edit/{after.id}/", json={"user_id": after.id,
                                                                         "guild_id": after.guild.id,
                                                                         "roles": roles_ids})

    async def add_verified_roles_to_member(self, member: Member, additional_roles: Iterable[int] = tuple()):
        guild = self.bot.get_guild(tortoise_guild_id)
        verified_role = guild.get_role(verified_role_id)
        unverified_role = guild.get_role(unverified_role_id)
        try:
            await member.remove_roles(unverified_role)
        except HTTPException:
            logger.debug(f"Bot could't remove unverified role {unverified_role}")

        self._database_role_update_lock = True
        # In case additional_roles are fetched from database, they can be no longer existing due to not removing roles
        # that got deleted, so just catch Exception and ignore.
        roles = [guild.get_role(role_id) for role_id in additional_roles]
        roles.append(verified_role)
        for role in roles:
            try:
                await member.add_roles(role)
            except Exception:
                continue
        self._database_role_update_lock = False

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

    async def handle_client(self, client, client_name: str):
        request = None
        while request != "quit":
            try:
                request = (await self.bot.loop.sock_recv(client, 255)).decode("utf8")
            except ConnectionResetError:
                # If the client disconnects without sending quit.
                logger.debug(f"{client_name} disconnected.")
                break

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

            if client not in self.verified_clients:
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

    @endpoint_register(endpoint_key="send")
    async def send_to_channel(self, message):
        logger.debug(f"Sending {message} to channel.")
        bot_dev_channel = self.bot.get_channel(tortoise_bot_dev_channel_id)
        await bot_dev_channel.send(message)
        logger.debug(f"Sent {message} to channel!")

    @endpoint_register(endpoint_key="members")
    async def get_member_activities(self, members: List[int]) -> Dict[int, str]:
        response_activities = {}
        tortoise_guild = self.bot.get_guild(tortoise_guild_id)
        logger.debug(f"Processing members: {members}")
        for member_id in members:
            logger.debug(f"Processing member: {member_id}")
            member = tortoise_guild.get_member(int(member_id))

            if member is None:
                logger.debug(f"Member {member_id} not found.")
                response_activities[member_id] = "None"
                continue

            if member.activity is None:
                response_activities[member_id] = "None"
            elif member.activity.type != ActivityType.custom:
                activity = f"{member.activity.type.name} {member.activity.name}"
                response_activities[member_id] = activity
            else:
                response_activities[member_id] = member.activity.name

        logger.debug(f"Processing members done, returning: {response_activities}")
        return response_activities

    @endpoint_register(endpoint_key="verify")
    async def verify_member(self, member_id: str):
        try:
            member_id = int(member_id)
        except ValueError:
            raise EndpointBadArguments()

        guild = self.bot.get_guild(tortoise_guild_id)
        verified_role = guild.get_role(verified_role_id)
        unverified_role = guild.get_role(unverified_role_id)
        bot_dev_channel = guild.get_channel(tortoise_bot_dev_channel_id)
        for check_none in (guild, verified_role, unverified_role, bot_dev_channel):
            if check_none is None:
                raise DiscordIDNotFound()

        member = guild.get_member(member_id)
        if member is None:
            raise DiscordIDNotFound()

        await self.add_verified_roles_to_member(member)
        await member.send("You are now verified.")
        await bot_dev_channel.send(f"{member.mention} is now verified.")


def setup(bot):
    bot.add_cog(SocketCommunication(bot))
