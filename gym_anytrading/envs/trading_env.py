import gym
from gym import spaces
from gym.utils import seeding
import numpy as np
from enum import Enum
import matplotlib.pyplot as plt
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from sklearn import preprocessing, model_selection, feature_selection, ensemble, linear_model, metrics, decomposition

class Actions(Enum):
    Sell = 0
    Buy = 1
    Hold = 2


class Positions(Enum):
    Low = 0
    Middle = 5
    High = 10

    #def opposite(self):
    #    return Positions.Short if self == Positions.Long else Positions.Long


class TradingEnv(gym.Env):

    metadata = {'render.modes': ['human']}

    def __init__(self, df, window_size):
        assert df.ndim == 2

        self.seed()
        self.df = df
        self.window_size = window_size
        self.prices, self.signal_features = self._process_data()
        self.shape = (window_size, self.signal_features.shape[1])

        # spaces
        self.action_space = spaces.Discrete(len(Actions))
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=self.shape, dtype=np.float32)

        # episode
        self._start_tick = self.window_size
        self._end_tick = len(self.prices) - 1
        self._done = None
        self._current_tick = None
        self._last_trade_tick = None
        self._position = None
        self._position_history = None
        self._total_reward = None
        self._total_value = None
        self._pocket = None
        self._first_rendering = None
        self.history = None


    def seed(self, seed=None):
        self.np_random, seed = seeding.np_random(seed)
        return [seed]


    def reset(self):
        self._done = False
        self._current_tick = self._start_tick
        self._last_trade_tick = self._current_tick - 1
        self._position = Positions.Low
        self._position_history = (self.window_size * [None]) + [self._position]
        self._total_reward = 0.
        self._total_value = 0.  # unit
        self._pocket = 100000. #starting 'cash' in pocket
        self._first_rendering = True
        self.history = {}
        return self._get_observation()


    def step(self, action):
        self._done = False
        # by increasing tick, it moves to next price right?
        self._current_tick += 1

        if self._current_tick == self._end_tick:
            self._done = True

        # pull next obs. to see if action was good or bad ??
        #already did this by updating _current_tick
        #observation = self._get_observation()
        step_reward = self._calculate_reward(action)
        self._total_reward += step_reward

        self._update_value(action)

        trade = False
        if ((action == Actions.Buy.value and self._position == Positions.Low)):
            trade = True
            #self._position = Positions.High

        if ((action == Actions.Sell.value and self._position == Positions.High)):
            trade = True
            #self._position = Positions.Low

        if trade:
            #self._position = self._position.opposite()
            self._last_trade_tick = self._current_tick

        self._position_history.append(self._position)
        observation = self._get_observation()
        info = dict(
            total_reward = self._total_reward,
            total_value = self._total_value,
            position = self._position.value,
            action = action
        )
        self._update_history(info)

        return observation, step_reward, self._done, info


    def _get_observation(self):
        return self.signal_features[(self._current_tick-self.window_size):self._current_tick]


    def _update_history(self, info):
        if not self.history:
            self.history = {key: [] for key in info.keys()}

        for key, value in info.items():
            self.history[key].append(value)


    def render(self, mode='human'):

        def _plot_position(position, tick):
            color = None
            if position == Positions.Low:
                color = 'yellow'
            elif position == Positions.High:
                color = 'blue'
            if color:
                plt.scatter(tick, self.prices[tick], color=color)

        if self._first_rendering:
            self._first_rendering = False
            plt.cla()
            plt.plot(self.prices)
            start_position = self._position_history[self._start_tick]
            _plot_position(start_position, self._start_tick)

        _plot_position(self._position, self._current_tick)

        plt.suptitle(
            "Total Reward: %.6f" % self._total_reward + ' ~ ' +
            "Total Value: %.6f" % self._total_value
        )

        plt.pause(0.01)


    def render_all_old(self, mode='human'):
        window_ticks = np.arange(len(self._position_history))
        window_ticks-=0
        plt.plot(self.prices)

        short_ticks = []
        long_ticks = []
        for i, tick in enumerate(window_ticks):
            if self._position_history[i] == Positions.Low:
                short_ticks.append(tick)
            elif self._position_history[i] == Positions.High:
                long_ticks.append(tick)

        plt.plot(short_ticks, self.prices[short_ticks], 'ro')
        plt.plot(long_ticks, self.prices[long_ticks], 'go')

        plt.suptitle(
            "Total Reward: %.6f" % self._total_reward + ' ~ ' +
            "Total Value: %.6f" % self._total_value
        )
    
    def render_all(self, mode='human'):
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=self.df.index, y=self.df['Low']))
        fig.add_trace(go.Scatter(x=self.df.index, y=self.df['High'],fill='tonexty'))
        fig.add_trace(go.Scatter(x=self.df.index, y=self.df['Adj Close']))
        fig.update_xaxes(title='Price')
        fig.show()
        
    def close(self):
        plt.close()


    def save_rendering(self, filepath):
        plt.savefig(filepath)


    def pause_rendering(self):
        plt.show()


    def _process_data(self):
        raise NotImplementedError


    def _calculate_reward(self, action):
        raise NotImplementedError


    def _update_value(self, action):
        raise NotImplementedError


    def max_possible_value(self):  # trade fees are ignored
        raise NotImplementedError
