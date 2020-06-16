import pygame as pg
import yaml
import random
import time
import numpy as np
from modules import InitDeck
from modules import Entity, Player, Enemy, Bullet, Walls, ActionSpace, ObservationSpace, Agent
import matplotlib.pyplot as plt 
from matplotlib import colors
import cv2
import csv

class RiverRaid:
    def __init__(self, preset='Basic', ai_agent=False, random=False, init_enemy_spawn=150,
                init_prop_spawn=150, init_fuel_spawn=500):

        # member variables from arg
        self.enemy_spawn_distance = init_enemy_spawn   #  spawn distance in pixel,lower means more enemy is spawned 
        self.prop_spawn_distance = init_prop_spawn
        self.fuel_spawn_distance = init_fuel_spawn
        self.init_enemy_randomizer = init_enemy_spawn   #  spawn distance in pixel,lower means more enemy is spawned 
        self.init_prop_randomizer = init_prop_spawn
        self.init_fuel_randomizer = init_fuel_spawn
        self.ai_agent = ai_agent
        self.random_assets = random

        # max of encoding values for each reduced state element
        # for example, wall=0, player=1, ... enemy=4, the enc_max is 4
        # for rgb or grayscale state, use 255
        self.enc_max = 255  

        #### SOUND ##############################################
        pg.mixer.pre_init(16000, -16, 2, 512)
        pg.mixer.init()
        pg.mixer.set_num_channels(8)
        #########################################################

        # initialize the pygame library
        pg.init()

        # initialize clock
        self.clock = pg.time.Clock()
        self.FPS = 30

        # initialize the score and its font
        self.font_small = pg.font.Font('freesansbold.ttf', 16)
        self.font_large = pg.font.Font('freesansbold.ttf', 48)

        # load game settings 
        loader = InitDeck(preset=preset)
        self.settings = loader.load()

        # hard coded game assets
        self.enemy_names = ['helicopter', 'ship']
        self.prop_names = ['prop1', 'prop2', 'prop3']    

        # box collision geometry dimension
        self.cg = {
            'player': (28,26),
            'bullet': (2,14),
            'helicopter': (32,20),
            'ship': (64,20),
            'prop': (64,64),
            'fuel': (32,56)
        }

        # setup the game display and title
        self.screen = pg.display.set_mode((self.settings['width'], self.settings['height']))
        pg.display.set_caption('River Raid 2020')
        icon = pg.image.load('media/icon/jetfighter.png')
        pg.display.set_icon(icon)
        self.background = ((20, 50, 255))   # screen background color RGB 

        # initialization of discrete state space plotting 
        ##########################################################
        self.cmap = colors.ListedColormap(['blue','yellow','red','pink','green'])   # color map for visualization
        plt.ion()
        plt.gca().invert_yaxis()
        frame1 = plt.gca()
        frame1.axes.xaxis.set_ticklabels([])
        frame1.axes.yaxis.set_ticklabels([])        
        ##########################################################      

        #### DETERMINISTIC GAME FOR AI ###########################
        if not self.random_assets:
            a = []
            with open('media/assets-position.csv') as pos:
                reader = csv.reader(pos, delimiter=',')
                next(reader)   # skip header
                for row in reader:
                    a.append(row)
            
            self.assets = np.array(a)

        ##########################################################
        #### RESET ###############################################
        self.reset()
        ########################################################## 
        

    '''
    creates enemies randomly with a random horizontal position
    '''
    def create_enemies(self, data=None):
        # update enemy list 
        self.enemies = [x for x in self.enemies if x.is_active()]

        # remove enemies that are dead or out of screen
        for e in self.enemies:
            if not e.is_active():
                del e 

        if not self.random_assets:
            if data != None:
                # get the wall coordinate at y=0 for spawning 
                wall = self.walls.return_wall_coordinate(0)            
                enemy_name = data[0]
                pos_h = data[1]
                vel_h = data[2]
                enemy = Enemy(scr=self.screen, name=enemy_name, ent_type='enemy', 
                                cg=self.cg[enemy_name], pos=[pos_h, 0], icon_list=['media/icon/{}.png'.format(enemy_name)],
                                v_speed=self.settings['player_speed'], h_speed=self.settings['enemy_speed']*vel_h)
                self.enemies.append(enemy)
                enemy.set_walls(wall)
        
        else:
            if (self.travel_distance-self.last_enemey_spawn) > self.enemy_randomizer:
                self.last_enemey_spawn = self.travel_distance
                self.enemy_randomizer = random.randint(self.enemy_spawn_distance*0.5, self.enemy_spawn_distance*1.5)  

                enemy_name = random.choice(self.enemy_names) 
                # get the wall coordinate at y=0 for spawning 
                wall_1 = self.walls.return_wall_coordinate(0)
                # get the wall coordinate at the bottom of CG for spawning 
                wall_2 = self.walls.return_wall_coordinate(self.cg[enemy_name][1]*3)

                # select the correct wall size 
                if wall_1[0] >= wall_2[0]:
                    wall = wall_1
                    pos_h = random.randint(wall[0], wall[1]-self.cg[enemy_name][0])
                    vel_h = random.randint(0,1)
                    enemy = Enemy(scr=self.screen, name=enemy_name, ent_type='enemy', 
                                    cg=self.cg[enemy_name], pos=[pos_h, 0], icon_list=['media/icon/{}.png'.format(enemy_name)],
                                    v_speed=self.settings['player_speed'], h_speed=self.settings['enemy_speed']*vel_h)
                    self.enemies.append(enemy)
                    enemy.set_walls(wall)

    '''
    create props randomly and in random horizontal position
    player cannot interact with props since they are positioned 
    outside of boundaries
    '''
    def create_props(self, data=None):
        # update prop list 
        self.props = [x for x in self.props if x.is_active()]

        # remove props that are dead or out of screen
        for p in self.props:
            if not p.is_active():
                del p

        if not self.random_assets:
            if data != None:
                prop_name = random.choice(self.prop_names) 
                # get the wall coordinate at y=0 for spawning 
                wall = self.walls.return_wall_coordinate(0)            
                pos_h = data[1]

                prop = Enemy(scr=self.screen, name=prop_name, ent_type='prop', 
                                cg=self.cg['prop'], pos=[pos_h, 0], icon_list=['media/icon/{}.png'.format(prop_name)],
                                v_speed=self.settings['player_speed'], h_speed=0)
                self.props.append(prop)
                prop.set_walls(wall)
        
        else:
            if (self.travel_distance-self.last_prop_spawn) > self.prop_randomizer:
                self.last_prop_spawn = self.travel_distance
                self.prop_randomizer = random.randint(self.prop_spawn_distance*0.3, self.prop_spawn_distance*1.3)    

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
                                cg=self.cg['prop'], pos=[pos, 0], icon_list=['media/icon/{}.png'.format(prop_name)],
                                v_speed=self.settings['player_speed'], h_speed=0)
                self.props.append(prop)
                prop.set_walls(wall)

    '''
    create fuel pumps randomly and on a random horizontal position
    '''
    def create_fuels(self, data=None):
        # update fuel list 
        self.fuels = [x for x in self.fuels if x.is_active()]

        # remove props that are dead or out of screen
        for f in self.fuels:
            if not f.is_active():
                del f

        if not self.random_assets:
            if data != None:
                # get the wall coordinate at y=0 for spawning 
                wall = self.walls.return_wall_coordinate(0)            
                pos_h = data[1]

                fuel = Enemy(scr=self.screen, name='fuel', ent_type='fuel', 
                                cg=self.cg['fuel'], pos=[pos_h, 0], icon_list=['media/icon/fuel.png'],
                                v_speed=self.settings['player_speed'], h_speed=0)
                self.fuels.append(fuel)
                fuel.set_walls(wall)
        
        else:
            if (self.travel_distance-self.last_fuel_spawn) > self.fuel_randomizer:
                self.last_fuel_spawn = self.travel_distance
                self.fuel_randomizer = random.randint(self.fuel_spawn_distance*0.3, self.fuel_spawn_distance*1.5)  

                # get the wall coordinate at y=0 for spawning 
                wall_1 = self.walls.return_wall_coordinate(0)
                # get the wall coordinate at the bottom of CG for spawning 
                wall_2 = self.walls.return_wall_coordinate(self.cg['fuel'][1]*2.5)
                # select the correct wall size 
                if wall_1[0] >= wall_2[0]:
                    wall = wall_1
                    pos_h = random.randint(wall[0],wall[1]-self.cg['fuel'][0])
                    fuel = Enemy(scr=self.screen, name='fuel', ent_type='fuel', 
                                    cg=self.cg['fuel'], pos=[pos_h, 0], icon_list=['media/icon/fuel.png'],
                                    v_speed=self.settings['player_speed'], h_speed=0)
                    self.fuels.append(fuel)
                    fuel.set_walls(wall)

    '''
    collision detection between enemies and player/bullet
    '''
    def enemy_collision(self):        
        for e in self.enemies:
            # if the bullet hits the enemy
            if self.bullet.pos[1] <= e.pos[1]+e.cg[1] and self.bullet.pos[1]+self.bullet.cg[1] >= e.pos[1]:
                if self.bullet.pos[0] < e.pos[0]+e.cg[0] and self.bullet.pos[0]+self.bullet.cg[0]> e.pos[0]:
                    self.bullet.reload()
                    e.alive = False
                    explosion = Entity(scr=self.screen, name='explosion', ent_type='explosion', 
                        cg=self.cg['player'], pos=e.pos, icon_list=['media/icon/explosion2.png'],
                        v_speed=self.settings['player_speed'], h_speed=0, life_span=100,
                        sound_list=['media/sound/explosion.wav'])

                    self.explosions.append(explosion)
                    if e.name == 'helicopter':
                        self.score_value += 60
                    elif e.name == 'ship':
                        self.score_value += 40
                    
                    # stop the episode for AI if it hits an enemy
                    # if self.ai_agent:
                    #     self.reward = 1000
                        # self.is_running = False


            # if the player hits the enemy
            if self.player.pos[1] <= e.pos[1]+e.cg[1] and self.player.pos[1]+self.player.cg[1] >= e.pos[1]:
                if self.player.pos[0] < e.pos[0]+e.cg[0] and self.player.pos[0]+self.player.cg[0]> e.pos[0]:
                    e.alive = False
                    self.player.alive = False
                    self.lives_left -= 1
                    explosion = Entity(scr=self.screen, name='explosion', ent_type='explosion', 
                        cg=self.cg['player'], pos=[(e.pos[0]+self.player.pos[0])/2,(e.pos[1]+self.player.pos[1])/2], 
                        icon_list=['media/icon/explosion1.png'], v_speed=self.settings['player_speed'], 
                        h_speed=0, life_span=100, sound_list=['media/sound/explosion.wav']) 

                    self.explosions.append(explosion)  
                    if e.name == 'helicopter':
                        self.score_value += 60
                    elif e.name == 'ship':
                        self.score_value += 40
                    

    '''
    collision detection between player and walls
    '''
    def wall_collision(self):
        wall_1 = self.walls.return_wall_coordinate(self.player.pos[1])
        wall_2 = self.walls.return_wall_coordinate(self.player.pos[1]+self.player.cg[1])

        # if the bullet hits the horizontal wall, it will disapear and reload
        wall_3 = self.walls.return_wall_coordinate(self.bullet.pos[1])
        if self.bullet.pos[0] < wall_3[0] or self.bullet.pos[0]+self.bullet.cg[0] > wall_3[1]: 
            self.bullet.reload()

        # if the player hits the wall
        if (self.player.pos[0] < wall_1[0] or self.player.pos[0]+self.player.cg[0] > wall_1[1] 
                or self.player.pos[0] < wall_2[0] or self.player.pos[0]+self.player.cg[0] > wall_2[1]):

            self.lives_left -= 1
            self.player.alive = False
            explosion = Entity(scr=self.screen, name='explosion', ent_type='explosion', 
                cg=self.cg['player'], pos=[self.player.pos[0],self.player.pos[1]], 
                icon_list=['media/icon/explosion1.png'], v_speed=self.settings['player_speed'], 
                h_speed=0, life_span=100, sound_list=['media/sound/explosion.wav']) 
            
            self.explosions.append(explosion)

    '''
    detect if player is passing over a fuel pump
    or a bullet has hit the pump
    '''
    def fuel_collision(self):
        collision = False
        for f in self.fuels:
            # if the player passing on fuel tanks 
            if self.player.pos[1] <= f.pos[1]+f.cg[1] and self.player.pos[1]+self.player.cg[1] >= f.pos[1]:
                if self.player.pos[0] < f.pos[0]+f.cg[0] and self.player.pos[0]+self.player.cg[0]> f.pos[0]:
                    collision = True 
                    
                    # add reward for AI agent when it is passing over a fuel
                    self.reward = 15

            # if the bullet hits the fuel tank
            if self.bullet.state == 'fired':
                if self.bullet.pos[1] <= f.pos[1]+f.cg[1] and self.bullet.pos[1]+self.bullet.cg[1] >= f.pos[1]:
                    if self.bullet.pos[0] < f.pos[0]+f.cg[0] and self.bullet.pos[0]+self.bullet.cg[0]> f.pos[0]:
                        self.bullet.reload()
                        f.alive = False
                        explosion = Entity(scr=self.screen, name='explosion', ent_type='explosion', 
                            cg=self.cg['player'], pos=f.pos, icon_list=['media/icon/explosion2.png'],
                            v_speed=self.settings['player_speed'], h_speed=0, life_span=100,
                            sound_list=['media/sound/explosion.wav'])

                        self.explosions.append(explosion) 
                        self.score_value += 80
   
        return collision

    '''
    show current score on the screen
    '''
    def show_score(self):
        # render the display
        score = self.font_small.render('Score: {}'.format(self.score_value), True, (255,255,255))
        self.screen.blit(score, (10, 20))  

    '''
    show current travel distance on the screen
    '''
    def show_travel(self):
        # render the display
        travel = self.font_small.render('Travel: {} km'.format(int(self.travel_distance/1000)), True, (255,255,255))
        self.screen.blit(travel, (10, 80))  

    '''
    show remaining number of lives on the screen
    '''
    def show_lives(self):
        # render the display
        lives = self.font_small.render('Lives: {}'.format(int(self.lives_left)), True, (255,255,255))
        self.screen.blit(lives, (10, 40)) 

    '''
    show remaining fuel on the screen
    '''
    def show_fuel(self):
        # render the display
        fuel = self.font_small.render('Fuel: {} %'.
                format(int(self.player.fuel*100/self.player.capacity)), True, (255,255,255))
        self.screen.blit(fuel, (10, 60)) 

    '''
    genereic function to show a string with a large font on the screen
    '''
    def show_on_screen(self, val, x, y, color=(255,255,255)):
        render = self.font_large.render(str(val), True, color)
        self.screen.blit(render, (x, y))         

    '''
    restart the game after dying 
    this is used when human is playing
    '''
    def restart_game(self, delay):
        paused = True
        timer = 0
        t0 = int(time.time()*1000.0)
        for e in self.explosions:
            e.alive = False 

        for e in self.enemies:
            e.alive = False 

        while paused:
            timer = int(time.time()*1000.0) - t0
            if timer > delay:
                paused = False

    '''
    pause game after pressing p
    '''
    def pause_game(self):
        paused = True
        while paused:
            self.player.pause()
            self.show_on_screen('PAUSED', self.settings['width']/2 - 100, self.settings['height']/2)
            pg.display.update()
            events = pg.event.get()
            for event in events:
                if event.type == pg.QUIT:
                    self.is_running = False  
                elif event.type == pg.KEYDOWN:
                    if event.key == pg.K_p:
                        self.game_paused = False
                        paused = False

    '''
    update the environment an state based on the agen action
    this is the main method that should be called every step
    '''
    def step(self, action):
        self.clock.tick(self.FPS)
        self.reward = 0

        ### RESTART #################################################
        if self.restart:
            self.restart_game(2000)
            self.player.reset()
            self.restart = False 
        ############################################################    

        ### ACTIONS #################################################
        if not self.ai_agent:
            keys = pg.key.get_pressed()
            action = self.action_space.decode_keys(keys)

            events = pg.event.get()
            for event in events:
                if event.type == pg.QUIT:
                    self.is_running = False  
                elif event.type == pg.KEYDOWN:
                    if event.key == pg.K_p:
                        self.game_paused = True

            if self.game_paused:
                self.pause_game()
        
        else:
            events = pg.event.get()
            for event in events:
                if event.type == pg.QUIT:
                    self.is_running = False  
            self.action_space.available_actions(condition=self.bullet.state == 'fired')
        ############################################################ 

        ### COLLISIONS #################################################
        self.walls.update(action)
        self.enemy_collision()
        self.wall_collision()
        ############################################################ 

        # random creation of assets
        if self.random_assets:
            ### ENEMY #################################################
            self.create_enemies()
            ############################################################

            ### PROP #################################################
            self.create_props()
            ############################################################

            ### FUEL #################################################
            self.create_fuels()
            ##########################################################
        
        # predefined asset position based on a csv file
        else:
            if self.travel_distance in self.assets[:, 1].astype(int):
                idx = np.argwhere(self.assets[:, 1].astype(int) == self.travel_distance)[0][0]
                asset_data = [self.assets[idx][0], self.assets[idx][2].astype(int), self.assets[idx][3].astype(int)]
                if asset_data[0] == 'ship' or asset_data[0] == 'helicopter':
                    self.create_enemies(asset_data)
                
                elif asset_data[0] == 'fuel':
                    self.create_fuels(asset_data)
                
                elif asset_data[0] == 'prop':
                    self.create_props(asset_data)
                
                else:
                    print('unknown asset type {}'.format(asset_data[0]))
            
            else:
                self.create_enemies()
                self.create_props()
                self.create_fuels()


        ### FUEL ZERO###############################################
        # player is dead if fuel is zero 
        if self.player.fuel == 0:
            explosion = Entity(scr=self.screen, name='explosion', ent_type='explosion', 
                cg=self.cg['player'], pos=[self.player.pos[0],self.player.pos[1]], 
                icon_list=['media/icon/explosion1.png'], v_speed=self.settings['player_speed'], 
                h_speed=0, life_span=100, sound_list=['media/sound/explosion.wav']) 
            
            self.explosions.append(explosion)            
            self.player.alive = False
            self.lives_left -= 1            
        ############################################################    

        ### UPDATE ################################################# 
        for p in self.props:
            p.update(action)

        for f in self.fuels:
            f.update(action) 

        for e in self.enemies: 
            e.update(action)   

        # update bullet 
        self.bullet.update(action, self.player.pos)      

        # update player 
        self.player.set_walls(self.walls.return_wall_coordinate(self.player.pos[1]))
        self.travel_distance = self.player.update(action, self.fuel_collision()) 

        # update explosions
        self.explosions = [x for x in self.explosions if x.is_active()]
        for e in self.explosions:
            e.update(action) 
            if not e.is_active():
                del e   

        ############################################################ 

        ### GAME END ################################################# 
        if self.lives_left < 1:
            self.is_running = False
        elif not self.player.alive:
            self.restart = True
        ############################################################ 

        ### UPDATE STATE ###########################################
        entity_encoding =[[self.enemies, 4],
                          [self.fuels, 3]]
        # self.state = self.observation_space.update(entity_encoding)

        # get the pixels from screen 
        surface = self.pre_render()
        tmp_arr = pg.surfarray.array3d(surface)

        # crop 
        tmp_arr = tmp_arr[100:tmp_arr.shape[0]-100, :, :]
    
        # resize the captured screen
        tmp_arr = tmp_arr[::4, ::4]

        # grayscale
        self.state = np.mean(tmp_arr, axis=2).astype(np.uint8)

        # reshape to be familiar for keras
        # self.state = self.state.reshape(self.state.shape[0], self.state.shape[1])
        
        ############################################################

        ### UPDATE REWARD ##########################################
        self.reward += self.score_value - self.score_value_prev
        self.score_value_prev = self.score_value

        # reduce 500 point if the agent dies
        if not self.player.alive:
            self.reward = -501
        
        # add two points of reward for each step that the agent is alive
        # elif self.is_running:
        #     self.reward += 1
        ############################################################

        return self.state, self.reward, self.is_running

    '''
    reset all game metrics and variable 
    this is also called when the environment is initialized
    '''
    def reset(self):
        #### PLAYER INIT ########################################
        player_name = 'player'
        init_player_pos = [self.settings['width']/2, self.settings['height']-50]
        bullet_speed_factor = 5
        self.player = Player(scr=self.screen, name=player_name, ent_type='player', 
                        cg=self.cg['player'], pos=init_player_pos, icon_list=['media/icon/jetfighter.png','media/icon/explosion2.png'], 
                        v_speed=self.settings['player_speed'], h_speed=self.settings['player_speed'],
                        sound_list=['media/sound/engine.wav', 'media/sound/engine-fast.wav', 'media/sound/engine-slow.wav',
                        'media/sound/fuel-up.wav', 'media/sound/fuel-low.wav', 'media/sound/tank-filled.wav'],
                        capacity=3000, dec_factor=1, inc_factor=30, low_fuel=0.2)
        ##########################################################
        
        #### BULLET INIT ########################################
        self.bullet = Bullet(scr=self.screen, name='bullet', ent_type='bullet', 
                        cg=self.cg['bullet'], pos=init_player_pos, icon_list=['media/icon/bullet.png'], 
                        v_speed=self.settings['player_speed']*bullet_speed_factor, h_speed=0, 
                        player_cg=self.cg['player'], sound_list=['media/sound/bullet.wav']) 
        ##########################################################

        #### WALL INIT ########################################
        length = 1000
        randomness = 1 if not self.random_assets else 0.8
        self.walls = Walls(scr=self.screen, color=(45,135,10), icon_list=[], normal=200, extended=100, channel=350, 
                            max_island=self.settings['width']-200, min_island=200, spawn_dist=800, length=length, randomness=randomness, 
                            v_speed=self.settings['player_speed'], block_size=self.settings['player_speed'])
        ##########################################################

        #### ACTION SPACE ########################################
        self.action_space = ActionSpace()
        ##########################################################

        #### STATE SPACE #########################################
        # state discretization parameters
        block_size = self.settings['player_speed']
        crop_h = 200
        crop_v = 0
        
        # entity-encoding lists
        wall_encoding = [self.walls, 1]
        player_encoding =[self.player, 2]

        # initialize the state space
        self.observation_space = ObservationSpace(w=self.settings['width'], 
                                                  h=self.settings['height'],
                                                  player=player_encoding,
                                                  wall=wall_encoding, enc_max=self.enc_max,
                                                  block_size=block_size,
                                                  crop_h=crop_h, crop_v=crop_v)     
        ##########################################################

        #### AGENT ###############################################
        self.agent = Agent()
        ##########################################################  

        self.enemy_randomizer = self.init_enemy_randomizer
        self.prop_randomizer = self.init_prop_randomizer
        self.fuel_randomizer = self.init_fuel_randomizer
        self.enemies = []
        self.props = []
        self.explosions = []
        self.fuels = []
        self.is_running = True
        self.travel_distance = 0
        self.last_enemey_spawn = 0
        self.last_prop_spawn = 0 
        self.last_fuel_spawn = 0      
        self.lives_left = self.settings['num_lives']
        self.restart = False
        self.game_paused = False 
        self.score_value = 0   
        self.score_value_prev = 0
        self.reward = 0

        return self.observation_space.state  

    '''
    render the game environment on screen
    this should not be called in every iteration in AI mode since it 
    slows down the trining process significantly
    '''
    def pre_render(self):
        # setup screen color
        self.screen.fill(self.background)

        # render walls 
        self.walls.render()

        for f in self.fuels:
            f.render()  

        for e in self.enemies: 
            e.render()    

        self.player.render() 
        self.bullet.render()  

        surface = pg.display.get_surface() 

        # render all entities 
        for p in self.props:
            p.render()  

        for e in self.explosions:
            e.render()

        return surface

    def render(self):
        # show game metrics
        self.show_score()
        self.show_lives()
        self.show_travel()
        self.show_fuel()

        # render all objects
        pg.display.update()

    '''
    render the discrete map with assets
    NOTE: very slow!
    '''
    def discrete_render(self):
        # comment this if you want to use opencv to show processed state (recommended)
        cv2.imshow('image', self.state)

        # comment above and uncomment the following if you want to use matplotlib to 
        # show the processed state (not recommended)
        # state_reshaped = self.state.reshape(self.state.shape[0],self.state.shape[1])
        # plt.imshow(np.transpose(state_reshaped), cmap=self.cmap)
        # plt.draw() 
        # plt.pause(0.001)