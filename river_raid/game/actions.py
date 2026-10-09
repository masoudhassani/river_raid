import random

import pygame as pg

# the actions available to an AI agent (speed up / slow down are human only, as in 2020)
ACTIONS = ('NO_MOVE', 'LEFT', 'RIGHT', 'LEFT_SHOOT', 'RIGHT_SHOOT', 'SHOOT')


class ActionSpace:
    def __init__(self, actions=ACTIONS):
        self.actions = list(actions)
        self.n = len(self.actions)

    def sample(self, rng=random):
        '''randomly select an action, returns the action and its index'''
        idx = rng.randrange(self.n)
        return self.actions[idx], idx

    @staticmethod
    def decode_keys(keys):
        '''decode keyboard input to a list of actions'''
        action_list = []
        if keys[pg.K_LEFT]:
            action_list.append('LEFT')
        elif keys[pg.K_RIGHT]:
            action_list.append('RIGHT')

        # handle speed
        if keys[pg.K_UP]:
            action_list.append('UP')
        elif keys[pg.K_DOWN]:
            action_list.append('DOWN')

        # handle shooting
        if keys[pg.K_SPACE]:
            action_list.append('SHOOT')

        return action_list

    def __str__(self):
        return 'Discrete ({})'.format(self.n)
