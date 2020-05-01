import random 
import pygame as pg

class ActionSpace:
    def __init__(self):
        self.available_actions(False)

    def available_actions(self, condition, player_pos=[], wall=[]):
        if condition:
            self.actions = ['LEFT', 'RIGHT']
        else:
            self.actions = ['LEFT', 'RIGHT', 'LEFT_SHOOT', 'RIGHT_SHOOT', 'SHOOT']

    def sample(self):
        return random.choice(self.actions)

    def decode_keys(self, keys):
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



