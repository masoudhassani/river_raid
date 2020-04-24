import pygame as pg
import yaml
import random
from modules import InitDeck
from modules import Entity, Player, Enemy, Bullet, Walls

# initialize the pygame library
pg.mixer.pre_init(16000, -16, 5, 640)
# pg.mixer.set_num_channels(10)
pg.init()

# initialize the score and its font
score_value = 0
font = pg.font.Font('freesansbold.ttf', 32)

# load game settings 
loader = InitDeck(preset='Basic')
settings = loader.load()
w = settings['width']
h = settings['height']


# hard coded game settings for calculation
player_name = 'player'
# box collision geometry dimension
cg = {
    'player': (28,26),
    'bullet': (2,8),
    'helicopter': (32,20),
    'ship': (64,16),
    'prop': (64,64)
}
block_size = 5

# setup the game display and title
screen = pg.display.set_mode((w, h))
pg.display.set_caption('River Raid 2020')
icon = pg.image.load('media/icon/jetfighter.png')
pg.display.set_icon(icon)
bkg = ((0, 50, 255))   # screen background color RGB 
init_player_pos = [w/2, h-50]
bullet_speed_factor = 6

# setup player and bullet
player = Player(scr=screen, name=player_name, ent_type='player', 
                cg=cg['player'], pos=init_player_pos, icon= 'media/icon/jetfighter.png', 
                v_speed=settings['player_speed'], h_speed=settings['player_speed']*2,
                sound_list=['media/sound/engine.wav', 'media/sound/engine-fast.wav', 'media/sound/engine-slow.wav'])

bullet = Bullet(scr=screen, name='bullet', ent_type='bullet', 
                cg=cg['bullet'], pos=init_player_pos, icon= 'media/icon/bullet.png', 
                v_speed=settings['player_speed']*bullet_speed_factor, h_speed=0, 
                player_cg=cg['player'], sound_list=['media/sound/bullet.wav']) 

# setup enemies
enemy_spawn_factor = 1   # lower means more enemy is spawned 
prop_spawn_factor = 2
enemy_names = ['helicopter', 'ship']
prop_names = ['prop1', 'prop2', 'prop3']
enemies = []
props = []
explosions = []

# setup walls 
walls = Walls(scr=screen, color=(45,135,10), icons=[], normal=200, extended=100, channel=350, 
                    max_island=w-200, min_island=200, spawn_dist=800, length=1000, randomness=0.8, 
                    v_speed=settings['player_speed'], block_size=block_size)

def create_enemies():
    enemy_name = random.choice(enemy_names) 

    # get the wall coordinate at y=0 for spawning 
    wall_1 = walls.return_wall_coordinate(0)
    # get the wall coordinate at the bottom of CG for spawning 
    wall_2 = walls.return_wall_coordinate(cg[enemy_name][1])
    # select the correct wall size 
    if wall_1[0] >= wall_2[0]:
        wall = wall_1
        pos_h = random.randint(wall[0],wall[1]-cg[enemy_name][0])
        vel_h = random.randint(0,1)
        enemy = Enemy(scr=screen, name=enemy_name, ent_type='enemy', 
                        cg=cg[enemy_name], pos=[pos_h, 0], icon='media/icon/{}.png'.format(enemy_name),
                        v_speed=settings['player_speed'], h_speed=settings['enemy_speed']*vel_h)
        enemies.append(enemy)
        enemy.set_walls(wall)

def create_props():
    prop_name = random.choice(prop_names) 

    # get the wall coordinate at y=0 for spawning 
    wall_1 = walls.return_wall_coordinate(0)
    # get the wall coordinate at the bottom of CG for spawning 
    wall_2 = walls.return_wall_coordinate(cg['prop'][1])
    # select the correct wall size 
    if wall_1[0] >= wall_2[0]:
        wall = wall_1
        pos_h = []
        pos_h.append(random.randint(0, wall[0]-cg['prop'][0]))
        pos_h.append(random.randint(wall[1],w-cg['prop'][0]))
        pos = random.choice(pos_h) 
        prop = Enemy(scr=screen, name=prop_name, ent_type='prop', 
                        cg=cg['prop'], pos=[pos, 0], icon='media/icon/{}.png'.format(prop_name),
                        v_speed=settings['player_speed'], h_speed=0)
        props.append(prop)
        prop.set_walls(wall)

