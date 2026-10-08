"""Gymnasium environment for River Raid."""
import gymnasium as gym
import numpy as np
from gymnasium import spaces

from .game import ACTIONS, RiverRaid


class RiverRaidEnv(gym.Env):
    '''
    Observation: the last `frame_stack` grayscale frames, uint8 array of shape
                 (frame_stack, obs_size, obs_size). The bottom two rows of every frame
                 are overwritten with a fuel gauge, so the agent knows how much fuel is left.
    Actions:     NO_MOVE, LEFT, RIGHT, LEFT_SHOOT, RIGHT_SHOOT, SHOOT
                 each action is repeated for `frame_skip` game frames.
    Reward:      (game score delta) * reward_scale
                 + refuel_reward per frame while refueling a tank that is not full
                 - death_penalty when the plane crashes or runs out of fuel
    Episode:     ends when the plane is destroyed (one life), truncated after
                 max_episode_frames game frames.
    '''
    metadata = {'render_modes': ['human', 'rgb_array'], 'render_fps': RiverRaid.FPS}

    def __init__(self, render_mode=None, frame_skip=4, frame_stack=4, obs_size=96,
                 max_episode_frames=54_000, reward_scale=0.01, refuel_reward=0.15,
                 death_penalty=1.0, fuel_gauge=True, random_assets=True,
                 enemy_spawn=160, prop_spawn=150, fuel_spawn=500, sound=False):
        assert render_mode is None or render_mode in self.metadata['render_modes']
        self.render_mode = render_mode
        self.frame_skip = frame_skip
        self.frame_stack = frame_stack
        self.obs_size = (obs_size, obs_size)
        self.max_episode_frames = max_episode_frames
        self.reward_scale = reward_scale
        self.refuel_reward = refuel_reward
        self.death_penalty = death_penalty
        self.fuel_gauge = fuel_gauge

        self.game = RiverRaid(preset='AI', render_mode='human' if render_mode == 'human' else None,
                              random=random_assets, init_enemy_spawn=enemy_spawn,
                              init_prop_spawn=prop_spawn, init_fuel_spawn=fuel_spawn,
                              sound=sound, num_lives=1)

        self.action_space = spaces.Discrete(len(ACTIONS))
        self.observation_space = spaces.Box(0, 255, (frame_stack, obs_size, obs_size), np.uint8)
        self._frames = np.zeros(self.observation_space.shape, np.uint8)

    @staticmethod
    def action_meanings():
        return list(ACTIONS)

    def _frame(self):
        frame = self.game.observation(self.obs_size)
        if self.fuel_gauge:
            filled = int(round(self.obs_size[1] * self.game.player.fuel / self.game.player.capacity))
            frame[-2:, :filled] = 255
            frame[-2:, filled:] = 0
        return frame

    def _info(self):
        g = self.game
        return {'score': g.score_value, 'travel': g.travel_distance, 'kills': g.kills,
                'fuel': g.player.fuel / g.player.capacity, 'frames': g.frame}

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        self.game.reset(seed=int(self.np_random.integers(2**31)))
        self._frames[:] = self._frame()
        if self.render_mode == 'human':
            self.game.render()
        return self._frames.copy(), self._info()

    def step(self, action):
        game = self.game
        action_name = ACTIONS[int(action)]
        reward = 0.0
        for _ in range(self.frame_skip):
            score = game.score_value
            game.step(action_name)
            reward += (game.score_value - score) * self.reward_scale
            if game.refueling and game.player.fuel < game.player.capacity:
                reward += self.refuel_reward
            if self.render_mode == 'human':
                game.render()
                game.handle_events()
            if not game.is_running:
                break

        terminated = not game.player.alive
        if terminated:
            reward -= self.death_penalty
        truncated = not terminated and (game.frame >= self.max_episode_frames or not game.is_running)

        self._frames[:-1] = self._frames[1:]
        self._frames[-1] = self._frame()
        return self._frames.copy(), reward, terminated, truncated, self._info()

    def render(self):
        if self.render_mode == 'rgb_array':
            return self.game.rgb_array()
        if self.render_mode == 'human':
            self.game.render()

    def close(self):
        self.game.close()
