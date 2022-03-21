import numpy as np

from .trading_env import TradingEnv, Actions, Positions


class StocksEnv(TradingEnv):

    def __init__(self, df, window_size, frame_bound):
        assert len(frame_bound) == 2

        self.frame_bound = frame_bound
        super().__init__(df, window_size)

        self.trade_fee_bid_percent = 0.01  # unit
        self.trade_fee_ask_percent = 0.005  # unit


    def _process_data(self):
        prices = self.df.loc[:, 'Close'].to_numpy()

        prices[self.frame_bound[0] - self.window_size]  # validate index (TODO: Improve validation)
        prices = prices[self.frame_bound[0]-self.window_size:self.frame_bound[1]]

        diff = np.insert(np.diff(prices), 0, 0)
        signal_features = np.column_stack((prices, diff))

        return prices, signal_features


    def _calculate_reward(self, action):
        stp_reward = 0
        val_reward = 0 # dt in values in percent or totals
        pkt_reward = 0 # dt in pocket in percent rel to starting?
        price_diff = 0
        trade = False
        #below should move position up down or stay same before calc dtreward
        if ((action == Actions.Buy.value and self._position == Positions.Low)):
            trade = True
            self._position = Positions.High
            self._pocket = self._pocket - 9. * self.prices[self._current_tick]

        if ((action == Actions.Sell.value and self._position == Positions.High)):
            trade = True
            self._position = Positions.Low
            #need to calculate how much made / lost since last .Low
            #self._pocket = current_price - price at last buy

        #if trade:
        current_price = self.prices[self._current_tick]
        last_trade_price = self.prices[self._last_trade_tick]
        price_diff = current_price - last_trade_price

        #my reward A * pocket + B * value, A & B to weight

        #if self._position == Positions.Long:
        stp_reward = price_diff*self._position.value #*position number

        return stp_reward


    def _update_profit(self, action):
        trade = False
        if ((action == Actions.Buy.value and self._position == Positions.Low) or
            (action == Actions.Sell.value and self._position == Positions.High)):
            trade = True

        if trade or self._done:
            current_price = self.prices[self._current_tick]
            last_trade_price = self.prices[self._last_trade_tick]

            #if self._position == Positions.Long:
            #again should be mults by position
            shares = (self._total_profit * (1 - self.trade_fee_ask_percent)) / last_trade_price
            self._total_profit = (shares * (1 - self.trade_fee_bid_percent)) * current_price


    # def max_possible_profit(self):
    #     current_tick = self._start_tick
    #     last_trade_tick = current_tick - 1
    #     profit = 1.

    #     while current_tick <= self._end_tick:
    #         position = None
    #         if self.prices[current_tick] < self.prices[current_tick - 1]:
    #             while (current_tick <= self._end_tick and
    #                    self.prices[current_tick] < self.prices[current_tick - 1]):
    #                 current_tick += 1
    #             position = Positions.Short
    #         else:
    #             while (current_tick <= self._end_tick and
    #                    self.prices[current_tick] >= self.prices[current_tick - 1]):
    #                 current_tick += 1
    #             position = Positions.Long

    #         if position == Positions.Long:
    #             current_price = self.prices[current_tick - 1]
    #             last_trade_price = self.prices[last_trade_tick]
    #             shares = profit / last_trade_price
    #             profit = shares * current_price
    #         last_trade_tick = current_tick - 1

    #     return profit
