import sys

import discord


class CACHE:
    def __init__(self):
        self.cache = {}
        self.size = 40

    def __iter__(self):
        return self.cache


class TRACKER:
    def __init__(self, bot):
        self.bot = bot
        self.__cache = CACHE()

    async def all_invites(self):
        for guild in self.bot.guilds:
            self.__cache.cache[guild.id] = {}
            try:
                invites = await guild.invites()
                for invite in invites:
                    if invite.inviter not in self.__cache.cache[guild.id].keys():
                        self.__cache.cache[guild.id][invite.inviter] = []
                    self.__cache.cache[guild.id][invite.inviter].append(invite)
                self.__cache.size = sys.getsizeof(self.__cache.cache)
            except discord.errors.Forbidden:
                pass

    async def update_invite(self, invite):
        try:
            if invite.guild.id not in self.__cache.cache.keys():
                self.__cache.cache[invite.guild.id] = {}
            if invite.inviter not in self.__cache.cache[invite.guild.id].keys():
                self.__cache.cache[invite.guild.id][invite.inviter] = []
            self.__cache.cache[invite.guild.id][invite.inviter].append(invite)
            self.__cache.size = sys.getsizeof(self.__cache.cache)
        except discord.errors.Forbidden:
            return

    async def remove_invites(self, invite):
        for key in self.__cache.cache:
            for lists in self.__cache.cache[key]:
                user = self.__cache.cache[key][lists]
                if invite in user:
                    self.__cache.cache[key][lists].remove(invite)
                    self.__cache.size = sys.getsizeof(self.__cache.cache)
                    break

    async def delete_guild_invites(self, guild: discord.Guild):
        if guild.id in self.__cache.cache.keys():
            self.__cache.size = sys.getsizeof(self.__cache.cache)
            del self.__cache.cache[guild.id]

    async def create_guild_invites(self, guild: discord.Guild):
        try:
            invites = await guild.invites()
            self.__cache.cache[guild.id] = {}
            for invite in invites:
                if invite.inviter not in self.__cache.cache[guild.id].keys():
                    self.__cache.cache[guild.id][invite.inviter] = []
                self.__cache.cache[guild.id][invite.inviter].append(invite)
            self.__cache.size = sys.getsizeof(self.__cache.cache)
        except discord.errors.Forbidden:
            return

    async def get_inviter(self, member: discord.Member):
        invites = {}
        try:
            new_invites = await member.guild.invites()
        except discord.errors.Forbidden:
            return
        for invite in new_invites:
            if invite.inviter not in invites.keys():
                invites[invite.inviter] = []
            invites[invite.inviter].append(invite)
        for new_invite_key in invites:
            for cached_invite_key in self.__cache.cache[member.guild.id]:
                if new_invite_key == cached_invite_key:
                    new_invite_list = invites[new_invite_key]
                    cached_invite_list = self.__cache.cache[member.guild.id][cached_invite_key]
                    for new_invite in new_invite_list:
                        for old_invite in cached_invite_list:
                            if new_invite.code == old_invite.code and new_invite.uses-old_invite.uses >= 1:
                                cached_invite_list.remove(old_invite)
                                cached_invite_list.append(new_invite)
                                self.__cache.size = sys.getsizeof(self.__cache.cache)
                                return new_invite_key
        else:
            return None
