"""Watch a trained agent play, or record a video/gif of it.

    python watch.py runs/<run>/best.pt
    python watch.py runs/<run>/best.pt --record media/agent.gif --episodes 1
"""
import argparse

import numpy as np
import torch

from river_raid.env import RiverRaidEnv
from river_raid.rl.ppo import load_agent


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('checkpoint')
    parser.add_argument('--episodes', type=int, default=3)
    parser.add_argument('--sample', action='store_true',
                        help='sample actions from the policy instead of always taking the most likely one '
                             '(more random, twitchier steering)')
    parser.add_argument('--record', default='', help='save a .gif/.mp4 instead of opening a window')
    parser.add_argument('--video-fps', type=float, default=15,
                        help='one video frame per agent step (4 game frames), 15 fps = 2x real time')
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--sound', action='store_true')
    args = parser.parse_args()

    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    agent, cfg = load_agent(args.checkpoint, device)
    env_kwargs = cfg.env_kwargs()
    env_kwargs['max_episode_frames'] = 10**9   # let it play until it crashes
    env = RiverRaidEnv(render_mode='rgb_array' if args.record else 'human', sound=args.sound, **env_kwargs)

    frames, scores = [], []
    obs, info = env.reset(seed=args.seed)
    for episode in range(args.episodes):
        done = False
        while not done:
            with torch.no_grad():
                action, _, _ = agent.act(torch.from_numpy(obs).unsqueeze(0).to(device), greedy=not args.sample)
            obs, _, terminated, truncated, info = env.step(action.item())
            done = terminated or truncated
            if args.record:
                frames.append(env.render()[::2, ::2])   # half resolution keeps files small
        scores.append(info['score'])
        print('episode {}: score {}, survived {:.1f} minutes, {} kills, {:.1f} km'.format(
            episode + 1, info['score'], info['frames'] / 30 / 60, info['kills'], info['travel'] / 1000))
        obs, info = env.reset()
    print('average score {:.0f}'.format(np.mean(scores)))
    env.close()

    if args.record:
        import imageio.v2 as imageio
        imageio.mimsave(args.record, frames, duration=1000 / args.video_fps, loop=0)
        print('saved', args.record)


if __name__ == '__main__':
    main()
