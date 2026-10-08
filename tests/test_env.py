import numpy as np
import pytest
from gymnasium.utils.env_checker import check_env

from river_raid import RiverRaid, RiverRaidEnv


def rollout(env, seed, steps=300):
    obs, _ = env.reset(seed=seed)
    rng = np.random.default_rng(0)
    trace = []
    for _ in range(steps):
        obs, reward, terminated, truncated, info = env.step(int(rng.integers(env.action_space.n)))
        trace.append((int(obs.sum()), reward))
        if terminated or truncated:
            break
    return trace


def test_gymnasium_api():
    check_env(RiverRaidEnv(), skip_render_check=True)


def test_observation():
    env = RiverRaidEnv(obs_size=84, frame_stack=3)
    obs, info = env.reset(seed=0)
    assert obs.shape == (3, 84, 84) and obs.dtype == np.uint8
    assert info['fuel'] == 1.0
    # fuel gauge: full tank -> bottom rows are white
    assert (obs[-1, -2:] == 255).all()


def test_seeding_is_deterministic():
    assert rollout(RiverRaidEnv(), 7) == rollout(RiverRaidEnv(), 7)
    assert rollout(RiverRaidEnv(), 7) != rollout(RiverRaidEnv(), 8)


def test_crashing_into_the_bank_terminates_with_penalty():
    env = RiverRaidEnv(death_penalty=1.0)
    env.reset(seed=0)
    for _ in range(500):
        _, reward, terminated, truncated, _ = env.step(1)   # keep flying left
        if terminated:
            break
    assert terminated and not truncated
    assert reward <= -1.0


def test_truncation():
    env = RiverRaidEnv(max_episode_frames=40, frame_skip=4)
    env.reset(seed=0)
    for i in range(10):
        _, _, terminated, truncated, info = env.step(0)
    assert truncated and not terminated and info['frames'] == 40


def test_unfired_bullet_does_not_kill():
    game = RiverRaid(preset='AI', num_lives=1, seed=0)
    enemy = game._spawn('helicopter', 'enemy', list(game.player.pos))
    enemy.set_walls(game.walls.return_wall_coordinate(0))
    game.enemies.append(enemy)
    game.bullet.update('NO_MOVE', game.player.pos)
    game.enemy_collision()
    # the plane crashed into the helicopter, it was not shot by the bullet sitting under the plane
    assert not game.player.alive and game.kills == 0


@pytest.mark.parametrize('random_assets', [True, False])
def test_game_runs(random_assets):
    game = RiverRaid(preset='AI', random=random_assets, num_lives=1, seed=1)
    for i in range(2000):
        game.step(i % 6)
        if not game.is_running:
            break
    assert game.frame > 0
