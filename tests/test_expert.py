import numpy as np
import torch

from river_raid import RiverRaidEnv
from river_raid.expert import Expert


def test_expert_hunts_enemies():
    env = RiverRaidEnv(max_episode_frames=1800)
    env.reset(seed=0)
    expert = Expert()
    for _ in range(450):
        action = expert.action(env.game)
        assert 0 <= action < env.action_space.n
        _, _, terminated, truncated, info = env.step(action)
        if terminated or truncated:
            break
    assert info['kills'] >= 5
    assert info['kills'] > info['escaped']


def test_pretrain_writes_a_checkpoint_train_can_start_from(tmp_path):
    import pretrain
    from river_raid.rl.ppo import load_agent, parse_args, train
    common = ['--device', 'cpu', '--channels', '8,8,8', '--obs-style', 'clean']
    out = str(tmp_path / 'pretrain.pt')
    pretrain.main(['--demo-steps', '64', '--epochs', '1', '--out', out, '--eval-episodes', '0', *common])
    agent, cfg = load_agent(out)
    assert cfg.obs_style == 'clean'
    assert agent.act(torch.zeros((1, 4, 96, 96), dtype=torch.uint8))[0].shape == (1,)
    train(parse_args(['--total-steps', '32', '--num-envs', '2', '--num-steps', '16', '--num-workers', '0',
                      '--log-dir', str(tmp_path), '--run-name', 'ft', '--init-from', out, *common]))
