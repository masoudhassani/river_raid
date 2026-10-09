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
    env = RiverRaidEnv(death_penalty=2.0)
    env.reset(seed=0)
    for _ in range(500):
        _, reward, terminated, truncated, _ = env.step(1)   # keep flying left
        if terminated:
            break
    assert terminated and not truncated
    assert reward < -1.9


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


def test_reward_terms():
    env = RiverRaidEnv(survival_reward=0.01, reversal_penalty=0.05, reversal_window=4, frame_skip=1)
    env.reset(seed=0)
    alive = 0.01
    assert env.step(0)[1] == pytest.approx(alive)            # fly straight: survival only
    assert env.step(1)[1] == pytest.approx(alive)            # start steering left: free
    assert env.step(1)[1] == pytest.approx(alive)            # keep steering left: free
    assert env.step(0)[1] == pytest.approx(alive)            # stop: free
    assert env.step(2)[1] == pytest.approx(alive - 0.05)     # quick left -> right reversal: penalized
    for _ in range(5):
        env.step(0)
    assert env.step(1)[1] == pytest.approx(alive)            # deliberate turn after a pause: free


def test_ramming_an_enemy_is_not_rewarded():
    env = RiverRaidEnv(death_penalty=2.0, frame_skip=1)
    env.reset(seed=0)
    game = env.game
    enemy = game._spawn('helicopter', 'enemy', [game.player.pos[0], game.player.pos[1] - 10])
    enemy.set_walls(game.walls.return_wall_coordinate(0))
    game.enemies.append(enemy)
    _, reward, terminated, _, info = env.step(0)
    assert terminated and info['score'] == 60       # the game still shows the points
    assert reward == pytest.approx(-2.0)            # but the agent only gets the death penalty


def test_escaped_enemy_is_penalized():
    env = RiverRaidEnv(escape_penalty=0.5, survival_reward=0.0, frame_skip=1)
    env.reset(seed=0)
    game = env.game
    game.enemies.clear()
    # a helicopter just about to leave the bottom of the screen, away from the plane
    enemy = game._spawn('helicopter', 'enemy', [210, game.settings['height'] - 2])
    enemy.set_walls(game.walls.return_wall_coordinate(0))
    game.enemies.append(enemy)
    rewards = [env.step(0)[1] for _ in range(2)]
    assert game.escaped == 1 and env._info()['escaped'] == 1
    assert sum(rewards) == pytest.approx(-0.5)
    # a shot-down enemy that scrolls off the screen is not an escape
    dead = game._spawn('ship', 'enemy', [300, game.settings['height'] - 2])
    dead.alive = False
    game.enemies.append(dead)
    env.step(0); env.step(0)
    assert game.escaped == 1


def test_resume_accepts_checkpoints_without_new_settings(tmp_path):
    from river_raid.rl.ppo import parse_args, train
    import torch
    common = ['--num-envs', '2', '--num-steps', '16', '--num-workers', '0', '--log-dir', str(tmp_path),
              '--device', 'cpu', '--save-every', '1', '--channels', '8,8,8']
    run_dir = train(parse_args(['--total-steps', '32', '--run-name', 'old', *common]))
    ckpt = torch.load(f'{run_dir}/latest.pt', weights_only=False)
    del ckpt['config']['escape_penalty']          # like a checkpoint written before the option existed
    torch.save(ckpt, f'{run_dir}/latest.pt')
    train(parse_args(['--total-steps', '64', '--resume', f'{run_dir}/latest.pt', *common]))


def test_fast_observation_matches_full_resolution_rendering():
    # identical except along the slanted river banks, where the two rasterize lines differently
    env = RiverRaidEnv()
    env.reset(seed=4)
    rng = np.random.default_rng(4)
    for _ in range(300):
        _, _, terminated, truncated, _ = env.step(int(rng.integers(env.action_space.n)))
        diff = np.abs(env.game.observation().astype(int) - env.game.observation_full_res().astype(int))
        assert diff.max() <= 16 and (diff > 0).mean() < 0.02
        if terminated or truncated:
            env.reset()


def test_clean_observation_style():
    env = RiverRaidEnv(obs_style='clean')
    env.reset(seed=0)
    game = env.game
    game.enemies.clear(); game.fuels.clear()
    enemy = game._spawn('helicopter', 'enemy', [380, 200])
    enemy.set_walls(game.walls.return_wall_coordinate(0))
    game.enemies.append(enemy)
    frame = game.observation(style='clean')
    water = frame[10:20, 40:56]
    assert (water == RiverRaid.CLEAN['water']).all()
    # the helicopter stands out from the black water
    assert frame[30:40, 40:56].max() > 150


@pytest.mark.parametrize('fuel, expected', [(0.3, -1.0), (0.9, 1.6)])   # needed tank: no points, penalty
def test_shooting_a_needed_fuel_tank_is_penalized(fuel, expected):
    env = RiverRaidEnv(reward_scale=0.02, survival_reward=0.0, refuel_below=0.6, low_fuel_shot_penalty=1.0,
                       frame_skip=1)
    env.reset(seed=0)
    game = env.game
    game.enemies.clear(); game.fuels.clear()
    game.player.fuel = fuel * game.player.capacity
    tank = game._spawn('fuel', 'fuel', [game.player.pos[0], 300])
    tank.set_walls(game.walls.return_wall_coordinate(0))
    game.fuels.append(tank)
    game.bullet.state = 'fired'
    game.bullet.pos = [game.player.pos[0] + 13, 300 + 40]
    _, reward, *_ , info = env.step(0)
    assert info['tanks_shot'] == 1
    assert reward == pytest.approx(expected)


def ghost_run(game, frames):
    '''advance the game with an invulnerable plane, calling back every frame'''
    for _ in range(frames):
        game.player.fuel = game.player.capacity
        game.player.alive, game.lives_left, game.is_running = True, 1, True
        game.player.pos[0] = 386
        game.step('NO_MOVE')
        yield game


def test_river_has_45_degree_ramps_and_varied_channel_spacing():
    game = RiverRaid(preset='AI', num_lives=1, seed=3)
    widths, wide_stretches = set(), set()
    for g in ghost_run(game, 6000):
        banks = [g.walls.return_wall_coordinate(y)[0] for y in range(0, 600)]
        assert max(abs(a - b) for a, b in zip(banks, banks[1:])) <= 1     # never steeper than 45 degrees
        widths.update(banks)
        wide_stretches.update(end - start for start, end, b0, b1 in g.walls.pieces if b0 == b1 == 200)
    assert {200, 350} <= widths and len(widths) > 100                     # wide, narrow and ramps between
    assert len(wide_stretches) > 3                                       # channel spacing varies


def test_enemies_and_fuel_tanks_stay_in_the_river():
    game = RiverRaid(preset='AI', num_lives=1, seed=5)
    game.enemy_collision = game.wall_collision = lambda: None
    checked = 0
    for g in ghost_run(game, 8000):
        for obj in [e for e in g.enemies if e.alive] + g.fuels:
            lo, hi = g.walls.narrowest(obj.pos[1], obj.pos[1] + obj.cg[1])
            # moving enemies turn after touching a bank, so they may reach 4 px into it
            assert lo - 4 <= obj.pos[0] and obj.pos[0] + obj.cg[0] <= hi + 4
            checked += 1
    assert checked > 10000
