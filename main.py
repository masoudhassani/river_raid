import pygame as pg
import yaml
from modules import InitDeck

# initialize the pygame library
pg.init()

# load game setting 
s = InitDeck()
settings = s.load()

# setup the screen propertoes
screen = pg.display.set_mode((settings['width'], settings['height']))
