import logging
import sys

import betting
from static_hole import strategy
import utils

logger = logging.getLogger()


class HoldemBot(object):
    def __init__(self):
        self.round = 0
        self.settings = {}
        self.match = {'amount_to_call': 0, 'big_blind': 0, 'small_blind': 0}
        self.hole = []
        self.table = []
        self.win_percent = 0
        self.players = {"player1": {}, "player2": {}}

        self.hole_strategy = strategy.StaticHoleStrategy()
        self.table_strategy = betting.TableStrategy()

    def output(self, line, action):
        logger.debug("Responding to {} with {}".format(line, action))
        sys.stdout.write(action + "\n")
        sys.stdout.flush()

    def handle_settings(self, line):
        self.settings[line[1]] = line[2]
        logger.debug("Settings: {}".format(self.settings))

    def handle_match(self, line):
        if line[1] == "round":
            # Start of a round, reinitialize
            self.start_match(line)
        elif line[1] in ("amount_to_call", "big_blind", "small_blind"):
            self.match[line[1]] = int(line[2])
        else:
            self.match[line[1]] = line[2]
        logger.debug("Saving match: {}".format(line))

    def start_match(self, line):
        self.round = line[2]
        self.hole = []
        self.table = []
        # self.match = {}
        self.win_percent = 0
        logger.info("===============Starting round {}=================".format(
            self.round))

    def handle_info(self, line):
        logger.debug("Info: {}".format(line))
        if line[1] == "hand":
            # Init bets
            self.match['round_bets'] = 0
            self._parse_hand(line[2])
            self.win_percent = float(
                self.hole_strategy.get_win_percentage(self.hole))
            logger.info("Estimated win percentage: {}".format(
                self.win_percent))
        elif line[1] in ["post", "stack"]:
            self.players[line[0]][line[1]] = line[2]
        elif line[1] == "table":
            # Reset bets
            self.match['round_bets'] = 0
            self._parse_table(line[2])
            self.hand = utils.highest_hand(self.hole, self.table)
            self.highest_hand = utils.highest_hand(self.hole, self.table,
                                                   self.hand)
        elif line[0] == "player1" and line[1] == "raise":
            self.match['raise'] = line[2]

    def handle_action(self, line):
        logger.debug("Action: {}".format(line))
        if self.hole and not self.table:
            multiplier = self.hole_strategy.get_multiplier(self.hole)
            max_bet = int(self.match.get('big_blind', '20')) * multiplier
            self.bet(line, max_bet=max_bet)
        elif self.hole and self.table:
            multiplier = self.table_strategy.get_table_multiplier(
                self.hole, self.table, self.hand)
            max_bet = int(self.match.get('big_blind', '20')) * multiplier
            self.bet(line, max_bet=max_bet)
        else:
            logger.error("Defaulting to check 0")
            self.output(line, "check 0")

    def bet(self, line, max_bet=0):
        """Decide how much to bet

        If no max bet, check if possible
        If the total bet would be more than max_bet, fold
        If amount to total bet so far + call is close to max_bet, call (hide some of our betting strategy
            and prevent a re-raise)
        Else, raise to max bet

        :return:
        """
        # What calling will put the total pot at
        amount_to_call = int(self.match['amount_to_call'])
        if_call_total = amount_to_call + self.match['round_bets']
        max_raise = max_bet - self.match['round_bets']

        if not max_bet:
            logger.info("Checking, no max bet")
            self.output(line, "call 0")
        elif if_call_total > max_bet:
            logger.info("Amount to raise {} would put us over max bet {}".format(amount_to_call, max_bet))
            self.output(line, "fold 0")
        elif max_raise - amount_to_call < amount_to_call * 2 or max_raise < self.match['big_blind']:
            logger.info("Rounding raise {} down to a call".format(max_raise))
            self.output(line, "call 0")
        else:
            logger.info("Raising {}".format(max_raise))
            self.output(line, "raise {}".format(max_raise))
            self.match['round_bets'] += max_raise

    def _parse_hand(self, hand):
        self.hole = []
        if utils.FACE_VALUE[hand[1]] <= utils.FACE_VALUE[hand[4]]:
            self.hole.append((hand[1], hand[2]))
            self.hole.append((hand[4], hand[5]))
        else:
            self.hole.append((hand[4], hand[5]))
            self.hole.append((hand[1], hand[2]))

    def _parse_table(self, table):
        self.table[0] = (table[1], table[2])
        self.table[1] = (table[4], table[5])
        self.table[2] = (table[7], table[8])
        if len(table) >= 12:
            self.table[3] = (table[10], table[11])
        if len(table) == 14:
            self.table[4] = (table[13], table[14])
        logger.debug("Table: {}".format(self.table))

    def run(self):
        logger.debug("Starting up!")
        while not sys.stdin.closed:
            try:
                raw_line = sys.stdin.readline()
                if not raw_line:
                    continue
                line = raw_line.split()
                # logger.debug("Line: {}".format(line))
                # Basic sanity check
                if len(line) != 3:
                    logger.error("Invalid input: {}".format(raw_line))

                # Dispatch based on action type
                if line[0] == "Action":
                    self.handle_action(line)
                elif line[0] == "Settings":
                    self.handle_settings(line)
                elif line[0] == "Match":
                    self.handle_match(line)
                elif line[0] in ["player1", "player2"]:
                    self.handle_info(line)
                else:
                    logger.info("Unhandled line: {}".format(raw_line))
            except Exception as e:
                logger.exception("Handling line failed: {}".format(raw_line))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--debug":
        logging.basicConfig(filename="../bot.log", level=logging.DEBUG)
    else:
        logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
    bot = HoldemBot()
    bot.run()
