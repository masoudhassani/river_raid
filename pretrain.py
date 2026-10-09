"""Teach the agent to imitate the scripted expert (river_raid/expert.py) before PPO.

PPO from scratch learns to sit in the middle of the river and shoot: it never discovers that
chasing enemies pays, so its network never even learns to react to them. Starting PPO from a
network that already imitates a player who hunts enemies and refuels fixes that.

    python pretrain.py --obs-style clean --survival-reward 0.0025 --reward-scale 0.02 --escape-penalty 0.5
    python train.py --init-from runs/pretrain.pt --obs-style clean --survival-reward 0.0025 --reward-scale 0.02 --escape-penalty 0.5

All train.py options are accepted, so the network, the observation and the reward (used to
pre-train the value head) match the PPO run. Use the same options for both commands.
"""
import argparse
import dataclasses
import os
import time

import numpy as np
import torch
from torch import nn

from river_raid.env import RiverRaidEnv
from river_raid.game import ACTIONS
from river_raid.expert import Expert
from river_raid.rl.network import ActorCritic
from river_raid.rl.ppo import RewardNormalizer, parse_args


def collect(env_kwargs, steps, seed, random_actions=0.1):
    '''play the expert (with some random actions, so mistakes and their fixes are in the data)'''
    env = RiverRaidEnv(**env_kwargs)
    expert, rng = Expert(), np.random.default_rng(seed)
    obs, _ = env.reset(seed=seed)
    observations = np.zeros((steps, *env.observation_space.shape), np.uint8)
    actions = np.zeros(steps, np.int64)
    rewards, dones = np.zeros(steps), np.zeros(steps, bool)
    for i in range(steps):
        actions[i] = expert.action(env.game)
        observations[i] = obs
        played = actions[i] if rng.random() > random_actions else int(rng.integers(env.action_space.n))
        obs, rewards[i], terminated, truncated, _ = env.step(played)
        dones[i] = terminated or truncated
        if dones[i]:
            obs, _ = env.reset()
            expert.reset()
    env.close()
    return observations, actions, rewards, dones


def value_targets(rewards, dones, gamma):
    '''discounted returns in the units PPO's value head uses (divided by the return std)'''
    normalizer = RewardNormalizer(1, gamma)
    for r, d in zip(rewards, dones):
        normalizer(np.array([r]), np.array([d]))
    returns, g = np.zeros(len(rewards), np.float32), 0.0
    for i in reversed(range(len(rewards))):
        g = rewards[i] + gamma * g * (not dones[i])
        returns[i] = g
    return returns / np.sqrt(normalizer.var + 1e-8), normalizer


def evaluate(agent, env_kwargs, device, episodes=5, max_minutes=5):
    env = RiverRaidEnv(**{**env_kwargs, 'max_episode_frames': int(max_minutes * 1800)})
    stats = []
    for ep in range(episodes):
        obs, _ = env.reset(seed=10_000 + ep)
        while True:
            with torch.no_grad():
                action = agent.act(torch.from_numpy(obs).unsqueeze(0).to(device), greedy=True)[0].item()
            obs, _, terminated, truncated, info = env.step(action)
            if terminated or truncated:
                break
        stats.append((info['frames'] / 1800, info['kills'], info['escaped']))
    minutes, kills, escaped = np.mean(stats, 0)
    print('imitation agent: {:.2f} minutes, {:.1f} kills, {:.0%} of enemies killed'.format(
        minutes, kills, kills / max(1, kills + escaped)))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--demo-steps', type=int, default=200_000,
                        help='agent steps of expert play to imitate (each takes 37 KB of RAM)')
    parser.add_argument('--epochs', type=int, default=5)
    parser.add_argument('--batch-size', type=int, default=256)
    parser.add_argument('--out', default='runs/pretrain.pt')
    parser.add_argument('--eval-episodes', type=int, default=5, help='episodes to evaluate the result on')
    args, rest = parser.parse_known_args(argv)
    cfg = parse_args(rest)
    device = torch.device('cuda' if cfg.device == 'auto' and torch.cuda.is_available() else
                          ('cpu' if cfg.device == 'auto' else cfg.device))
    torch.manual_seed(cfg.seed)

    start = time.time()
    observations, actions, rewards, dones = collect(cfg.env_kwargs(), args.demo_steps, cfg.seed)
    targets, normalizer = value_targets(rewards, dones, cfg.gamma)
    print('{:,} steps of expert play in {:.0f} s'.format(args.demo_steps, time.time() - start), flush=True)

    obs_shape = observations.shape[1:]
    agent = ActorCritic(obs_shape, len(ACTIONS), **cfg.network_kwargs()).to(device)
    optimizer = torch.optim.Adam(agent.parameters(), lr=5e-4)
    use_bf16 = cfg.bf16 and device.type == 'cuda'
    actions_t, targets_t = torch.from_numpy(actions), torch.from_numpy(targets)
    for epoch in range(args.epochs):
        perm = torch.randperm(len(actions))
        total = 0.0
        for s in range(0, len(perm), args.batch_size):
            idx = perm[s:s + args.batch_size]
            obs = torch.from_numpy(observations[idx.numpy()]).to(device)
            with torch.autocast('cuda', torch.bfloat16, enabled=use_bf16):
                logits, value = agent(obs)
            imitation = nn.functional.cross_entropy(logits.float(), actions_t[idx].to(device))
            loss = imitation + 0.5 * ((value.float() - targets_t[idx].to(device)) ** 2).mean()
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            optimizer.step()
            total += imitation.item() * len(idx)
        print('epoch {}: imitation loss {:.3f}'.format(epoch + 1, total / len(perm)), flush=True)

    os.makedirs(os.path.dirname(args.out) or '.', exist_ok=True)
    # the same format as a training checkpoint, so watch.py and train.py --init-from accept it
    torch.save({'model': agent.state_dict(), 'reward_norm': normalizer.state_dict(),
                'config': dataclasses.asdict(cfg), 'obs_shape': obs_shape, 'num_actions': len(ACTIONS)}, args.out)
    print('saved', args.out)
    agent.eval()
    if args.eval_episodes:
        evaluate(agent, cfg.env_kwargs(), device, args.eval_episodes)


if __name__ == '__main__':
    main()
