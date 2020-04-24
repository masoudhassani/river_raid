import pygame as pg
import yaml
import random
from modules import InitDeck
from modules import Entity, Player, Enemy, Bullet, Walls

class RiverRaid:
    def __init__(self, preset='Basic', block_size=5, init_enemy_spawn=150,
                init_prop_spawn=150):

        # member variables from arg
        self.enemy_spawn_distance = init_enemy_spawn   #  spawn distance in pixel,lower means more enemy is spawned 
        self.prop_spawn_distance = init_prop_spawn

        # initialize the pygame library
        pg.mixer.pre_init(16000, -16, 5, 640)
        # pg.mixer.set_num_channels(10)
        pg.init()

        # initialize the score and its font
        self.score_value = 0
        self.font = pg.font.Font('freesansbold.ttf', 16)

        # load game settings 
        loader = InitDeck(preset='Basic')
        self.settings = loader.load()

        # hard coded game settings
        player_name = 'player'
        self.enemy_names = ['helicopter', 'ship']
        self.prop_names = ['prop1', 'prop2', 'prop3']        
        # box collision geometry dimension
        self.cg = {
            'player': (28,26),
            'bullet': (2,8),
            'helicopter': (32,20),
            'ship': (64,16),
            'prop': (64,64)
        }

        # setup the game display and title
        self.screen = pg.display.set_mode((self.settings['width'], self.settings['height']))
        pg.display.set_caption('River Raid 2020')
        icon = pg.image.load('media/icon/jetfighter.png')
        pg.display.set_icon(icon)
        self.background = ((0, 50, 255))   # screen background color RGB 

        # setup player and bullet
        init_player_pos = [self.settings['width']/2, self.settings['height']-50]
        bullet_speed_factor = 6
        self.player = Player(scr=self.screen, name=player_name, ent_type='player', 
                        cg=self.cg['player'], pos=init_player_pos, icon= 'media/icon/jetfighter.png', 
                        v_speed=self.settings['player_speed'], h_speed=self.settings['player_speed']*2,
                        sound_list=['media/sound/engine.wav', 'media/sound/engine-fast.wav', 'media/sound/engine-slow.wav'])

        self.bullet = Bullet(scr=self.screen, name='bullet', ent_type='bullet', 
                        cg=self.cg['bullet'], pos=init_player_pos, icon= 'media/icon/bullet.png', 
                        v_speed=self.settings['player_speed']*bullet_speed_factor, h_speed=0, 
                        player_cg=self.cg['player'], sound_list=['media/sound/bullet.wav']) 

        # setup walls 
        self.walls = Walls(scr=self.screen, color=(45,135,10), icons=[], normal=200, extended=100, channel=350, 
                            max_island=self.settings['width']-200, min_island=200, spawn_dist=800, length=1000, randomness=0.8, 
                            v_speed=self.settings['player_speed'], block_size=block_size)

        # initialization
        self.randomizer = 200
        self.enemies = []
        self.props = []
        self.explosions = []
        self.is_running = True
        self.travel_distance = 0
        self.last_enemey_spawn = 0
        self.last_prop_spawn = 0      

    def create_enemies(self):
        enemy_name = random.choice(self.enemy_names) 

        # get the wall coordinate at y=0 for spawning 
        wall_1 = self.walls.return_wall_coordinate(0)
        # get the wall coordinate at the bottom of CG for spawning 
        wall_2 = self.walls.return_wall_coordinate(self.cg[enemy_name][1]*3)
        # select the correct wall size 
        if wall_1[0] >= wall_2[0]:
            wall = wall_1
            pos_h = random.randint(wall[0],wall[1]-self.cg[enemy_name][0])
            vel_h = random.randint(0,1)
            enemy = Enemy(scr=self.screen, name=enemy_name, ent_type='enemy', 
                            cg=self.cg[enemy_name], pos=[pos_h, 0], icon='media/icon/{}.png'.format(enemy_name),
                            v_speed=self.settings['player_speed'], h_speed=self.settings['enemy_speed']*vel_h)
            self.enemies.append(enemy)
            enemy.set_walls(wall)

    def create_props(self):
        prop_name = random.choice(self.prop_names) 

        # get the wall coordinate at y=0 for spawning 
        wall_1 = self.walls.return_wall_coordinate(0)
        # get the wall coordinate at the bottom of CG for spawning 
        wall_2 = self.walls.return_wall_coordinate(self.cg['prop'][1])
        # select the correct wall size 
        wall = min(wall_1, wall_2)

        pos_h = []
        pos_h.append(random.randint(0, wall[0]-self.cg['prop'][0]))
        pos_h.append(random.randint(wall[1],self.settings['width']-self.cg['prop'][0]))
        pos = random.choice(pos_h) 
        prop = Enemy(scr=self.screen, name=prop_name, ent_type='prop', 
                        cg=self.cg['prop'], pos=[pos, 0], icon='media/icon/{}.png'.format(prop_name),
                        v_speed=self.settings['player_speed'], h_speed=0)
        self.props.append(prop)
        prop.set_walls(wall)

    def detect_collision(self):
        for e in self.enemies:
            # if the bullet hits the enemy
            if self.bullet.pos[1] <= e.pos[1]+e.cg[1] and self.bullet.pos[1]+self.bullet.cg[1] >= e.pos[1]:
                if self.bullet.pos[0] < e.pos[0]+e.cg[0] and self.bullet.pos[0]+self.bullet.cg[0]> e.pos[0]:
                    self.bullet.reload()
                    e.alive = False
                    explosion =Entity(scr=self.screen, name='explosion', ent_type='explosion', 
                        cg=self.cg['player'], pos=e.pos, icon='media/icon/explosion1.png',
                        v_speed=self.settings['player_speed'], h_speed=0, life_span=300,
                        sound_list=['media/sound/explosion.wav'])

                    self.explosions.append(explosion)
                    if e.name == 'helicopter':
                        self.score_value += 60
                    elif e.name == 'ship':
                        self.score_value += 40

            # if the player hits the enemy
            if self.player.pos[1] <= e.pos[1]+e.cg[1] and self.player.pos[1]+self.player.cg[1] >= e.pos[1]:
                if self.player.pos[0] < e.pos[0]+e.cg[0] and self.player.pos[0]+self.player.cg[0]> e.pos[0]:
                    e.alive = False
                    explosion =Entity(scr=self.screen, name='explosion', ent_type='explosion', 
                        cg=self.cg['player'], pos=[(e.pos[0]+self.player.pos[0])/2,(e.pos[1]+self.player.pos[1])/2], 
                        icon='media/icon/explosion1.png', v_speed=self.settings['player_speed'], 
                        h_speed=0, life_span=300, sound_list=['media/sound/explosion.wav']) 

                    self.explosions.append(explosion)           

    def show_score(self):
        # render the display
        score = self.font.render('Score: {}'.format(self.score_value), True, (255,255,255))
        self.screen.blit(score, (10, 20))  

    def show_travel(self):
        # render the display
        travel = self.font.render('Travel: {}'.format(int(self.travel_distance)), True, (255,255,255))
        self.screen.blit(travel, (10, 60))  

    def update(self):
        # setup screen color
        self.screen.fill(self.background)

        keys = pg.key.get_pressed() 
        events = pg.event.get()
        for event in events:
            if event.type == pg.QUIT:
                self.is_running = False    

        # draw walls
        self.walls.update(keys)

        ### ENEMY #################################################
        # update enemy list 
        self.enemies = [x for x in self.enemies if x.is_active()]

        # remove enemies that are dead or out of screen
        for e in self.enemies:
            if not e.is_active():
                del e 

        if (self.travel_distance-self.last_enemey_spawn) > self.randomizer:
            self.last_enemey_spawn = self.travel_distance
            self.randomizer = random.randint(self.enemy_spawn_distance*0.5, self.enemy_spawn_distance*1.5)
            self.create_enemies()
        ############################################################

        ### PROP #################################################
        # update prop list 
        self.props = [x for x in self.props if x.is_active()]

        # remove props that are dead or out of screen
        for p in self.props:
            if not p.is_active():
                del p

        if (self.travel_distance-self.last_prop_spawn) > self.randomizer:
            self.last_prop_spawn = self.travel_distance
            self.randomizer = random.randint(self.prop_spawn_distance*0.3, self.prop_spawn_distance*1.3)
            self.create_props()
        ############################################################

        # get the wall coordinate at the player's height 
        wall_player = self.walls.return_wall_coordinate(self.player.pos[1])

        # update player position
        self.player.set_walls(wall_player)
        self.travel_distance = self.player.update(keys) 

        # update bullet 
        # bullet.set_walls(wall)
        self.bullet.update(keys, self.player.pos)     

        for p in self.props:
            p.update(keys)  

        for e in self.enemies:
            e.update(keys)     

        # check for collision between player and enemies or bullet 
        self.detect_collision()
        self.explosions = [x for x in self.explosions if x.is_active()]

        # remove enemies that are dead or out of screen
        for e in self.explosions:
            e.update(keys)
            if not e.is_active():
                del e   

        self.show_score()
        # show_travel()
        pg.display.update()

        return self.is_running
