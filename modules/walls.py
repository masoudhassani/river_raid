import random 
import pygame as pg

class Walls:
    def __init__(self, scr, color, icon_list, normal, extended, channel, 
                    max_island, min_island, spawn_dist, length, randomness, 
                    v_speed, block_size, symmetric=True):

        self.screen = scr 
        self.color = color 
        self.icon_list = icon_list
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
        self.symmetric = symmetric

        self.travel_total = 0     # total travel distance
        self.travel_per_wall = 0  # travel for each section of wall
        self.screen_height = scr.get_height()
        self.screen_width = scr.get_width()
        self.channel_length = self.block_size*50
        self.channel_visible = False
        self.channel_passed = False
        self.wall_length = self.init_wall_length()
        self.walls = ()

    def update(self, action, ai):
        # if ai agent is playing 
        if ai:
            if action == 'UP':
                self.speed_up()
            elif action == 'DOWN':
                self.slow_down()
            else:
                self.current_speed_v = self.base_speed_v
        
        # if human is playing 
        else:
            # handle speed
            if 'UP' in action:
                self.speed_up()
            elif 'DOWN' in action:
                self.slow_down()
            else:
                self.current_speed_v = self.base_speed_v

        self.update_odometer()
        self.wall_logic()

    # wall logic for symmetric walls with channels and extensions 
    def wall_logic(self):
        if self.symmetric:
            if self.travel_per_wall == 0:
                self.wall_length = self.init_wall_length() 

            if self.travel_per_wall < self.wall_length - self.channel_length:
                self.channel_passed = True
                if not self.channel_visible:
                    pass
                else:
                    if self.travel_per_wall >= self.screen_height-self.block_size:
                        self.channel_visible = False

            else:
                self.channel_passed = False
                self.channel_visible = True
                if self.travel_per_wall >= self.wall_length:
                    self.travel_per_wall = 0           

    def render(self):
        # symmetric walls with channels and extensions 
        if self.symmetric:

            if self.travel_per_wall < self.wall_length - self.channel_length:
                if not self.channel_visible:
                    pg.draw.rect(self.screen, self.color, [0, 0, self.normal, self.screen_height])
                    pg.draw.rect(self.screen, self.color, [self.screen_width-self.normal, 0, self.normal, self.screen_height])
                
                else:
                    pg.draw.rect(self.screen, self.color, [0, self.travel_per_wall, self.channel, self.channel_length])
                    pg.draw.rect(self.screen, self.color, [self.screen_width-self.channel, self.travel_per_wall, self.channel, self.channel_length])   
                    pg.draw.rect(self.screen, self.color, [0, self.travel_per_wall+self.channel_length, self.normal, 
                                                            self.screen_height-(self.travel_per_wall+self.channel_length)])
                    pg.draw.rect(self.screen, self.color, [self.screen_width-self.normal, self.travel_per_wall+self.channel_length, self.normal, 
                                                            self.screen_height-(self.travel_per_wall+self.channel_length)])
                    pg.draw.rect(self.screen, self.color, [0, 0, self.normal, self.travel_per_wall])
                    pg.draw.rect(self.screen, self.color, [self.screen_width-self.normal, 0, self.normal, self.travel_per_wall])   

            else:
                pos = self.travel_per_wall - (self.wall_length - self.channel_length)
                pg.draw.rect(self.screen, self.color, [0, 0, self.channel, pos])
                pg.draw.rect(self.screen, self.color, [self.screen_width-self.channel, 0, self.channel, pos])            
                pg.draw.rect(self.screen, self.color, [0, pos, self.normal, self.screen_height-pos])
                pg.draw.rect(self.screen, self.color, [self.screen_width-self.normal, pos, self.normal, self.screen_height-pos])     

        # simple wall without symmetry 
        else:
            pg.draw.rect(self.screen, self.color, [0, 0, self.channel, self.screen_height])
            pg.draw.rect(self.screen, [62,57,57], [self.screen_width-self.normal, 0, self.normal, self.screen_height])
                
      
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

    def return_wall_coordinate(self, y):
        if self.symmetric:
            # when a channel has been pass but in screen OR it has not appeared yet
            if self.channel_passed:
                # if channel is not visible in screen
                if not self.channel_visible:
                    return [self.normal, self.screen_width-self.normal]

                # if channel is visible in screen
                else:
                    if y < self.travel_per_wall:
                        return [self.normal, self.screen_width-self.normal]
                    elif y >= self.travel_per_wall and y < self.travel_per_wall+self.channel_length:
                        return [self.channel, self.screen_width-self.channel]  
                    else:
                        return [self.normal, self.screen_width-self.normal]   

            # it a channel starts to appear in the screen
            else:
                if y < self.travel_per_wall - (self.wall_length - self.channel_length):
                    return [self.channel, self.screen_width-self.channel]  
                else:
                    return [self.normal, self.screen_width-self.normal] 

        else:
            return [self.channel, self.screen_width-self.normal] 

