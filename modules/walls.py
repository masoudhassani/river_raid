import random 
import pygame as pg

class Walls:
    def __init__(self, scr, color, icons, normal, extended, channel, 
                    max_island, min_island, spawn_dist, length, randomness, 
                    v_speed, block_size):

        self.screen = scr 
        self.color = color 
        self.icons = icons 
        self.current_speed_v = v_speed  
        self.base_speed_v = v_speed
        self.normal = normal
        self.extended = extended 
        self.channel = channel
        self.wall_size = normal
        self.max_island = max_island
        self.min_island = min_island
        self.spawn_dist = spawn_dist
        self.length = length
        self.randomness = randomness
        self.block_size = block_size

        self.travel_total = 0     # total travel distance
        self.travel_per_wall = 0  # travel for each section of wall
        self.screen_height = scr.get_height()
        self.screen_width = scr.get_width()
        # self.wall_length = self.init_wall_length()
        self.walls = ()

    def update(self, keys):
        # handle speed
        if keys[pg.K_UP]:
            self.speed_up()
        elif keys[pg.K_DOWN]:
            self.slow_down()
        else:
            self.current_speed_v = self.base_speed_v

        self.create_wall()
        self.update_odometer()
        
        return self.walls

    def create_wall(self):
        if self.travel_per_wall == 0:
            self.wall_length = self.init_wall_length() 
        
        if self.travel_per_wall < self.wall_length:
            pg.draw.rect(self.screen, self.color, [0, 0, self.normal, self.screen_height])
            pg.draw.rect(self.screen, self.color, [self.screen_width-self.normal, 0, self.normal, self.screen_height])
            self.walls = ((self.normal, self.screen_width-self.normal),(self.normal, self.screen_width-self.normal))
        
        else:
            self.travel_per_wall = 0

    def speed_up(self):
        self.current_speed_v = self.base_speed_v * 2.0

    def slow_down(self):
        self.current_speed_v = self.base_speed_v / 2.0        

    def update_odometer(self):
        self.travel_total += self.current_speed_v
        self.travel_per_wall += self.current_speed_v

    # set RGB colors for the walls
    def set_color(self, color):
        self.color = color

    def mod(self, x, y):
        return x - int(x/y)*y

    def init_wall_length(self):
        random_length = random.randint(self.randomness*self.length, self.length*(2-self.randomness))
        random_length = int(random_length/self.block_size) * self.block_size

        return random_length