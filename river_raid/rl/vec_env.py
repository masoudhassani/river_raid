"""A small, fast vectorized environment.

Each worker process runs a group of environments and writes observations straight
into shared memory, so only actions, rewards and a few small dicts travel through
pipes. Environments are reset automatically in the same step in which their
episode ends; the stats of finished episodes are returned as a list of dicts.
"""
import multiprocessing as mp
from multiprocessing import shared_memory

import numpy as np


def make_env(env_kwargs):
    from ..env import RiverRaidEnv
    return RiverRaidEnv(**env_kwargs)


class EnvGroup:
    '''several environments stepped one after the other in the same process'''

    def __init__(self, env_kwargs, seeds):
        self.envs = [make_env(env_kwargs) for _ in seeds]
        self.seeds = list(seeds)
        self.returns = np.zeros(len(seeds))
        self.lengths = np.zeros(len(seeds), dtype=np.int64)

    def reset(self, obs):
        for i, (env, seed) in enumerate(zip(self.envs, self.seeds)):
            obs[i], _ = env.reset(seed=seed)
        self.returns[:] = 0
        self.lengths[:] = 0

    def step(self, actions, obs, rewards, terminated, truncated, offset=0):
        finished = []
        for i, (env, action) in enumerate(zip(self.envs, actions)):
            o, r, term, trunc, info = env.step(action)
            self.returns[i] += r
            self.lengths[i] += 1
            if term or trunc:
                finished.append({'env': offset + i, 'return': float(self.returns[i]),
                                 'steps': int(self.lengths[i]), 'score': info['score'],
                                 'kills': info['kills'], 'travel': info['travel'],
                                 'frames': info['frames'], 'truncated': bool(trunc),
                                 # needed to bootstrap the value of truncated episodes
                                 'final_obs': o if trunc else None})
                self.returns[i] = 0
                self.lengths[i] = 0
                o, _ = env.reset()
            obs[i], rewards[i], terminated[i], truncated[i] = o, r, term, trunc
        return finished

    def close(self):
        for env in self.envs:
            env.close()


def _worker(remote, shm_names, num_envs, obs_shape, start, end, env_kwargs, seeds):
    shms = [shared_memory.SharedMemory(name=n) for n in shm_names]
    obs = np.ndarray((num_envs, *obs_shape), np.uint8, buffer=shms[0].buf)[start:end]
    rewards = np.ndarray((num_envs,), np.float32, buffer=shms[1].buf)[start:end]
    terminated = np.ndarray((num_envs,), np.bool_, buffer=shms[2].buf)[start:end]
    truncated = np.ndarray((num_envs,), np.bool_, buffer=shms[3].buf)[start:end]
    group = EnvGroup(env_kwargs, seeds)
    try:
        while True:
            cmd, data = remote.recv()
            if cmd == 'step':
                remote.send(group.step(data, obs, rewards, terminated, truncated, offset=start))
            elif cmd == 'reset':
                group.reset(obs)
                remote.send(None)
            elif cmd == 'close':
                break
    except (KeyboardInterrupt, EOFError):
        pass
    finally:
        group.close()
        del obs, rewards, terminated, truncated
        for shm in shms:
            shm.close()


class VecEnv:
    '''
    num_envs environments spread over num_workers processes.
    num_workers=0 runs everything in the main process (handy for debugging/tests).
    '''

    def __init__(self, num_envs, num_workers=0, seed=0, env_kwargs=None):
        env_kwargs = env_kwargs or {}
        probe = make_env(env_kwargs)
        self.observation_space = probe.observation_space
        self.action_space = probe.action_space
        probe.close()

        self.num_envs = num_envs
        self.num_workers = min(num_workers, num_envs)
        obs_shape = self.observation_space.shape
        seeds = [seed + i for i in range(num_envs)]

        if self.num_workers == 0:
            self.obs = np.zeros((num_envs, *obs_shape), np.uint8)
            self.rewards = np.zeros(num_envs, np.float32)
            self.terminated = np.zeros(num_envs, np.bool_)
            self.truncated = np.zeros(num_envs, np.bool_)
            self.group = EnvGroup(env_kwargs, seeds)
            return

        sizes = [int(np.prod((num_envs, *obs_shape))), num_envs * 4, num_envs, num_envs]
        self._shms = [shared_memory.SharedMemory(create=True, size=s) for s in sizes]
        self.obs = np.ndarray((num_envs, *obs_shape), np.uint8, buffer=self._shms[0].buf)
        self.rewards = np.ndarray((num_envs,), np.float32, buffer=self._shms[1].buf)
        self.terminated = np.ndarray((num_envs,), np.bool_, buffer=self._shms[2].buf)
        self.truncated = np.ndarray((num_envs,), np.bool_, buffer=self._shms[3].buf)

        ctx = mp.get_context('spawn')
        bounds = np.linspace(0, num_envs, self.num_workers + 1).astype(int)
        self.slices = list(zip(bounds[:-1], bounds[1:]))
        self.remotes, self.procs = [], []
        for start, end in self.slices:
            parent, child = ctx.Pipe()
            proc = ctx.Process(target=_worker, daemon=True,
                               args=(child, [s.name for s in self._shms], num_envs, obs_shape,
                                     start, end, env_kwargs, seeds[start:end]))
            proc.start()
            child.close()
            self.remotes.append(parent)
            self.procs.append(proc)

    def reset(self):
        if self.num_workers == 0:
            self.group.reset(self.obs)
        else:
            for remote in self.remotes:
                remote.send(('reset', None))
            for remote in self.remotes:
                remote.recv()
        return self.obs.copy()

    def step(self, actions):
        '''returns obs, rewards, terminated, truncated, list of finished episode dicts'''
        actions = np.asarray(actions)
        if self.num_workers == 0:
            finished = self.group.step(actions, self.obs, self.rewards, self.terminated, self.truncated)
        else:
            for remote, (start, end) in zip(self.remotes, self.slices):
                remote.send(('step', actions[start:end]))
            finished = [ep for remote in self.remotes for ep in remote.recv()]
        return self.obs.copy(), self.rewards.copy(), self.terminated.copy(), self.truncated.copy(), finished

    def close(self):
        if self.num_workers == 0:
            self.group.close()
            return
        for remote in self.remotes:
            try:
                remote.send(('close', None))
            except (BrokenPipeError, EOFError):
                pass
        for proc in self.procs:
            proc.join(timeout=5)
            if proc.is_alive():
                proc.terminate()
        self.obs = self.rewards = self.terminated = self.truncated = None
        for shm in self._shms:
            shm.close()
            shm.unlink()
