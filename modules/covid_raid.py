import pygame as pg
import yaml
import random
import time
from modules import InitDeck
from modules import Entity, Player, Enemy, Bullet, Walls, ActionSpace

class CovidRaid:
    def __init__(self, preset='Basic', ai_agent=False, init_enemy_spawn=20, init_people_spawn=20,
                init_prop_spawn=150, init_fuel_spawn=1000):

        # member variables from arg
        self.enemy_spawn_distance = init_enemy_spawn   #  spawn distance in pixel,lower means more enemy is spawned 
        self.prop_spawn_distance = init_prop_spawn
        self.people_spawn_distance = init_people_spawn   #  spawn distance in pixel,lower means more people is spawned 
        self.fuel_spawn_distance = init_fuel_spawn
        self.ai_agent = ai_agent

        # initialize the pygame library
        pg.mixer.pre_init(16000, -16, 5, 640)
        pg.mixer.init()
        # play backgraound music
        pg.mixer.music.load('media/covid/sound/outside.wav')
        pg.mixer.music.play(-1)
        # pg.mixer.set_num_channels(10)
        pg.init()

        # initialize clock
        self.clock = pg.time.Clock()
        self.FPS = 60

        # initialize the score and its font
        self.score_value = 0
        self.font_small = pg.font.Font('freesansbold.ttf', 16)
        self.font_large = pg.font.Font('freesansbold.ttf', 48)

        # load game settings 
        loader = InitDeck(preset=preset)
        self.settings = loader.load()

        # hard coded game settings
        player_name = 'player'
        self.enemy_names = ['human1','human2','human3','human4','human5','human6','human7','human8','human9','human10']
        self.prop_names = ['house1']      
        self.people_names = ['human1-mask','human2-mask','human3-mask','human4-mask','human5-mask','human6-mask','human7-mask','human8-mask','human9-mask','human10-mask']    
        self.tree_names = ['trees1','trees2','trees3','trees4','trees5']  
        self.car_names = ['car1','car2','car3','car4','car5']  
        # box collision geometry dimension
        self.cg = {
            'player': (50,69),
            'bullet': (23,16),
            'human': (50,69),
            'prop': (225,225),
            'tree':(200,200),
            'car':(160,310),
            'fuel': (64,64)
        }

        # setup the game display and title
        self.screen = pg.display.set_mode((self.settings['width'], self.settings['height']))
        pg.display.set_caption('Covid Raid 2020')
        icon = pg.image.load('media/covid/icon/virus.png')
        pg.display.set_icon(icon)
        self.background = ((100, 89, 89))   # screen background color RGB 

        # setup player and bullet
        init_player_pos = [self.settings['width']/2 - self.cg['player'][0]/2, self.settings['height']-100]
        init_bullet_pos = [self.settings['width']/2 - self.cg['bullet'][0]/2, init_player_pos[1]]
        bullet_speed_factor = 6
        self.player = Player(scr=self.screen, name=player_name, ent_type='player', 
                        cg=self.cg['player'], pos=init_player_pos, icon_list=['media/covid/icon/elham.png','media/covid/icon/virus.png'], 
                        v_speed=self.settings['player_speed'], h_speed=self.settings['player_speed'],
                        sound_list=['media/covid/sound/walking.wav', 'media/sound/engine-fast.wav', 'media/sound/engine-slow.wav',
                        'media/sound/fuel-up.wav', 'media/sound/fuel-low.wav', 'media/sound/tank-filled.wav'],
                        capacity=20000, dec_factor=1, inc_factor=6, low_fuel=0.2)

        self.bullet = Bullet(scr=self.screen, name='bullet', ent_type='bullet', 
                        cg=self.cg['bullet'], pos=init_bullet_pos, icon_list=['media/covid/icon/mask.png'], 
                        v_speed=self.settings['player_speed']*bullet_speed_factor, h_speed=0, 
                        player_cg=self.cg['player'], sound_list=['media/covid/sound/bullet.wav']) 

        # setup walls 
        self.walls = Walls(scr=self.screen, color=(45,135,10), icon_list=[], normal=150, extended=100, channel=200, 
                            max_island=self.settings['width']-200, min_island=200, spawn_dist=800, length=1000, randomness=1, 
                            v_speed=self.settings['player_speed'], block_size=self.settings['player_speed'], symmetric=False)

        # initialization
        self.randomizer = 200
        self.fuel_randomizer = 200
        self.enemies = []
        self.peoples = []
        self.trees = []
        self.explosions = []
        self.fuels = []
        self.is_running = True
        self.travel_distance = 0
        self.last_enemey_spawn = 0
        self.last_people_spawn = 0
        self.last_prop_spawn = 0  
        self.last_car_spawn = 0
        self.last_tree_spawn = 0   
        self.last_fuel_spawn = 0 
        self.lives_left = self.settings['num_lives']
        self.restart = False
        self.game_paused = False
        self.cars = []

        # initialization for ai agent 
        self.action_space = ActionSpace()

    def create_enemies(self):
        # update enemy list 
        self.enemies = [x for x in self.enemies if x.is_active()]

        # remove enemies that are dead or out of screen
        for e in self.enemies:
            if not e.is_active():
                del e 

        if (self.travel_distance-self.last_enemey_spawn) > self.randomizer:
            self.last_enemey_spawn = self.travel_distance
            self.randomizer = random.randint(self.enemy_spawn_distance*0.5, self.enemy_spawn_distance*1.5)

            enemy_name = random.choice(self.enemy_names) 

            # get the wall coordinate at y=0 for spawning 
            wall_1 = self.walls.return_wall_coordinate(0)
            # get the wall coordinate at the bottom of CG for spawning 
            wall_2 = self.walls.return_wall_coordinate(self.cg['human'][1]*3)
            # select the correct wall size 
            if wall_1[0] >= wall_2[0]:
                wall = wall_1
                pos_h = random.randint(wall[0],wall[1]-self.cg['human'][0])
                vel_h = random.randint(0,1)
                enemy = Enemy(scr=self.screen, name=enemy_name, ent_type='enemy', 
                                cg=self.cg['human'], pos=[pos_h, 0], icon_list=['media/covid/icon/{}.png'.format(enemy_name)],
                                v_speed=self.settings['player_speed']*1.5, h_speed=self.settings['enemy_speed']*vel_h*0.5)
                self.enemies.append(enemy)
                enemy.set_walls(wall)

    def create_trees(self):
        # update trees list 
        self.trees = [x for x in self.trees if x.is_active()]

        # remove trees that are dead or out of screen
        for p in self.trees:
            if not p.is_active():
                del p

        if (self.travel_distance-self.last_tree_spawn) > 150:
            self.last_tree_spawn = self.travel_distance
            tree_name = random.choice(self.tree_names)

            # get the wall coordinate at y=0 for spawning 
            wall = self.walls.return_wall_coordinate(0)

            tree = Enemy(scr=self.screen, name=tree_name, ent_type='tree',
                            cg=self.cg['tree'], pos=[0, 0], icon_list=['media/covid/icon/{}.png'.format(tree_name)],
                            v_speed=self.settings['player_speed'], h_speed=0)
            self.trees.append(tree)
            tree.set_walls(wall)

    def create_cars(self):
        self.cars = [x for x in self.cars if x.is_active()]

        # remove cars that are dead or out of screen
        for p in self.cars:
            if not p.is_active():
                del p

        if (self.travel_distance-self.last_car_spawn) > 300:
            self.last_car_spawn = self.travel_distance
            car_name = random.choice(self.car_names) 

            # get the wall coordinate at y=0 for spawning 
            wall = self.walls.return_wall_coordinate(0)

            car = Enemy(scr=self.screen, name=car_name, ent_type='car', 
                            cg=self.cg['car'], pos=[670, 0], icon_list=['media/covid/icon/{}.png'.format(car_name)],
                            v_speed=self.settings['player_speed'], h_speed=0)
            self.cars.append(car)
            car.set_walls(wall)

    def create_people(self):
        # update enemy list 
        self.peoples = [x for x in self.peoples if x.is_active()]

        # remove peoples that are dead or out of screen
        for e in self.peoples:
            if not e.is_active():
                del e 

        if (self.travel_distance-self.last_people_spawn) > self.randomizer:
            self.last_people_spawn = self.travel_distance
            self.randomizer = random.randint(self.people_spawn_distance*0.5, self.people_spawn_distance*0.8)
            people_name = random.choice(self.people_names) 

            # get the wall coordinate at y=0 for spawning 
            wall_1 = self.walls.return_wall_coordinate(0)
            # get the wall coordinate at the bottom of CG for spawning 
            wall_2 = self.walls.return_wall_coordinate(self.cg['human'][1]*3)
            # select the correct wall size 
            if wall_1[0] >= wall_2[0]:
                wall = wall_1
                pos_h = random.randint(wall[0],wall[1]-self.cg['human'][0])
                vel_h = random.randint(0,1)
                people = Enemy(scr=self.screen, name=people_name, ent_type='people', 
                                cg=self.cg['human'], pos=[pos_h, 0], icon_list=['media/covid/icon/{}.png'.format(people_name)],
                                v_speed=self.settings['player_speed']*1.5, h_speed=self.settings['enemy_speed']*vel_h*0)
                self.peoples.append(people)
                people.set_walls(wall)

    def create_fuels(self):
        # update fuel list 
        self.fuels = [x for x in self.fuels if x.is_active()]

        # remove props that are dead or out of screen
        for f in self.fuels:
            if not f.is_active():
                del f

        if (self.travel_distance-self.last_fuel_spawn) > self.fuel_randomizer:
            self.last_fuel_spawn = self.travel_distance
            self.fuel_randomizer = random.randint(self.fuel_spawn_distance*0.6, self.fuel_spawn_distance*1.5)
            # get the wall coordinate at y=0 for spawning 
            wall_1 = self.walls.return_wall_coordinate(0)
            # get the wall coordinate at the bottom of CG for spawning 
            wall_2 = self.walls.return_wall_coordinate(self.cg['fuel'][1]*2.5)
            # select the correct wall size 
            if wall_1[0] >= wall_2[0]:
                wall = wall_1
                pos_h = wall[0] # or wall[1]-self.cg['fuel'][0]
                fuel = Enemy(scr=self.screen, name='fuel', ent_type='fuel', 
                                cg=self.cg['fuel'], pos=[pos_h, 0], icon_list=['media/covid/icon/fuel.png'],
                                v_speed=self.settings['player_speed'], h_speed=0)
                self.fuels.append(fuel)
                fuel.set_walls(wall)


    def enemy_collision(self):
        for e in self.enemies:
            # if the bullet hits the enemy
            if self.bullet.pos[1] <= e.pos[1]+e.cg[1] and self.bullet.pos[1]+self.bullet.cg[1] >= e.pos[1]:
                if self.bullet.pos[0] < e.pos[0]+e.cg[0] and self.bullet.pos[0]+self.bullet.cg[0]> e.pos[0]:
                    self.bullet.reload()
                    e.alive = False
                    explosion = Entity(scr=self.screen, name='explosion', ent_type='explosion', 
                        cg=self.cg['player'], pos=e.pos, icon_list=['media/covid/icon/{}-mask.png'.format(e.name)],
                        v_speed=self.settings['player_speed']*1.5, h_speed=0, life_span=1000)

                    self.explosions.append(explosion)
                    self.score_value += 60

            # if the player hits the enemy
            if self.player.pos[1] <= e.pos[1]+e.cg[1] and self.player.pos[1]+self.player.cg[1] >= e.pos[1]:
                if self.player.pos[0] < e.pos[0]+e.cg[0] and self.player.pos[0]+self.player.cg[0]> e.pos[0]:
                    e.alive = False
                    self.player.alive = False
                    self.lives_left -= 1
                    explosion = Entity(scr=self.screen, name='explosion', ent_type='explosion', 
                        cg=self.cg['player'], pos=[(e.pos[0]+self.player.pos[0])/2,(e.pos[1]+self.player.pos[1])/2], 
                        icon_list=['media/covid/icon/virus.png'], v_speed=self.settings['player_speed'], 
                        h_speed=0, life_span=100, sound_list=['media/covid/sound/explosion.wav']) 

                    self.explosions.append(explosion)  
                    if e.name == 'helicopter':
                        self.score_value += 60
                    elif e.name == 'ship':
                        self.score_value += 40


    def wall_collision(self):
        wall = self.walls.return_wall_coordinate(self.player.pos[1])
        # left wall collision
        if self.player.pos[0] <= wall[0]:
            self.player.pos[0] = wall[0]
        
        # right wall collision 
        if self.player.pos[0] + self.player.cg[0] >= wall[1]:
            self.player.pos[0] = wall[1] - self.player.cg[0]
        

    def fuel_collision(self):
        collision = False
        for f in self.fuels:
            # if the player passing on fuel tanks 
            if self.player.pos[1] <= f.pos[1]+f.cg[1] and self.player.pos[1]+self.player.cg[1] >= f.pos[1]:
                if self.player.pos[0] < f.pos[0]+f.cg[0] and self.player.pos[0]+self.player.cg[0]> f.pos[0]:
                    collision = True 
   
        
        return collision

    def show_score(self):
        # render the display
        score = self.font_small.render('Score: {}'.format(self.score_value), True, (255,255,255))
        self.screen.blit(score, (10, 20))  

    def show_travel(self):
        # render the display
        travel = self.font_small.render('Travel: {} m'.format(int(self.travel_distance/100)), True, (255,255,255))
        self.screen.blit(travel, (10, 80))  

    def show_lives(self):
        # render the display
        lives = self.font_small.render('Lives: {}'.format(int(self.lives_left)), True, (255,255,255))
        self.screen.blit(lives, (10, 40)) 

    def show_fuel(self):
        # render the display
        fuel = self.font_small.render('Fuel: {} %'.
                format(int(self.player.fuel*100/self.player.capacity)), True, (255,255,255))
        self.screen.blit(fuel, (10, 60)) 

    def show_on_screen(self, val, x, y, color=(255,255,255)):
        render = self.font_large.render(str(val), True, color)
        self.screen.blit(render, (x, y))         

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
    main class method
    '''
    def step(self, action):
        
        self.clock.tick(self.FPS)

        ### RESTART #################################################
        if self.restart:
            self.restart_game(2000)
            self.player.reset()
            self.restart = False 
            return self.is_running
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
            self.action_space.available_actions(condition=self.bullet.state == 'fired')
        ############################################################  

        ### COLLISIONS #################################################
        self.walls.update(action, self.ai_agent)
        self.enemy_collision()
        self.wall_collision()
        ############################################################ 

        ### ENEMY #################################################
        self.create_enemies()
        ############################################################

        ### PEOPLE #################################################
        self.create_people()
        ############################################################

        ### TREES and CARS ################################################
        self.create_trees()
        self.create_cars()
        ###################################################################

        ### FUEL #################################################
        self.create_fuels()

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
        for p in self.trees:
            p.update(action, self.ai_agent)

        for c in self.cars:
            c.update(action, self.ai_agent) 

        for e in self.enemies: 
            e.update(action, self.ai_agent)   

        for p in self.peoples: 
            p.update(action, self.ai_agent)   

        for f in self.fuels:
            f.update(action, self.ai_agent) 

        close_enemies = 0
        for e in self.enemies+self.explosions+self.peoples:
            p = self.player.center()
            d = ((e.center()[0]-p[0])**2 + (e.center()[1]-p[1])**2)**0.5
            if d < 200:
                close_enemies += 1

        # update player position
        self.player.set_walls(self.walls.return_wall_coordinate(self.player.pos[1]))
        self.travel_distance = self.player.update(action, self.ai_agent, self.fuel_collision(), close_enemies) 
        
        # update bullet 
        self.bullet.update(action, self.ai_agent, self.player.pos)        

        self.explosions = [x for x in self.explosions if x.is_active()]
        # remove enemies that are dead or out of screen
        for e in self.explosions:
            e.update(action, self.ai_agent)
            if not e.is_active():
                del e   
        ############################################################ 

        ### GAME END ################################################# 
        if self.lives_left < 1:
            self.is_running = False
        elif not self.player.alive:
            self.restart = True
        ############################################################ 

        return self.is_running

    '''
    reset all game metrics and variable 
    '''
    def reset(self):
        self.randomizer = 200
        self.fuel_randomizer = 200
        self.enemies = []
        self.peoples = []
        self.trees = []
        self.explosions = []
        self.fuels = []
        self.is_running = True
        self.travel_distance = 0
        self.last_enemey_spawn = 0
        self.last_people_spawn = 0
        self.last_prop_spawn = 0  
        self.last_car_spawn = 0
        self.last_tree_spawn = 0   
        self.last_fuel_spawn = 0 
        self.lives_left = self.settings['num_lives']
        self.restart = False
        self.cars = []
        self.game_paused = False 
        self.score_value = 0       

    '''
    render the game environment on screen
    '''
    def render(self):
        # setup screen color
        self.screen.fill(self.background)

        # render walls 
        self.walls.render()

        # render all entities 
        for p in self.trees+self.cars+self.peoples:
            p.render()  

        for f in self.fuels:
            f.render()  

        for e in self.enemies: 
            e.render()    

        self.player.render() 
        self.bullet.render()   

        for e in self.explosions:
            e.render()

        # show game metrics
        self.show_score()
        self.show_lives()
        self.show_travel()
        self.show_fuel()

        # render all objects
        pg.display.update()
