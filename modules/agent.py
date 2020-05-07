
import numpy as np
import random

class Agent:
  def __init__(self, eps=0.1, alpha=0.5, id=0):
    self.eps = eps               # epsilon greedy algorithm parameter
    self.alpha = alpha           # learning rate
    self.state_history = []
    self.agent_id = id

  def reset_history(self):
    self.state_history = []

  def take_action(self, env):
    action = env.action_space.sample()   
    return action

  def update_state_history(self, s):
    self.state_history.append(s)

  def update(self, env):
      pass