def detect_collision(player, bullet, enemies, explosions):
    for e in enemies:
        # if the bullet hits the enemy
        if bullet.pos[1] <= e.pos[1]+e.cg[1] and bullet.pos[1]+bullet.cg[1] >= e.pos[1]:
            if bullet.pos[0] < e.pos[0]+e.cg[0] and bullet.pos[0]+bullet.cg[0]> e.pos[0]:
                bullet.reload()
                e.alive = False
                explosion =Entity(scr=screen, name='explosion', ent_type='explosion', 
                    cg=cg['player'], pos=e.pos, icon='media/icon/explosion2.png',
                    v_speed=settings['player_speed'], h_speed=0, life_span=300,
                    sound_list=['media/sound/explosion.wav'])
                explosions.append(explosion)
                # score += 10

        # if the player hits the enemy
        if player.pos[1] <= e.pos[1]+e.cg[1] and player.pos[1]+player.cg[1] >= e.pos[1]:
            if player.pos[0] < e.pos[0]+e.cg[0] and player.pos[0]+player.cg[0]> e.pos[0]:
                e.alive = False
                print('you lost')
                explosion =Entity(scr=screen, name='explosion', ent_type='explosion', 
                    cg=cg['player'], pos=[(e.pos[0]+player.pos[0])/2,(e.pos[1]+player.pos[1])/2], 
                    icon='media/icon/explosion1.png', v_speed=settings['player_speed'], 
                    h_speed=0, life_span=300, sound_list=['media/sound/explosion.wav']) 
                explosions.append(explosion)  

    return explosions             

def show_score():
    # render the display
    score = font.render('Score: {}'.format(score_value), True, (255,255,255))
    screen.blit(score, (40, h-50))  

# main loop
is_running = True
enemy_counter = 0
prop_counter = 0
while is_running:
    prop_counter += 1
    enemy_counter += 1

    # setup screen color
    screen.fill(bkg)

    keys = pg.key.get_pressed() 
    events = pg.event.get()
    for event in events:
        if event.type == pg.QUIT:
            is_running = False    

    # draw walls
    walls.update(keys)

    ### ENEMY #################################################
    # update enemy list 
    enemies = [x for x in enemies if x.is_active()]

    # remove enemies that are dead or out of screen
    for e in enemies:
        if not e.is_active():
            del e 

    # random generation of enemies 
    if enemies == []:
        randomizer = random.randint(1, enemy_spawn_factor+1)
        create_enemies()
    elif (enemy_counter/randomizer) == 200:
        randomizer = random.randint(1, enemy_spawn_factor+1)
        create_enemies()
        enemy_counter = 0
    ############################################################

    ### PROP #################################################
    # update prop list 
    props = [x for x in props if x.is_active()]

    # remove props that are dead or out of screen
    for p in props:
        if not p.is_active():
            del p

    # random generation of enemies 
    if props == []:
        randomizer = random.randint(prop_spawn_factor-1, prop_spawn_factor+1)
        create_props()
    elif (prop_counter/randomizer) == 200:
        randomizer = random.randint(prop_spawn_factor-1, prop_spawn_factor+1)
        create_props()
        prop_counter = 0
    ############################################################

    # get the wall coordinate at the player's height 
    wall_player = walls.return_wall_coordinate(player.pos[1])

    # update player position
    player.set_walls(wall_player)
    player.update(keys) 

    # update bullet 
    # bullet.set_walls(wall)
    bullet.update(keys, player.pos)     

    for p in props:
        # p.set_walls(wall_top)
        p.update(keys)  

    for e in enemies:
        # update enemy position 
        # e.set_walls(wall_top)
        e.update(keys)     

    # check for collision between player and enemies or bullet 
    explosions = detect_collision(player, bullet, enemies, explosions)
    explosions = [x for x in explosions if x.is_active()]

    # remove enemies that are dead or out of screen
    for e in explosions:
        e.update(keys)
        if not e.is_active():
            del e   

    show_score()
    pg.display.update()
