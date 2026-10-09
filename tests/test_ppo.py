import numpy as np
import torch

from river_raid.rl.network import ActorCritic
from river_raid.rl.ppo import RewardNormalizer, load_agent, parse_args, train
from river_raid.rl.vec_env import VecEnv


def test_network_shapes():
    net = ActorCritic((4, 96, 96), 6)
    obs = torch.randint(0, 255, (5, 4, 96, 96), dtype=torch.uint8)
    action, logprob, value = net.act(obs)
    assert action.shape == logprob.shape == value.shape == (5,)


def test_vec_env_autoreset():
    envs = VecEnv(4, num_workers=0, env_kwargs={'max_episode_frames': 40})
    obs = envs.reset()
    assert obs.shape == (4, 4, 96, 96)
    finished = []
    for _ in range(12):
        obs, rewards, terminated, truncated, eps = envs.step(np.zeros(4, dtype=int))
        finished += eps
    assert len(finished) >= 4
    assert all(ep['final_obs'] is not None for ep in finished if ep['truncated'])
    envs.close()


def test_subprocess_vec_env_matches_inprocess():
    a = VecEnv(4, num_workers=2, seed=3)
    b = VecEnv(4, num_workers=0, seed=3)
    try:
        assert (a.reset() == b.reset()).all()
        for i in range(20):
            actions = np.full(4, i % 6)
            oa, ra, *_ = a.step(actions)
            ob, rb, *_ = b.step(actions)
            assert (oa == ob).all() and (ra == rb).all()
    finally:
        a.close()
        b.close()


def test_reward_normalizer():
    norm = RewardNormalizer(2, 0.99)
    out = norm(np.array([1.0, -1.0]), np.array([False, True]))
    assert out.shape == (2,) and np.isfinite(out).all()


def test_train_and_reload(tmp_path):
    cfg = parse_args(['--total-steps', '256', '--num-envs', '4', '--num-steps', '32', '--num-workers', '0',
                      '--log-dir', str(tmp_path), '--run-name', 't', '--device', 'cpu', '--channels', '8,8,8'])
    run_dir = train(cfg)
    agent, loaded_cfg = load_agent(f'{run_dir}/latest.pt')
    assert loaded_cfg.channels == '8,8,8'
    action, _, _ = agent.act(torch.zeros((1, 4, 96, 96), dtype=torch.uint8), greedy=True)
    assert 0 <= action.item() < 6


def test_resume_uses_checkpoint_architecture(tmp_path):
    common = ['--num-envs', '4', '--num-steps', '32', '--num-workers', '0', '--log-dir', str(tmp_path),
              '--device', 'cpu', '--save-every', '1']
    run_dir = train(parse_args(['--total-steps', '128', '--run-name', 'a', '--channels', '8,8,8', *common]))
    # resume without repeating --channels
    train(parse_args(['--total-steps', '256', '--resume', f'{run_dir}/latest.pt', *common]))
    ckpt = torch.load(f'{run_dir}/latest.pt', weights_only=False)
    assert ckpt['config']['channels'] == '8,8,8' and ckpt['global_step'] == 256
