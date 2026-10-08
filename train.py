"""Train a PPO agent to play River Raid.

    python train.py                                  # sensible defaults for a single GPU
    python train.py --num-envs 128 --bf16            # more throughput on an RTX 3090
    python train.py --resume runs/<run>/latest.pt    # continue a run
    python train.py --help                           # all options
"""
from river_raid.rl.ppo import main

if __name__ == '__main__':
    main()
