import numpy as np
from sklearn import preprocessing, model_selection, feature_selection, ensemble, linear_model, metrics, decomposition
import pandas as pd

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
        diff = np.insert(np.diff(prices/100.), 0, 0)

        #convert signal_features into normalized 0 - 1 data
        
        signal_features = np.column_stack((prices, diff))

        min_max_scaler = preprocessing.MinMaxScaler(feature_range=(0,1))
        signal_features_norm = min_max_scaler.fit_transform(signal_features)

        return prices, signal_features_norm

    #calculate the delta reward based on current action
    # and the next step
    def _calculate_reward(self, action):
        stp_reward = 0.
        price_diff = 0.
        buy_cost =0.
        price_diff_percent = 0.
        trade = False
        current_price = self.prices[self._current_tick]
        #last_trade_price = self.prices[self._last_trade_tick]
        price_diff = current_price - self.prices[self._current_tick-1]
        price_diff_percent = price_diff / (0.5*self.prices[self._current_tick] + 0.5*self.prices[self._current_tick-1]) * 100.
        buy_cost = 9. * current_price
        #print(buy_cost)
        #below should move position up down or stay same before calc dtreward
        #also diff reward for different actions?
        if ((action == Actions.Buy.value and self._position == Positions.Low)):
            trade = True
            self._position = Positions.High
            self._pocket  -= buy_cost
            if (price_diff >= 0.0):
                stp_reward = 1.
            else:
                stp_reward = -1.

        if ((action == Actions.Sell.value and self._position == Positions.High)):
            trade = True
            self._position = Positions.Low
            self._pocket += buy_cost
            if (price_diff <= 0.0):
                stp_reward = 1.
            else:
                stp_reward = -1.
            #need to calculate how much made / lost since last .Low
            #self._pocket = current_price - price at last buy

        if ((action == Actions.Hold.value)):
            trade = False
            if (price_diff >= 0.0 and self._position == Positions.High):
                stp_reward = 0.25
            if (self._position == Positions.Low):
                stp_reward = -0.25
        
        #print(self._pocket)
        self._update_value(action)
        #stp_reward = price_diff*self._position.value / self.prices[self._current_tick] * 100.#*position number

        #need to calculate how much made / lost since last .Low
        #self._pocket = current_price - price at last buy
        #if trade:
        #should be done with averages into the future, or values,
        #into the future for training
        #should maybe add pocket value too?
        #or percent from previous total value i think...
        #actually should be reward for selling before a fall too,
        #as in a 'saved_value' reward bonus...
        #Call _update_value here first
        #%
        #       
        return stp_reward

    #update value
    def _update_value(self, action):
        #my value A * pocket + B * current_price * shares,
        shares = self._position.value
        self._total_value = self._pocket + shares * self.prices[self._current_tick]
