import csv
import random as _random

import numpy as np
import pygame as pg

from ..assets import Audio, asset_path, image
from ..settings import load_settings
from .actions import ActionSpace
from .bullet import Bullet
from .enemy import Enemy
from .entity import Entity
from .player import Player
from .walls import Walls


class RiverRaid:
    '''
    The River Raid game engine. step() advances the game by exactly one frame.

    render_mode=None runs completely headless (no window, no sound, no frame rate
    limit) which is what RL training uses. render_mode='human' opens a window and
    runs at 30 FPS.
    '''
    FPS = 30

    # box collision geometry dimension
    cg = {
        'player': (28, 26),
        'bullet': (2, 14),
        'helicopter': (32, 20),
        'ship': (64, 20),
        'prop': (64, 64),
        'fuel': (32, 56),
    }
    points = {'helicopter': 60, 'ship': 40, 'fuel': 80}
    enemy_names = ['helicopter', 'ship']
    prop_names = ['prop1', 'prop2', 'prop3']
    background = (20, 50, 255)   # screen background color RGB

    def __init__(self, preset='Basic', render_mode=None, random=True, init_enemy_spawn=150,
                 init_prop_spawn=150, init_fuel_spawn=500, sound=None, num_lives=None, seed=None,
                 fuel_capacity=50000, refuel_rate=30):

        # spawn distances in pixel, lower means more assets are spawned
        self.enemy_spawn_distance = init_enemy_spawn
        self.prop_spawn_distance = init_prop_spawn
        self.fuel_spawn_distance = init_fuel_spawn
        self.random_assets = random
        self.fuel_capacity = fuel_capacity   # the plane burns player_speed (4) fuel per frame
        self.refuel_rate = refuel_rate       # fuel gained per frame over a fuel tank
        self.render_mode = render_mode
        self.rng = _random.Random(seed)

        # load game settings
        self.settings = load_settings(preset)
        if num_lives is not None:
            self.settings['num_lives'] = num_lives
        width, height = self.settings['width'], self.settings['height']

        if render_mode == 'human':
            pg.init()
            self.screen = pg.display.set_mode((width, height))
            pg.display.set_caption('River Raid')
            pg.display.set_icon(image('media/icon/jetfighter.png'))
            self.clock = pg.time.Clock()
            self.font_small = self._font(16)
            self.font_large = self._font(48)
        else:
            # off-screen canvas, nothing is shown
            self.screen = pg.Surface((width, height))

        use_sound = self.settings['sound'] if sound is None else sound
        self.audio = Audio(enabled=use_sound and render_mode == 'human')
        self.action_space = ActionSpace()

        #### DETERMINISTIC GAME ##################################
        if not self.random_assets:
            with open(asset_path('media/assets-position.csv')) as f:
                reader = csv.reader(f)
                next(reader)   # skip header
                self.assets = {}   # travel distance -> list of (entity, pos_h, vel_h)
                for row in reader:
                    self.assets.setdefault(int(row[1]), []).append((row[0], int(row[2]), int(row[3])))

        self.reset()

    @staticmethod
    def _font(size):
        pg.font.init()
        try:
            return pg.font.Font('freesansbold.ttf', size)
        except (FileNotFoundError, OSError):
            return pg.font.Font(None, size)

    def seed(self, seed):
        self.rng.seed(seed)

    '''
    reset all game metrics and variables
    this is also called when the game is initialized
    '''
    def reset(self, seed=None):
        if seed is not None:
            self.rng.seed(seed)
        speed = self.settings['player_speed']

        #### PLAYER ##############################################
        init_player_pos = [self.settings['width']/2, self.settings['height']-50]
        self.player = Player(scr=self.screen, name='player', ent_type='player',
                             cg=self.cg['player'], pos=init_player_pos,
                             icon_list=['media/icon/jetfighter.png', 'media/icon/explosion2.png'],
                             v_speed=speed, h_speed=speed,
                             sound_list=['media/sound/engine.wav', 'media/sound/engine-fast.wav',
                                         'media/sound/engine-slow.wav', 'media/sound/fuel-up.wav',
                                         'media/sound/fuel-low.wav', 'media/sound/tank-filled.wav'],
                             capacity=self.fuel_capacity, dec_factor=1, inc_factor=self.refuel_rate, low_fuel=0.2, audio=self.audio)

        #### BULLET ##############################################
        bullet_speed_factor = 5
        self.bullet = Bullet(scr=self.screen, name='bullet', ent_type='bullet',
                             cg=self.cg['bullet'], pos=init_player_pos, icon_list=['media/icon/bullet.png'],
                             v_speed=speed*bullet_speed_factor, h_speed=0,
                             player_cg=self.cg['player'], sound_list=['media/sound/bullet.wav'], audio=self.audio)

        #### WALLS ###############################################
        self.walls = Walls(scr=self.screen, color=(45, 135, 10), icon_list=[], normal=200, extended=100, channel=350,
                           max_island=self.settings['width']-200, min_island=200, spawn_dist=800, length=1000,
                           randomness=0.8 if self.random_assets else 1,
                           v_speed=speed, block_size=speed, rng=self.rng)

        self.enemy_randomizer = self.enemy_spawn_distance
        self.prop_randomizer = self.prop_spawn_distance
        self.fuel_randomizer = self.fuel_spawn_distance
        self.enemies = []
        self.props = []
        self.explosions = []
        self.fuels = []
        self.is_running = True
        self.travel_distance = 0
        self.last_enemy_spawn = 0
        self.last_prop_spawn = 0
        self.last_fuel_spawn = 0
        self.lives_left = self.settings['num_lives']
        self.game_paused = False
        self.score_value = 0
        self.refueling = False   # True while the player is over a fuel tank
        self.kills = 0
        self.ram_points = 0      # points earned by crashing into enemies (not shooting them)
        self.frame = 0

    def _spawn(self, name, ent_type, pos, h_speed=0, icon=None):
        entity = Enemy(scr=self.screen, name=name, ent_type=ent_type, cg=self.cg[ent_type if ent_type != 'enemy' else name],
                       pos=pos, icon_list=[icon or 'media/icon/{}.png'.format(name)],
                       v_speed=self.settings['player_speed'], h_speed=h_speed, audio=self.audio)
        return entity

    def _explode(self, pos, icon='explosion2'):
        self.explosions.append(Entity(scr=self.screen, name='explosion', ent_type='explosion',
                                      cg=self.cg['player'], pos=pos, icon_list=['media/icon/{}.png'.format(icon)],
                                      v_speed=self.settings['player_speed'], h_speed=0, life_span=100,
                                      sound_list=['media/sound/explosion.wav'], audio=self.audio))

    def kill_player(self, pos=None):
        if not self.player.alive:
            return
        self.player.alive = False
        self.lives_left -= 1
        self._explode(pos or [self.player.pos[0], self.player.pos[1]], icon='explosion1')

    '''
    creates enemies with a random horizontal position
    '''
    def create_enemies(self, data=None):
        self.enemies = [x for x in self.enemies if x.is_active()]

        if not self.random_assets:
            if data is not None:
                enemy_name, pos_h, vel_h = data
                enemy = self._spawn(enemy_name, 'enemy', [pos_h, 0], self.settings['enemy_speed']*vel_h)
                enemy.set_walls(self.walls.return_wall_coordinate(0))
                self.enemies.append(enemy)

        elif (self.travel_distance-self.last_enemy_spawn) > self.enemy_randomizer:
            self.last_enemy_spawn = self.travel_distance
            self.enemy_randomizer = self.rng.randint(int(self.enemy_spawn_distance*0.5), int(self.enemy_spawn_distance*1.5))

            enemy_name = self.rng.choice(self.enemy_names)
            # get the wall coordinates at y=0 and at the bottom of the CG for spawning
            wall_1 = self.walls.return_wall_coordinate(0)
            wall_2 = self.walls.return_wall_coordinate(self.cg[enemy_name][1]*3)

            # do not spawn while the river narrows
            if wall_1[0] >= wall_2[0]:
                pos_h = self.rng.randint(wall_1[0], wall_1[1]-self.cg[enemy_name][0])
                vel_h = self.rng.randint(0, 1)
                enemy = self._spawn(enemy_name, 'enemy', [pos_h, 0], self.settings['enemy_speed']*vel_h)
                enemy.set_walls(wall_1)
                self.enemies.append(enemy)

    '''
    create props in random horizontal positions on the river banks
    player cannot interact with props since they are positioned outside of boundaries
    '''
    def create_props(self, data=None):
        self.props = [x for x in self.props if x.is_active()]

        if not self.random_assets:
            if data is not None:
                prop = self._spawn(self.rng.choice(self.prop_names), 'prop', [data[1], 0])
                prop.set_walls(self.walls.return_wall_coordinate(0))
                self.props.append(prop)

        elif (self.travel_distance-self.last_prop_spawn) > self.prop_randomizer:
            self.last_prop_spawn = self.travel_distance
            self.prop_randomizer = self.rng.randint(int(self.prop_spawn_distance*0.3), int(self.prop_spawn_distance*1.3))

            wall_1 = self.walls.return_wall_coordinate(0)
            wall_2 = self.walls.return_wall_coordinate(self.cg['prop'][1])
            wall = min(wall_1, wall_2)

            pos_h = self.rng.choice([self.rng.randint(0, wall[0]-self.cg['prop'][0]),
                                     self.rng.randint(wall[1], self.settings['width']-self.cg['prop'][0])])
            prop = self._spawn(self.rng.choice(self.prop_names), 'prop', [pos_h, 0])
            prop.set_walls(wall)
            self.props.append(prop)

    '''
    create fuel tanks in random horizontal positions
    '''
    def create_fuels(self, data=None):
        self.fuels = [x for x in self.fuels if x.is_active()]

        if not self.random_assets:
            if data is not None:
                fuel = self._spawn('fuel', 'fuel', [data[1], 0])
                fuel.set_walls(self.walls.return_wall_coordinate(0))
                self.fuels.append(fuel)

        elif (self.travel_distance-self.last_fuel_spawn) > self.fuel_randomizer:
            self.last_fuel_spawn = self.travel_distance
            self.fuel_randomizer = self.rng.randint(int(self.fuel_spawn_distance*0.3), int(self.fuel_spawn_distance*1.5))

            wall_1 = self.walls.return_wall_coordinate(0)
            wall_2 = self.walls.return_wall_coordinate(self.cg['fuel'][1]*2.5)
            if wall_1[0] >= wall_2[0]:
                pos_h = self.rng.randint(wall_1[0], wall_1[1]-self.cg['fuel'][0])
                fuel = self._spawn('fuel', 'fuel', [pos_h, 0])
                fuel.set_walls(wall_1)
                self.fuels.append(fuel)

    '''
    collision detection between enemies and player/bullet
    '''
    def enemy_collision(self):
        for e in self.enemies:
            if not e.alive:
                continue

            # if the bullet hits the enemy. Before 2021 an un-fired bullet (which sits on
            # top of the plane) could also "hit" enemies, giving free points.
            if self.bullet.state == 'fired' and self.bullet.overlaps(e):
                self.bullet.reload()
                e.alive = False
                self._explode(e.pos)
                self.score_value += self.points[e.name]
                self.kills += 1

            # if the player hits the enemy
            elif self.player.alive and self.player.overlaps(e):
                e.alive = False
                self.score_value += self.points[e.name]
                self.ram_points += self.points[e.name]
                self.kill_player([(e.pos[0]+self.player.pos[0])/2, (e.pos[1]+self.player.pos[1])/2])

    '''
    collision detection between player/bullet and walls
    '''
    def wall_collision(self):
        # if the bullet hits the wall, it will disappear and reload
        wall_3 = self.walls.return_wall_coordinate(self.bullet.pos[1])
        if self.bullet.pos[0] < wall_3[0] or self.bullet.pos[0]+self.bullet.cg[0] > wall_3[1]:
            self.bullet.reload()

        # if the player hits the wall
        wall_1 = self.walls.return_wall_coordinate(self.player.pos[1])
        wall_2 = self.walls.return_wall_coordinate(self.player.pos[1]+self.player.cg[1])
        x0, x1 = self.player.pos[0], self.player.pos[0]+self.player.cg[0]
        if x0 < wall_1[0] or x1 > wall_1[1] or x0 < wall_2[0] or x1 > wall_2[1]:
            self.kill_player()

    '''
    detect if player is passing over a fuel tank or a bullet has hit the tank
    '''
    def fuel_collision(self):
        collision = False
        for f in self.fuels:
            if not f.alive:
                continue

            # if the player is passing over a fuel tank
            if self.player.overlaps(f):
                collision = True

            # if the bullet hits the fuel tank
            if self.bullet.state == 'fired' and self.bullet.overlaps(f):
                self.bullet.reload()
                f.alive = False
                self._explode(f.pos)
                self.score_value += self.points['fuel']

        self.refueling = collision and self.player.alive
        return collision

    '''
    update the game based on the action. This is the main method that should be called every frame.
    action can be a string ('LEFT_SHOOT'), a list of strings (['LEFT', 'UP']) or an action index
    '''
    def step(self, action):
        if isinstance(action, (int, np.integer)):
            action = self.action_space.actions[action]
        self.frame += 1

        ### COLLISIONS #############################################
        self.walls.update(action)
        if self.player.alive:
            self.enemy_collision()
            self.wall_collision()

        ### SPAWN ##################################################
        if self.random_assets:
            self.create_enemies()
            self.create_props()
            self.create_fuels()

        # predefined asset positions based on a csv file
        else:
            self.create_enemies()
            self.create_fuels()
            self.create_props()
            for asset_data in self.assets.get(int(self.travel_distance), []):
                if asset_data[0] in self.enemy_names:
                    self.create_enemies(asset_data)
                elif asset_data[0] == 'fuel':
                    self.create_fuels(asset_data)
                elif asset_data[0] == 'prop':
                    self.create_props(asset_data)

        ### FUEL ZERO ##############################################
        if self.player.fuel <= 0:
            self.kill_player()

        ### UPDATE #################################################
        for p in self.props:
            p.update(action)

        for f in self.fuels:
            f.update(action)

        for e in self.enemies:
            e.update(action)

        self.bullet.update(action, self.player.pos)

        self.player.set_walls(self.walls.return_wall_coordinate(self.player.pos[1]))
        self.travel_distance = self.player.update(action, self.fuel_collision())

        self.explosions = [x for x in self.explosions if x.is_active()]
        for e in self.explosions:
            e.update(action)

        ### GAME END ###############################################
        if self.lives_left < 1:
            self.is_running = False

    '''
    restart after losing a life (human play)
    '''
    def restart_life(self):
        for e in self.explosions + self.enemies:
            e.alive = False
        self.player.reset()
        self.bullet.reload()

    '''
    draw the game world (without the score board) on the canvas
    '''
    def draw(self):
        self.screen.fill(self.background)
        self.walls.render()

        for f in self.fuels:
            f.render()

        for e in self.enemies:
            e.render()

        self.player.render()
        self.bullet.render()

        for p in self.props:
            p.render()

        for e in self.explosions:
            e.render()

        return self.screen

    '''
    grayscale, down-sampled observation of the playing field
    crop: x range of the screen that is kept, the player can never leave it
    '''
    def observation(self, size=(96, 96), crop=(100, 700)):
        self.draw()
        region = self.screen.subsurface((crop[0], 0, crop[1]-crop[0], self.settings['height']))
        # a cheap 2x nearest-neighbour pass first (the thinnest sprite, the bullet, is 2 px wide)
        half = pg.transform.scale(region, (region.get_width()//2, region.get_height()//2))
        small = pg.transform.smoothscale(half, size)
        rgb = pg.surfarray.pixels3d(small)   # (w, h, 3)
        gray = rgb[..., 0]*0.299 + rgb[..., 1]*0.587 + rgb[..., 2]*0.114
        del rgb   # release the surface lock
        return gray.T.astype(np.uint8)       # (h, w)

    def rgb_array(self):
        self.draw()
        return pg.surfarray.array3d(self.screen).transpose(1, 0, 2)

    def show_text(self, text, pos, large=False):
        font = self.font_large if large else self.font_small
        self.screen.blit(font.render(str(text), True, (255, 255, 255)), pos)

    '''
    draw the world plus the score board and show it in the window (human mode)
    '''
    def render(self):
        if self.render_mode != 'human':
            return
        self.draw()
        self.show_text('Score: {}'.format(self.score_value), (10, 20))
        self.show_text('Lives: {}'.format(int(self.lives_left)), (10, 40))
        self.show_text('Fuel: {} %'.format(int(self.player.fuel*100/self.player.capacity)), (10, 60))
        self.show_text('Travel: {} km'.format(int(self.travel_distance/1000)), (10, 80))
        pg.display.update()
        self.clock.tick(self.FPS)

    def handle_events(self):
        '''process window events, returns False if the window was closed'''
        for event in pg.event.get():
            if event.type == pg.QUIT:
                self.is_running = False
            elif event.type == pg.KEYDOWN and event.key == pg.K_p:
                self.game_paused = not self.game_paused
        return self.is_running

    def wait(self, ms):
        '''wait while keeping the window responsive'''
        end = pg.time.get_ticks() + ms
        while pg.time.get_ticks() < end and self.handle_events():
            pg.time.wait(10)

    '''
    play the game with the keyboard: arrows to move/accelerate, space to shoot, p to pause
    '''
    def play(self):
        assert self.render_mode == 'human', 'create the game with render_mode="human" to play'
        while self.handle_events():
            if self.game_paused:
                self.player.pause()
                self.show_text('PAUSED', (self.settings['width']/2 - 100, self.settings['height']/2), large=True)
                pg.display.update()
                self.clock.tick(self.FPS)
                continue

            self.step(self.action_space.decode_keys(pg.key.get_pressed()))
            self.render()

            if not self.is_running:
                self.show_text('GAME OVER', (self.settings['width']/2 - 140, self.settings['height']/2), large=True)
                pg.display.update()
                self.wait(3000)
                break
            if not self.player.alive:
                self.wait(2000)
                self.restart_life()

    def close(self):
        if self.render_mode == 'human':
            pg.display.quit()
