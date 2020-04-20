from modules import Entity
import pygame as pg

class Bullet(Entity):
    def __init__(self, scr, name, ent_type, cg, pos, icon, v_speed, h_speed, player_cg):
        super().__init__(scr, name, ent_type, cg, pos, icon, v_speed, h_speed)
        self.state = 'ready'
        self.player_cg = player_cg

    def update(self, keys, player_pos, hit): 
        # handle movements
        if self.state == 'fired':
            self.fire()
        else:
            self.pos = [player_pos[0]+self.player_cg[0]/2, player_pos[1]+self.player_cg[1]/2]

        # check if bullet is fired
        if keys[pg.K_SPACE] and self.state == 'ready':
            self.state = 'fired'

        # check collision with boundaries 
        self.check_walls()

        # check if bullet is not in screen, it will be removed from memory 
        self.check_state(hit)

        # draw
        self.screen.blit(self.icon, self.pos)

    def fire(self):
        self.pos[1] -= self.current_speed_v

    def check_walls(self):
        pass

    # check if the fired bullet is still in the screen
    def check_state(self, hit):
        if self.pos[1] < 0 or hit:
            self.state = 'ready'

