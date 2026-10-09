"""PPO (Schulman et al. 2017) for River Raid, in the style of CleanRL's single-file
implementations: IMPALA ResNet encoder, GAE, clipped policy/value losses, advantage
normalization, return-based reward normalization, linear learning-rate annealing and
proper bootstrapping of time-limit truncations."""
import argparse
import dataclasses
import os
import signal
import time
from collections import deque
from dataclasses import dataclass

import numpy as np
import torch
from torch import nn

from .network import ActorCritic
from .vec_env import VecEnv


@dataclass
class Config:
    # experiment
    run_name: str = ''                  # defaults to a timestamp
    log_dir: str = 'runs'
    seed: int = 1
    resume: str = ''                    # path to a checkpoint to continue training from
    device: str = 'auto'                # auto | cuda | cpu
    bf16: bool = False                  # bfloat16 autocast (Ampere GPUs, e.g. RTX 3090)
    compile: bool = False               # torch.compile the network
    save_every: int = 50                # updates between checkpoints

    # PPO
    total_steps: int = 50_000_000       # agent steps (each is frame_skip game frames)
    num_envs: int = 64
    num_workers: int = -1               # env processes, -1: number of CPU cores - 1
    num_steps: int = 128                # rollout length per env and update
    lr: float = 2.5e-4
    anneal_lr: bool = True
    gamma: float = 0.995                # ~200 agent steps (~27 s of game) planning horizon
    gae_lambda: float = 0.95
    num_minibatches: int = 4
    update_epochs: int = 3
    clip_coef: float = 0.1
    clip_vloss: bool = True
    ent_coef: float = 0.01
    ent_coef_final: float = 0.001       # entropy bonus is annealed to this, for a more decisive policy
    vf_coef: float = 0.5
    max_grad_norm: float = 0.5
    target_kl: float = 0.0              # early stop the update epochs above this KL (0: off)
    norm_reward: bool = True

    # network
    channels: str = '16,32,32'          # IMPALA stack widths, e.g. 32,64,64 for a bigger net
    hidden: int = 256

    # environment
    frame_skip: int = 4
    frame_stack: int = 4
    obs_size: int = 96
    max_episode_frames: int = 54_000    # 30 minutes of game play at 30 FPS
    reward_scale: float = 0.01
    survival_reward: float = 0.01
    refuel_reward: float = 0.15
    refuel_below: float = 0.4
    reversal_penalty: float = 0.05
    reversal_window: int = 4
    death_penalty: float = 2.0
    fuel_capacity: int = 7200           # 1 minute of flight
    refuel_rate: int = 60

    def env_kwargs(self):
        return dict(frame_skip=self.frame_skip, frame_stack=self.frame_stack, obs_size=self.obs_size,
                    max_episode_frames=self.max_episode_frames, reward_scale=self.reward_scale,
                    survival_reward=self.survival_reward, refuel_reward=self.refuel_reward,
                    refuel_below=self.refuel_below, reversal_penalty=self.reversal_penalty,
                    reversal_window=self.reversal_window,
                    death_penalty=self.death_penalty, fuel_capacity=self.fuel_capacity,
                    refuel_rate=self.refuel_rate)

    def network_kwargs(self):
        return dict(channels=tuple(int(c) for c in self.channels.split(',')), hidden=self.hidden)


class RewardNormalizer:
    '''scales rewards by the running standard deviation of the discounted return'''

    def __init__(self, num_envs, gamma, epsilon=1e-8):
        self.gamma = gamma
        self.epsilon = epsilon
        self.returns = np.zeros(num_envs)
        self.mean, self.var, self.count = 0.0, 1.0, 1e-4

    def _update(self, x):
        batch_mean, batch_var, batch_count = x.mean(), x.var(), x.size
        delta = batch_mean - self.mean
        total = self.count + batch_count
        self.mean += delta * batch_count / total
        m2 = self.var * self.count + batch_var * batch_count + delta**2 * self.count * batch_count / total
        self.var = m2 / total
        self.count = total

    def __call__(self, rewards, dones):
        self.returns = self.returns * self.gamma + rewards
        self._update(self.returns)
        self.returns[dones] = 0.0
        return rewards / np.sqrt(self.var + self.epsilon)

    def state_dict(self):
        return {'mean': self.mean, 'var': self.var, 'count': self.count}

    def load_state_dict(self, state):
        self.mean, self.var, self.count = state['mean'], state['var'], state['count']


