import random 
import pygame as pg

class ActionSpace:
    def __init__(self):
        self.available_actions(False)
        self.n = len(self.actions)

    '''
    create a list of available actions based on a condition
    '''
    def available_actions(self, condition, player_pos=[], wall=[]):
        self.actions = ['LEFT', 'RIGHT', 'LEFT_SHOOT', 'RIGHT_SHOOT', 'SHOOT']
        # if condition:
        #     self.actions = ['LEFT', 'RIGHT']
        # else:
        #     self.actions = ['LEFT', 'RIGHT', 'LEFT_SHOOT', 'RIGHT_SHOOT', 'SHOOT']
  
    '''
    randomly select an action from available actions
    '''
    def sample(self):
        act = random.choice(self.actions)
        return act, self.actions.index(act)

    '''
    decode keyboard input to actions
    '''
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

    def __str__(self):
        return ('Discrete ({})'.format(self.n))