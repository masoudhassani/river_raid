import pygame as pg
import yaml
import random
import time
from modules import InitDeck
from modules import Entity, Player, Enemy, Bullet, Walls

class CovidRaid:
    def __init__(self, preset='Basic', block_size=5, init_enemy_spawn=50,
                init_prop_spawn=150):

        # member variables from arg
        self.enemy_spawn_distance = init_enemy_spawn   #  spawn distance in pixel,lower means more enemy is spawned 
        self.prop_spawn_distance = init_prop_spawn
        self.people_spawn_distance = init_enemy_spawn   #  spawn distance in pixel,lower means more people is spawned 


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
        self.enemy_names = ['human-v2']
        self.prop_names = ['house1']      
        self.people_names = ['human1','human2','human3']    
        self.tree_names = ['trees1','trees2','trees3','trees4','trees5']  
        self.car_names = ['car1','car2','car3','car4','car5']  
        # box collision geometry dimension
        self.cg = {
            'player': (50,69),
            'bullet': (23,16),
            'human-v2': (50,69),
            'people': (50,69),
            'prop': (225,225),
            'tree':(200,200),
            'car':(160,310)
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
                        cg=self.cg['player'], pos=init_player_pos, icons=['media/covid/icon/elham.png','media/covid/icon/virus.png'], 
                        v_speed=self.settings['player_speed'], h_speed=self.settings['player_speed']*2,
                        sound_list=['media/covid/sound/walking.wav'])

        self.bullet = Bullet(scr=self.screen, name='bullet', ent_type='bullet', 
                        cg=self.cg['bullet'], pos=init_bullet_pos, icons=['media/covid/icon/mask.png'], 
                        v_speed=self.settings['player_speed']*bullet_speed_factor, h_speed=0, 
                        player_cg=self.cg['player'], sound_list=['media/covid/sound/bullet.wav']) 

        # setup walls 
        self.walls = Walls(scr=self.screen, color=(45,135,10), icons=[], normal=250, extended=100, channel=200, 
                            max_island=self.settings['width']-200, min_island=200, spawn_dist=800, length=1000, randomness=1, 
                            v_speed=self.settings['player_speed'], block_size=block_size, symmetric=False)

        # initialization
        self.randomizer = 200
        self.enemies = []
        self.peoples = []
        self.props = []
        self.explosions = []
        self.is_running = True
        self.travel_distance = 0
        self.last_enemey_spawn = 0
        self.last_people_spawn = 0
        self.last_prop_spawn = 0  
        self.last_car_spawn = 0
        self.last_tree_spawn = 0    
        self.lives_left = self.settings['num_lives']
        self.reset = False
        self.game_paused = False
        self.cars = []

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
                            cg=self.cg[enemy_name], pos=[pos_h, 0], icons=['media/covid/icon/{}.png'.format(enemy_name)],
                            v_speed=self.settings['player_speed']*1.5, h_speed=self.settings['enemy_speed']*vel_h*0.5)
            self.enemies.append(enemy)
            enemy.set_walls(wall)

    def create_trees(self):
        tree_name = random.choice(self.tree_names) 

        # get the wall coordinate at y=0 for spawning 
        wall = self.walls.return_wall_coordinate(0)

        tree = Enemy(scr=self.screen, name=tree_name, ent_type='tree', 
                        cg=self.cg['tree'], pos=[0, 0], icons=['media/covid/icon/{}.png'.format(tree_name)],
                        v_speed=self.settings['player_speed'], h_speed=0)
        self.props.append(tree)
        tree.set_walls(wall)

    def create_cars(self):
        car_name = random.choice(self.car_names) 

        # get the wall coordinate at y=0 for spawning 
        wall = self.walls.return_wall_coordinate(0)

        car = Enemy(scr=self.screen, name=car_name, ent_type='car', 
                        cg=self.cg['car'], pos=[570, 0], icons=['media/covid/icon/{}.png'.format(car_name)],
                        v_speed=self.settings['player_speed'], h_speed=0)
        self.cars.append(car)
        car.set_walls(wall)

    def create_people(self):
        people_name = random.choice(self.people_names) 

        # get the wall coordinate at y=0 for spawning 
        wall_1 = self.walls.return_wall_coordinate(0)
        # get the wall coordinate at the bottom of CG for spawning 
        wall_2 = self.walls.return_wall_coordinate(self.cg['people'][1]*3)
        # select the correct wall size 
        if wall_1[0] >= wall_2[0]:
            wall = wall_1
            pos_h = random.randint(wall[0],wall[1]-self.cg['people'][0])
            vel_h = random.randint(0,1)
            people = Enemy(scr=self.screen, name=people_name, ent_type='people', 
                            cg=self.cg['people'], pos=[pos_h, 0], icons=['media/covid/icon/{}.png'.format(people_name)],
                            v_speed=self.settings['player_speed']*1.5, h_speed=self.settings['enemy_speed']*vel_h*0)
            self.peoples.append(people)
            people.set_walls(wall)


    def enemy_collision(self):
        for e in self.enemies:
            # if the bullet hits the enemy
            if self.bullet.pos[1] <= e.pos[1]+e.cg[1] and self.bullet.pos[1]+self.bullet.cg[1] >= e.pos[1]:
                if self.bullet.pos[0] < e.pos[0]+e.cg[0] and self.bullet.pos[0]+self.bullet.cg[0]> e.pos[0]:
                    self.bullet.reload()
                    e.alive = False
                    explosion = Entity(scr=self.screen, name='explosion', ent_type='explosion', 
                        cg=self.cg['player'], pos=e.pos, icons=['media/covid/icon/human-v-mask.png'],
                        v_speed=self.settings['player_speed']*1.5, h_speed=0, life_span=1000,
                        sound_list=['media/covid/sound/bullet.wav'])

                    self.explosions.append(explosion)
                    self.score_value += 60
                    if e.name == 'helicopter':
                        self.score_value += 60
                    elif e.name == 'ship':
                        self.score_value += 40

            # if the player hits the enemy
            if self.player.pos[1] <= e.pos[1]+e.cg[1] and self.player.pos[1]+self.player.cg[1] >= e.pos[1]:
                if self.player.pos[0] < e.pos[0]+e.cg[0] and self.player.pos[0]+self.player.cg[0]> e.pos[0]:
                    e.alive = False
                    self.player.alive = False
                    self.lives_left -= 1
                    explosion = Entity(scr=self.screen, name='explosion', ent_type='explosion', 
                        cg=self.cg['player'], pos=[(e.pos[0]+self.player.pos[0])/2,(e.pos[1]+self.player.pos[1])/2], 
                        icons=['media/covid/icon/virus.png'], v_speed=self.settings['player_speed'], 
                        h_speed=0, life_span=100, sound_list=['media/covid/sound/explosion.wav']) 

                    self.explosions.append(explosion)  
                    if e.name == 'helicopter':
                        self.score_value += 60
                    elif e.name == 'ship':
                        self.score_value += 40

                    return True 
            
        return False

    def wall_collision(self):
        wall = self.walls.return_wall_coordinate(self.player.pos[1])
        # left wall collision
        if self.player.pos[0] <= wall[0]:
            self.player.pos[0] = wall[0]
        
        # right wall collision 
        if self.player.pos[0] + self.player.cg[0] >= wall[1]:
            self.player.pos[0] = wall[1] - self.player.cg[0]
        

    def show_score(self):
        # render the display
        score = self.font_small.render('Score: {}'.format(self.score_value), True, (255,255,255))
        self.screen.blit(score, (10, 20))  

    def show_travel(self):
        # render the display
        travel = self.font_small.render('Travel: {} m'.format(int(self.travel_distance/100)), True, (255,255,255))
        self.screen.blit(travel, (10, 100))  

    def show_lives(self):
        # render the display
        lives = self.font_small.render('Lives: {}'.format(int(self.lives_left)), True, (255,255,255))
        self.screen.blit(lives, (10, 60)) 

    def show_on_screen(self, val, x, y, color=(255,255,255)):
        render = self.font_large.render(str(val), True, color)
        self.screen.blit(render, (x, y))         

    def reset_game(self, delay):
        paused = True
        timer = 0
        t0 = int(time.time()*1000.0)
        for e in self.explosions:
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
    def update(self):
        
        # setup screen color
        self.screen.fill(self.background)

        keys = pg.key.get_pressed() 

        events = pg.event.get()
        for event in events:
            if event.type == pg.QUIT:
                self.is_running = False  
            elif event.type == pg.KEYDOWN:
                if event.key == pg.K_p:
                    self.game_paused = True

        if self.game_paused:
            self.pause_game()

        # draw walls
        self.walls.update(keys)

        # check for collision between player, enemies, bullet and walls
        enemy_col = self.enemy_collision()
        self.wall_collision()

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

        ### PEOPLE #################################################
        # update enemy list 
        self.peoples = [x for x in self.peoples if x.is_active()]

        # remove peoples that are dead or out of screen
        for e in self.peoples:
            if not e.is_active():
                del e 

        if (self.travel_distance-self.last_people_spawn) > self.randomizer:
            self.last_people_spawn = self.travel_distance
            self.randomizer = random.randint(self.people_spawn_distance*0.5, self.people_spawn_distance*1.5)
            self.create_people()
        ############################################################

        ### PROP #################################################
        # update prop list 
        self.props = [x for x in self.props if x.is_active()]
        self.cars = [x for x in self.cars if x.is_active()]

        # remove props that are dead or out of screen
        for p in self.props:
            if not p.is_active():
                del p

        for p in self.cars:
            if not p.is_active():
                del p

        if (self.travel_distance-self.last_tree_spawn) > 150:
            self.last_tree_spawn = self.travel_distance
            self.create_trees()

        if (self.travel_distance-self.last_car_spawn) > 300:
            self.last_car_spawn = self.travel_distance
            self.create_cars()
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

        for c in self.cars:
            c.update(keys)  

        for e in self.enemies: 
            e.update(keys)     

        for p in self.peoples: 
            p.update(keys)    

        self.explosions = [x for x in self.explosions if x.is_active()]

        # remove enemies that are dead or out of screen
        for e in self.explosions:
            e.update(keys)
            if not e.is_active():
                del e   

        self.show_score()
        self.show_lives()
        self.clock.tick(self.FPS)
        self.show_travel()
        pg.display.update()

        if enemy_col:
            if self.lives_left < 1:
                self.is_running = False
            else:
                self.reset = True

        if self.reset:
            self.reset_game(2000)
            self.player.reset()
            keys = ()
            self.reset = False 

        return self.is_running