def load_agent(path, device='cpu'):
    '''load a trained agent from a checkpoint, returns (agent, config)'''
    ckpt = torch.load(path, map_location=device, weights_only=False)
    cfg = Config(**{k: v for k, v in ckpt['config'].items() if k in {f.name for f in dataclasses.fields(Config)}})
    agent = ActorCritic(tuple(ckpt['obs_shape']), ckpt['num_actions'], **cfg.network_kwargs()).to(device)
    agent.load_state_dict(ckpt['model'])
    agent.eval()
    return agent, cfg


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description='Train a PPO agent to play River Raid')
    for f in dataclasses.fields(Config):
        flag = '--' + f.name.replace('_', '-')
        if f.type is bool:
            parser.add_argument(flag, action=argparse.BooleanOptionalAction, default=f.default)
        else:
            parser.add_argument(flag, type=f.type, default=f.default)
    return Config(**vars(parser.parse_args(argv)))


def _raise_interrupt(signum, frame):
    raise KeyboardInterrupt


def train(cfg: Config):
    from torch.utils.tensorboard import SummaryWriter

    # treat `kill` like ctrl-c: save a checkpoint and shut the env workers down cleanly
    signal.signal(signal.SIGTERM, _raise_interrupt)

    if cfg.device == 'auto':
        cfg.device = 'cuda' if torch.cuda.is_available() else 'cpu'
    device = torch.device(cfg.device)
    if cfg.num_workers < 0:
        cfg.num_workers = max(1, (os.cpu_count() or 2) - 1)
    if device.type == 'cuda':
        torch.backends.cudnn.benchmark = True
        torch.set_float32_matmul_precision('high')   # TF32 on Ampere
    use_bf16 = cfg.bf16 and device.type == 'cuda'

    ckpt = torch.load(cfg.resume, map_location=device, weights_only=False) if cfg.resume else None
    if ckpt:
        # the network and the environment must match the checkpoint, whatever the command line says
        for key in ('channels', 'hidden', *cfg.env_kwargs()):
            setattr(cfg, key, ckpt['config'][key])
    run_name = cfg.run_name or (os.path.basename(os.path.dirname(cfg.resume)) if ckpt else time.strftime('ppo_%Y%m%d_%H%M%S'))
    run_dir = os.path.join(cfg.log_dir, run_name)
    os.makedirs(run_dir, exist_ok=True)
    writer = SummaryWriter(run_dir)
    writer.add_text('config', '\n'.join('{}: {}'.format(k, v) for k, v in dataclasses.asdict(cfg).items()))

    np.random.seed(cfg.seed)
    torch.manual_seed(cfg.seed)

    envs = VecEnv(cfg.num_envs, cfg.num_workers, seed=cfg.seed * 10_000, env_kwargs=cfg.env_kwargs())
    obs_shape = envs.observation_space.shape
    num_actions = envs.action_space.n

    agent = ActorCritic(obs_shape, num_actions, **cfg.network_kwargs()).to(device)
    optimizer = torch.optim.Adam(agent.parameters(), lr=cfg.lr, eps=1e-5)
    normalizer = RewardNormalizer(cfg.num_envs, cfg.gamma)

    batch_size = cfg.num_envs * cfg.num_steps
    minibatch_size = batch_size // cfg.num_minibatches
    num_updates = cfg.total_steps // batch_size
    start_update, global_step, best_score = 1, 0, -np.inf
    if ckpt:
        agent.load_state_dict(ckpt['model'])
        optimizer.load_state_dict(ckpt['optimizer'])
        normalizer.load_state_dict(ckpt['reward_norm'])
        start_update, global_step, best_score = ckpt['update'] + 1, ckpt['global_step'], ckpt['best_score']
        print('resumed from {} at step {:,}'.format(cfg.resume, global_step))
    if cfg.compile:
        agent.forward = torch.compile(agent.forward)
    model = agent

    def save(name, update):
        torch.save({'model': agent.state_dict(), 'optimizer': optimizer.state_dict(),
                    'reward_norm': normalizer.state_dict(), 'config': dataclasses.asdict(cfg),
                    'obs_shape': obs_shape, 'num_actions': num_actions, 'update': update,
                    'global_step': global_step, 'best_score': best_score},
                   os.path.join(run_dir, name))

    # rollout storage, kept on the GPU (64 envs x 128 steps x 4x96x96 uint8 = 300 MB)
    obs = torch.zeros((cfg.num_steps, cfg.num_envs, *obs_shape), dtype=torch.uint8, device=device)
    actions = torch.zeros((cfg.num_steps, cfg.num_envs), dtype=torch.long, device=device)
    logprobs = torch.zeros((cfg.num_steps, cfg.num_envs), device=device)
    rewards = torch.zeros((cfg.num_steps, cfg.num_envs), device=device)
    dones = torch.zeros((cfg.num_steps, cfg.num_envs), device=device)
    values = torch.zeros((cfg.num_steps, cfg.num_envs), device=device)

    next_obs = torch.from_numpy(envs.reset()).to(device)
    next_done = torch.zeros(cfg.num_envs, device=device)
    recent = {k: deque(maxlen=100) for k in ('score', 'frames', 'kills', 'travel')}
    num_episodes = 0
    print('PPO on {} | {} envs on {} workers | {:,} updates of {:,} steps | obs {} | {:,} parameters'.format(
        device, cfg.num_envs, cfg.num_workers, num_updates, batch_size, obs_shape,
        sum(p.numel() for p in agent.parameters())))
    print('logging to {}  (tensorboard --logdir {})'.format(run_dir, cfg.log_dir))

    start_time, start_step = time.time(), global_step
    try:
        for update in range(start_update, num_updates + 1):
            progress = (update - 1.0) / num_updates
            if cfg.anneal_lr:
                optimizer.param_groups[0]['lr'] = cfg.lr * (1.0 - progress)
            ent_coef = cfg.ent_coef + (cfg.ent_coef_final - cfg.ent_coef) * progress

            ### COLLECT A ROLLOUT ##############################################
            for step in range(cfg.num_steps):
                global_step += cfg.num_envs
                obs[step] = next_obs
                dones[step] = next_done
                with torch.no_grad(), torch.autocast('cuda', torch.bfloat16, enabled=use_bf16):
                    action, logprob, value = model.act(next_obs)
                actions[step], logprobs[step], values[step] = action, logprob.float(), value.float()

                o, r, term, trunc, finished = envs.step(action.cpu().numpy())
                done = term | trunc
                if cfg.norm_reward:
                    r = normalizer(r, done)
                # a time limit is not a real terminal state: bootstrap with the value of the last obs
                truncated = [ep for ep in finished if ep['truncated']]
                if truncated:
                    final = torch.from_numpy(np.stack([ep['final_obs'] for ep in truncated])).to(device)
                    with torch.no_grad(), torch.autocast('cuda', torch.bfloat16, enabled=use_bf16):
                        final_values = model.value(final).float().cpu().numpy()
                    for ep, v in zip(truncated, final_values):
                        r[ep['env']] += cfg.gamma * v
                rewards[step] = torch.from_numpy(np.asarray(r, np.float32)).to(device)
                next_obs = torch.from_numpy(o).to(device)
                next_done = torch.from_numpy(done.astype(np.float32)).to(device)

                for ep in finished:
                    num_episodes += 1
                    for k in recent:
                        recent[k].append(ep[k])
                    writer.add_scalar('episode/score', ep['score'], global_step)
                    writer.add_scalar('episode/minutes_survived', ep['frames'] / 30 / 60, global_step)
                    writer.add_scalar('episode/kills', ep['kills'], global_step)
                    writer.add_scalar('episode/travel_km', ep['travel'] / 1000, global_step)
                    writer.add_scalar('episode/steering_changes_per_s', ep['steer_changes'] / (ep['frames'] / 30), global_step)

            ### GENERALIZED ADVANTAGE ESTIMATION ###############################
            with torch.no_grad(), torch.autocast('cuda', torch.bfloat16, enabled=use_bf16):
                next_value = model.value(next_obs).float()
            advantages = torch.zeros_like(rewards)
            lastgaelam = 0
            for t in reversed(range(cfg.num_steps)):
                if t == cfg.num_steps - 1:
                    nextnonterminal, nextvalues = 1.0 - next_done, next_value
                else:
                    nextnonterminal, nextvalues = 1.0 - dones[t + 1], values[t + 1]
                delta = rewards[t] + cfg.gamma * nextvalues * nextnonterminal - values[t]
                advantages[t] = lastgaelam = delta + cfg.gamma * cfg.gae_lambda * nextnonterminal * lastgaelam
            returns = advantages + values

            ### OPTIMIZE THE POLICY AND VALUE NETWORK ##########################
            b_obs = obs.reshape((-1, *obs_shape))
            b_actions, b_logprobs = actions.reshape(-1), logprobs.reshape(-1)
            b_advantages, b_returns, b_values = advantages.reshape(-1), returns.reshape(-1), values.reshape(-1)

            clipfracs = []
            for epoch in range(cfg.update_epochs):
                perm = torch.randperm(batch_size, device=device)
                for start in range(0, batch_size, minibatch_size):
                    mb = perm[start:start + minibatch_size]
                    with torch.autocast('cuda', torch.bfloat16, enabled=use_bf16):
                        newlogprob, entropy, newvalue = model.evaluate(b_obs[mb], b_actions[mb])
                    newlogprob, entropy, newvalue = newlogprob.float(), entropy.float(), newvalue.float()
                    logratio = newlogprob - b_logprobs[mb]
                    ratio = logratio.exp()
                    with torch.no_grad():
                        approx_kl = ((ratio - 1) - logratio).mean()
                        clipfracs.append(((ratio - 1.0).abs() > cfg.clip_coef).float().mean().item())

                    mb_adv = b_advantages[mb]
                    mb_adv = (mb_adv - mb_adv.mean()) / (mb_adv.std() + 1e-8)
                    pg_loss = torch.max(-mb_adv * ratio,
                                        -mb_adv * ratio.clamp(1 - cfg.clip_coef, 1 + cfg.clip_coef)).mean()

                    if cfg.clip_vloss:
                        v_clipped = b_values[mb] + (newvalue - b_values[mb]).clamp(-cfg.clip_coef, cfg.clip_coef)
                        v_loss = 0.5 * torch.max((newvalue - b_returns[mb])**2, (v_clipped - b_returns[mb])**2).mean()
                    else:
                        v_loss = 0.5 * ((newvalue - b_returns[mb])**2).mean()

                    entropy_loss = entropy.mean()
                    loss = pg_loss - ent_coef * entropy_loss + cfg.vf_coef * v_loss

                    optimizer.zero_grad(set_to_none=True)
                    loss.backward()
                    nn.utils.clip_grad_norm_(agent.parameters(), cfg.max_grad_norm)
                    optimizer.step()

                if cfg.target_kl and approx_kl > cfg.target_kl:
                    break

            ### LOGGING / CHECKPOINTS ##########################################
            y_pred, y_true = b_values.cpu().numpy(), b_returns.cpu().numpy()
            explained_var = 1 - np.var(y_true - y_pred) / (np.var(y_true) + 1e-8)
            sps = int((global_step - start_step) / (time.time() - start_time))
            writer.add_scalar('charts/learning_rate', optimizer.param_groups[0]['lr'], global_step)
            writer.add_scalar('charts/SPS', sps, global_step)
            writer.add_scalar('losses/value_loss', v_loss.item(), global_step)
            writer.add_scalar('losses/policy_loss', pg_loss.item(), global_step)
            writer.add_scalar('losses/entropy', entropy_loss.item(), global_step)
            writer.add_scalar('losses/approx_kl', approx_kl.item(), global_step)
            writer.add_scalar('losses/clipfrac', np.mean(clipfracs), global_step)
            writer.add_scalar('losses/explained_variance', explained_var, global_step)

            if recent['score']:
                avg_score = float(np.mean(recent['score']))
                writer.add_scalar('charts/avg100_score', avg_score, global_step)
                if len(recent['score']) >= 20 and avg_score > best_score:
                    best_score = avg_score
                    save('best.pt', update)
                eta = (cfg.total_steps - global_step) / max(sps, 1) / 3600
                print('step {:>11,} | episodes {:>6} | avg score {:>7.0f} | max {:>6} | avg minutes {:>5.2f} | '
                      'avg kills {:>5.1f} | best avg {:>7.0f} | {:>5} steps/s | ETA {:.1f} h'.format(
                          global_step, num_episodes, avg_score, max(recent['score']),
                          np.mean(recent['frames']) / 30 / 60, np.mean(recent['kills']), best_score, sps, eta),
                      flush=True)

            if update % cfg.save_every == 0 or update == num_updates:
                save('latest.pt', update)
    except KeyboardInterrupt:
        print('\ninterrupted, saving latest.pt')
        save('latest.pt', update - 1)
    finally:
        envs.close()
        writer.close()
    return run_dir


def main(argv=None):
    train(parse_args(argv))


if __name__ == '__main__':
    main()
