import pygame as pg
import yaml
from modules import InitDeck
from modules import Player

# initialize the pygame library
pg.init()

# load game settings 
loader = InitDeck(preset='Basic')
settings = loader.load()
w = settings['width']
h = settings['height']
s = settings['speed']

# hard coded game settings for calculation
player_name = 'player'
player_cg = (28,26)     # box collision geometry dimension of player (w,h)
helicopter_cg =(32,20)  # box collision geometry dimesion of enemy
ship_cg = (64,16)       # box collision geometry dimension of enemy
block_size = 5

# setup the game display and title
screen = pg.display.set_mode((w, h))
pg.display.set_caption('River Raid 2020')
icon = pg.image.load('media/icon/jetfighter.png')
pg.display.set_icon(icon)
bkg = ((0, 50, 255))   # screen background color RGB 

# setup player 
player = Player(scr=screen, name=player_name, ent_type='player', 
                cg=player_cg, pos=[w/2, h-50], icon= 'media/icon/jetfighter.png', speed=s)

# setup enemies

# main loop
is_running = True
while is_running:
    # setup screen color
    screen.fill(bkg)

    # read current boundary and barrier 
    walls = (0, w)

    keys = pg.key.get_pressed() 
    events = pg.event.get()
    for event in events:
        if event.type == pg.QUIT:
            is_running = False    

    # update player position
    player.set_walls(walls)
    player.update(keys) 

    # render the display
    pg.display.update()
