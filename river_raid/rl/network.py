"""IMPALA ResNet actor-critic (Espeholt et al. 2018), the standard encoder for
pixel-based PPO (Procgen, Atari). Much stronger than the 2-layer Nature CNN used in 2020."""
import numpy as np
import torch
from torch import nn
from torch.distributions import Categorical


def layer_init(layer, std=np.sqrt(2), bias=0.0):
    nn.init.orthogonal_(layer.weight, std)
    nn.init.constant_(layer.bias, bias)
    return layer


class ResidualBlock(nn.Module):
    def __init__(self, channels):
        super().__init__()
        self.conv0 = nn.Conv2d(channels, channels, 3, padding=1)
        self.conv1 = nn.Conv2d(channels, channels, 3, padding=1)

    def forward(self, x):
        return x + self.conv1(torch.relu(self.conv0(torch.relu(x))))


class ConvSequence(nn.Module):
    def __init__(self, in_channels, out_channels):
        super().__init__()
        self.conv = nn.Conv2d(in_channels, out_channels, 3, padding=1)
        self.pool = nn.MaxPool2d(3, stride=2, padding=1)
        self.res0 = ResidualBlock(out_channels)
        self.res1 = ResidualBlock(out_channels)

    def forward(self, x):
        return self.res1(self.res0(self.pool(self.conv(x))))


class ActorCritic(nn.Module):
    def __init__(self, obs_shape, num_actions, channels=(16, 32, 32), hidden=256):
        super().__init__()
        c, h, w = obs_shape
        seqs = []
        for out in channels:
            seqs.append(ConvSequence(c, out))
            c = out
            h, w = (h + 1) // 2, (w + 1) // 2
        self.encoder = nn.Sequential(*seqs, nn.Flatten(), nn.ReLU(),
                                     nn.Linear(c * h * w, hidden), nn.ReLU())
        self.actor = layer_init(nn.Linear(hidden, num_actions), std=0.01)
        self.critic = layer_init(nn.Linear(hidden, 1), std=1.0)

    def forward(self, obs):
        z = self.encoder(obs.float() / 255.0)
        return self.actor(z), self.critic(z).squeeze(-1)

    def value(self, obs):
        return self.forward(obs)[1]

    def act(self, obs, greedy=False):
        logits, value = self.forward(obs)
        dist = Categorical(logits=logits)
        action = logits.argmax(-1) if greedy else dist.sample()
        return action, dist.log_prob(action), value

    def evaluate(self, obs, actions):
        logits, value = self.forward(obs)
        dist = Categorical(logits=logits)
        return dist.log_prob(actions), dist.entropy(), value
