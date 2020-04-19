
import pygame as pg

class Entity:
    def __init__(self, scr, name, ent_type, cg, pos, icon):
        self.screen = scr
        self.name = name
        self.type = ent_type
        self.cg = cg    # collision geometry dimension wxh
        self.pos = pos 
        self.icon = pg.image.load(icon)

    def update(self, events=[]):
        # logic for position manipulation comes here 

        # draw on screen
        self.screen.blit(self.icon, self.pos) 

    def set_walls(self, walls):
        self.walls = walls

    def set_barrier(self):
        pass