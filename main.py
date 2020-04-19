import pygame as pg
import yaml
from modules import InitDeck

# initialize the pygame library
pg.init()

# load game settings 
s = InitDeck(preset='Basic')
settings = s.load()

# hard coded game settings for calculation
player_dim = (28,26)     # dimension of jet fighter square (w,h)
helicopter_dim =(32,20)  # dimesion of enemy
ship_dim = (64,16)       # dimension of enemy
block_dim = 5

# setup the game display and title
screen = pg.display.set_mode((settings['width'], settings['height']))
pg.display.set_caption('River Raid 2020')
icon = pg.image.load('media/icon/jetfighter.png')
pg.display.set_icon(icon)
screen_fill = ((0, 50, 255))   # RGB 

is_running = True
# main game loop
while is_running:
    # setup screen color
    screen.fill(screen_fill)

    for event in pg.event.get():
        if event.type == pg.QUIT:
            is_running = False    

    pg.display.update()
