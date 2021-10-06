import random
from typing import List

import discord
from bot.constants import card_emotes, blank_card_emoji


class Player:
    def __init__(self, user_id: int, bet_amount, game, message: discord.Message = None, is_dealer=False):
        self.user_id = user_id
        self.bet_amount = int(bet_amount)
        self.card_value = 0
        self.cards = []
        self.game = game
        self.message = message
        self.stay = False
        self.is_dealer = is_dealer

    def calculate_card_value(self) -> int:
        value = 0
        a_count = 0
        for card in self.cards:
            if card.name == "A":
                a_count += 1
            elif card.name in ("K", "Q", "J"):
                value += 10
            else:
                value += int(card.name)

        if not self.is_dealer:
            if a_count != 0:
                for _ in range(a_count):
                    if value + 11 > 21:
                        value += 1
                    else:
                        value += 11
            self.card_value = value
            return value
        else:
            if a_count != 0:
                for _ in range(a_count):
                    if value > 17:
                        value += 1
                    else:
                        value += 11
            self.card_value = value
            return value

    def get_emote_string(self, hidden=True) -> str:
        if not hidden:
            emote_string = "".join(card.emote for card in self.cards)
            return f"{emote_string}\nvalue: {self.card_value}"
        return f"{self.cards[0].emote} + {blank_card_emoji}\nvalue: ?"


class Game():
    def __init__(self, channel: discord.TextChannel):   # noqa
        self.channel = channel
        self.participants = {}
        self.deck = Deck()
        self.dealer = Player(0000, 0, game=self, is_dealer=True)


class Card(object):
    def __init__(self, suit: str, name: str):
        self.suit = suit
        self.name = name
        self.emote = self._get_emoji()

    def __str__(self):
        return f"{self.name} of {self.suit}"

    def _get_emoji(self):
        return card_emotes[self.suit].get(self.name)


class Deck:
    suits = ("club", "heart", "diamond", "spade")
    cards_set = ("A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "K", "Q", "J")

    def __init__(self):
        self.cards = self.build_deck()
        self.shuffle()

    def build_deck(self) -> List[Card]:
        return [Card(suit, card) for suit in self.suits for card in self.cards_set]

    def shuffle(self) -> None:
        for _ in range(random.randint(1, 9)):
            random.shuffle(self.cards)

    def get_random_cards(self, count: int) -> List[Card]:
        cards_list = []
        for i in range(count):
            random_card = random.choice(self.cards)
            cards_list.append(random_card)
            self.cards.remove(random_card)
        return cards_list

    def get_random_card(self) -> Card:
        return self.get_random_cards(1)[0]

    def give_random_card(self, player: Player, count: int) -> None:
        for random_card in self.get_random_cards(count):
            player.cards.append(random_card)
        player.calculate_card_value()
