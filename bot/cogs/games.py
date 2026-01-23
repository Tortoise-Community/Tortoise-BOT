import logging

import discord
from discord.ext import commands

from bot.utils.gambling_backend import Game, Player
from bot.utils.embed_handler import simple_embed, black_jack_embed
from bot.constants import hit_emoji_id, stay_emoji_id, double_emoji_id, blackjack_player_limit


logger = logging.getLogger(__name__)


class Games(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.live_games = {}
        self.reactable_messages = {}
        self.reaction_options = {
            hit_emoji_id: self.hit,
            stay_emoji_id: self.stay,
            double_emoji_id: self.double
        }

    async def evaluate_results(self, game):
        participants = game.participants
        dealer_card_value = game.dealer.calculate_card_value()
        for participant in list(participants):
            player = participants[participant]
            me = self.bot.get_user(player.user_id)
            if dealer_card_value > 21 or dealer_card_value < player.card_value:
                await player.message.edit(embed=black_jack_embed(me, player, outcome="win", hidden=False))
            elif dealer_card_value > player.card_value:
                await player.message.edit(embed=black_jack_embed(me, player, outcome="lose", hidden=False))
            else:
                await player.message.edit(embed=black_jack_embed(me, player, outcome="tie", hidden=False))
            await self.remove(player)
        del self.live_games[game.channel]

    async def dealers_play(self, game):
        while True:
            card_value = game.dealer.calculate_card_value()
            if card_value < 17:
                game.dealer.cards.append(game.deck.get_random_card())
            else:
                break
        await self.evaluate_results(game)

    async def check_blackjack(self, player):
        player.card_value = player.calculate_card_value()
        me = self.bot.get_user(player.user_id)
        if player.card_value > 21:
            embed = black_jack_embed(me, player, outcome="lose")
            embed.title = "Busted!"
            await player.message.edit(embed=embed)
            await self.remove(player)
        if player.card_value == 21:
            embed = black_jack_embed(me, player, outcome="win")
            embed.title = "Blackjack!"
            await player.message.edit(embed=embed)
            await self.remove(player)

    async def remove(self, player):
        await player.message.clear_reactions()
        player.game.participants.pop(player.user_id)
        self.reactable_messages.pop(player.message.id)
        del player

    async def hit(self, player):
        player.game.deck.give_random_card(player, 1)
        me = self.bot.get_user(player.user_id)
        await player.message.edit(embed=black_jack_embed(me, player))
        await self.check_blackjack(player)
        await self.check_active_session(player.game)

    async def check_active_session(self, player):
        participants = player.game.participants
        for person in participants:
            if participants[person].stay:
                me = self.bot.get_user(player.user_id)
                embed = black_jack_embed(me, player)
                embed.description = "**Status: **Waiting for other players..."
                await player.message.edit(embed=embed)
                return
        await self.dealers_play(player.game)

    async def stay(self, player):
        player.stay = True
        await self.check_blackjack(player)
        await player.message.clear_reactions()
        await self.check_active_session(player)

    async def double(self, player):
        player.bet_amount *= 2
        player.game.deck.give_random_card(player, 1)
        await self.stay(player)

    async def init_blackjack(self, ctx, bet_amount):
        if ctx.channel.id in self.live_games:
            game = self.live_games[ctx.channel.id]
        else:
            game = Game(ctx.channel.id)
            game.deck.give_random_card(game.dealer, 2)
            self.live_games[ctx.channel.id] = game

        if not len(game.participants) == blackjack_player_limit:
            if ctx.author.id not in game.participants:
                player = Player(ctx.author.id, bet_amount, game)
                game.participants[ctx.author.id] = player
                game.deck.give_random_card(player, 2)
                embed = black_jack_embed(ctx.author, player)
                msg = await ctx.channel.send(embed=embed)
                player.message = msg
                self.reactable_messages[msg.id] = player
                emotes = [hit_emoji_id, stay_emoji_id, double_emoji_id]
                for emote in emotes:
                    reaction = self.bot.get_emoji(emote)
                    await msg.add_reaction(reaction)
                await self.check_blackjack(player)
            else:
                await ctx.channel.send(embed=simple_embed(
                    "You've already joined the game. You can try joining another lobby.", "", discord.Color.red())
                )
        else:
            await ctx.channel.send(
                embed=simple_embed("The lobby if full. Try in another channel.", "", discord.Color.red())
            )

    @commands.command(aliases=['bj'])
    async def blackjack(self, ctx):
        """Initializes single/multiplayer blackjack game"""
        # TODO: Bet amount update on server currency implementation
        await self.init_blackjack(ctx, bet_amount=10)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.message_id in self.reactable_messages:
            reaction = self.bot.get_emoji(payload.emoji.id)
            user = self.bot.get_user(payload.user_id)
            player = self.reactable_messages.get(payload.message_id)
            if payload.user_id == player.user_id:
                await player.message.remove_reaction(reaction, user)
                await self.reaction_options[payload.emoji.id](player)  # noqa


async def setup(bot):
    await bot.add_cog(Games(bot))
