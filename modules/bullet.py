from modules import Entity
import pygame as pg
from pygame import mixer

class Bullet(Entity):

    def update(self, action, player_pos): 
        # handle movements
        if self.state == 'fired':
            self.fire()
        else:
            self.pos = [player_pos[0]+self.player_cg[0]/2-self.cg[0]/2, player_pos[1]+4]

        # check if bullet is fired
        if 'SHOOT' in action and self.state == 'ready':
            self.state = 'fired'

        # check collision with boundaries 
        self.check_walls()

        # check if bullet is not in screen, it will be removed from memory 
        self.check_state()

    def fire(self):
        # play the explosion sound 
        if not self.sound_played:
            pg.mixer.Channel(6).play(self.sounds[0])
            # self.sound.play()
            self.sound_played = True

        self.pos[1] -= self.current_speed_v

    def check_walls(self):
        pass

    # check if the fired bullet is still in the screen
    def check_state(self):
        if self.pos[1] < 0:
            self.state = 'ready'
            self.sound_played = False

    def reload(self):
        self.state = 'ready'
        self.sound_played = False

    def render(self):
        # draw
        if self.state == 'fired':
            self.screen.blit(self.icons[0], self.pos)