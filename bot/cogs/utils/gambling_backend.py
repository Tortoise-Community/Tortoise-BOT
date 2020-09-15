import random

import discord
from bot.constants import red_emotes, black_emotes

face_cards = ["K", "Q", "J"]


class Card(object):
    def __init__(self, suit, name):
        self.suit = suit
        self.name = name
        self.emote = self._get_emoji()

    def show(self):
        print(f"{self.name} of {self.suit}")

    def _get_emoji(self):
        if self.suit in ["Diamond", "Heart"]:
            return red_emotes.get(self.name)
        else:
            return black_emotes.get(self.name)


class Deck:
    def __init__(self):
        self.cards = []
        self.build_deck()
        self.shuffle()

    def build_deck(self):
        suits = ["Club", "Heart", "Diamond", "Spade"]
        cards_set = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "K", "Q", "J"]
        for suit in suits:
            for card in cards_set:
                self.cards.append(Card(suit, card))

    def show(self):
        for card in self.cards:
            card.show()

    def shuffle(self):
        for _ in range(random.randint(1, 9)):
            random.shuffle(self.cards)

    def get_random_cards(self, count):
        cards_list = []
        for i in range(count):
            random_card = random.choice(self.cards)
            cards_list.append(random_card)
            self.cards.remove(random_card)
        return cards_list

    def give_random_card(self, player, count):
        for random_card in self.get_random_cards(count):
            player.cards.append(random_card)
        player.calculate_card_value()


class Player:
    message: discord.Message

    def __init__(self, user_id, bet_amount, game):
        self.user_id = user_id
        self.bet_amount = int(bet_amount)
        self.card_value = 0
        self.cards = []
        self.game = game
        self.stay = False

    def calculate_card_value(self, dealer=False):
        value = 0
        a_count = 0
        for card in self.cards:
            if card.name == "A":
                a_count += 1
            elif card.name in face_cards:
                value += 10
            else:
                value += int(card.name)
        if not dealer:
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

    def get_emote_string(self, hidden=True):
        if not hidden:
            emote_string = " ".join(card.emote for card in self.cards)
            emote_string += f"\nvalue: {self.card_value}"
            return emote_string
        return f"{self.cards[0].emote} + ?\nvalue: ?"


class Game(Player):
    def __init__(self, channel):  # noqa
        self.channel = channel
        self.participants = {}
        self.deck = Deck()
        self.cards = self.deck.get_random_cards(2)
        self.card_value = self.calculate_card_value()
