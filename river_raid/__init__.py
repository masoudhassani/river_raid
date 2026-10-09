import os

os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')

import gymnasium as gym  # noqa: E402

from .game import CovidRaid, RiverRaid  # noqa: E402
from .env import RiverRaidEnv  # noqa: E402

gym.register(id='RiverRaid-v1', entry_point='river_raid.env:RiverRaidEnv')

__all__ = ['RiverRaid', 'CovidRaid', 'RiverRaidEnv']
