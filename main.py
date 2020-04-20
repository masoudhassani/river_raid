import pygame as pg
import yaml
import random
from modules import InitDeck
from modules import Player, Enemy

# initialize the pygame library
pg.init()

# load game settings 
loader = InitDeck(preset='Basic')
settings = loader.load()
w = settings['width']
h = settings['height']

# hard coded game settings for calculation
player_name = 'player'
cg = {
    'player': (28,26),
    'helicopter': (32,20),
    'ship': (64,16)
}
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
                cg=cg['player'], pos=[w/2, h-50], icon= 'media/icon/jetfighter.png', 
                v_speed=settings['player_speed'], h_speed=settings['player_speed'])

# setup enemies
max_num_enemy = 2
enemy_frequency = 3
enemy_names = ['helicopter', 'ship']
enemies = []

def create_enemies(walls):
    enemy_name = random.choice(enemy_names) 
    pos_h = random.randint(walls[0][0],walls[0][1]-cg[enemy_name][0])
    vel_h = random.randint(0,1)
    enemy = Enemy(scr=screen, name=enemy_name, ent_type='enemy', 
                    cg=cg[enemy_name], pos=[pos_h, 0], icon='media/icon/{}.png'.format(enemy_name),
                    v_speed=settings['player_speed'], h_speed=settings['enemy_speed']*vel_h)
    enemies.append(enemy)

# main loop
is_running = True
counter = 0
while is_running:
    counter += 1

    # setup screen color
    screen.fill(bkg)

    # read current boundary and barrier 
    walls = ((0, w),(0, w))   # top, bottom

    keys = pg.key.get_pressed() 
    events = pg.event.get()
    for event in events:
        if event.type == pg.QUIT:
            is_running = False    

    ### ENEMY #################################################
    # up datae enemy list 
    enemies = [x for x in enemies if x.is_active()]

    # remove enemies that are dead or out of screen
    for e in enemies:
        if not e.is_active():
            del e 

    # random generation of enemies 
    if enemies == []:
        randomizer = random.randint(1, enemy_frequency+1)
        create_enemies(walls)
    elif (counter/randomizer) == 1000:
        randomizer = random.randint(1, enemy_frequency+1)
        create_enemies(walls)
        counter = 0
    ############################################################


    # update player position
    player.set_walls(walls)
    player.update(keys) 

    for e in enemies:
        # update enemy position 
        e.set_walls(walls)
        e.update(keys)     

    # render the display
    pg.display.update()
