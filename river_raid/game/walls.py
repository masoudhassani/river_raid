import random

import pygame as pg


class Walls:
    def __init__(self, scr, color, icon_list, normal, extended, channel, 
                    max_island, min_island, spawn_dist, length, randomness, 
                    v_speed, block_size, symmetric=True, rng=random):

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
        self.rng = rng    # random number generator, pass a seeded random.Random for reproducibility

        self.travel_total = 0     # total travel distance
        self.travel_per_wall = 0  # travel for each section of wall
        self.screen_height = scr.get_height()
        self.screen_width = scr.get_width()
        self.channel_length = self.block_size*50
        self.channel_visible = False
        self.channel_passed = False
        self.wall_length = self.init_wall_length()
        self.walls = ()

    def update(self, action):
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
        random_length = self.rng.randint(int(self.randomness*self.length), int(self.length*(2-self.randomness)))
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



class River:
    '''
    The river of River Raid: wide stretches of random length and narrow channels, joined by
    straight ramps. Both banks are mirror images; bank(w) is the width of each bank.

    The course is a list of straight pieces in world coordinates. Screen row y shows world
    position travel_total + screen_height - y, so the course scrolls down as the plane flies.
    Ramps are never steeper than 45 degrees: the plane moves sideways exactly as fast as the
    river scrolls, so it can always follow a bank.
    '''

    def __init__(self, scr, color, normal=200, narrow=350, channel_length=200, ramp=150,
                 wide_length=(600, 1000), v_speed=4, rng=random):
        assert ramp >= narrow - normal, 'ramps steeper than 45 degrees cannot be followed'
        self.screen = scr
        self.color = color
        self.normal, self.narrow = normal, narrow
        self.channel_length, self.ramp = channel_length, ramp
        self.wide_length = wide_length
        self.base_speed_v = self.current_speed_v = v_speed
        self.rng = rng
        self.screen_width, self.screen_height = scr.get_width(), scr.get_height()
        self.travel_total = 0
        self.pieces = []          # (world start, world end, bank at start, bank at end)
        self._add(self.screen_height + self._wide(), normal, normal)   # start on a wide stretch
        self._extend()

    def _wide(self):
        lo, hi = self.wide_length
        return self.rng.randint(lo // 4, hi // 4) * 4

    def _add(self, length, bank_start, bank_end):
        start = self.pieces[-1][1] if self.pieces else 0
        self.pieces.append((start, start + length, bank_start, bank_end))

    def _extend(self):
        while self.pieces[-1][1] < self.travel_total + 2 * self.screen_height:
            self._add(self.ramp, self.normal, self.narrow)
            self._add(self.channel_length, self.narrow, self.narrow)
            self._add(self.ramp, self.narrow, self.normal)
            self._add(self._wide(), self.normal, self.normal)
        while len(self.pieces) > 1 and self.pieces[0][1] < self.travel_total - self.screen_height:
            self.pieces.pop(0)

    def world(self, y):
        return self.travel_total + self.screen_height - y

    def bank(self, w):
        '''width of each bank at world position w'''
        if w <= self.pieces[0][0]:
            return self.pieces[0][2]
        for start, end, b0, b1 in self.pieces:
            if w < end:
                return b0 + (b1 - b0) * (w - start) / (end - start)
        return self.pieces[-1][3]

    def return_wall_coordinate(self, y):
        '''x of the left and right bank at screen row y'''
        b = int(round(self.bank(self.world(y))))
        return [b, self.screen_width - b]

    def narrowest(self, y0, y1):
        '''the river between screen rows y0 and y1: [x of the left bank, x of the right bank]
        at the narrowest row, i.e. where an object spanning these rows fits'''
        w0, w1 = sorted((self.world(y0), self.world(y1)))
        corners = [s for s, _, _, _ in self.pieces if w0 < s < w1]
        b = max(self.bank(w) for w in [w0, w1] + corners)
        b = int(-(-b // 1))    # ceil
        return [b, self.screen_width - b]

    def thinnest_bank(self, y0, y1):
        '''the smallest bank width between screen rows y0 and y1 (to keep props on land)'''
        w0, w1 = sorted((self.world(y0), self.world(y1)))
        corners = [s for s, _, _, _ in self.pieces if w0 < s < w1]
        return int(min(self.bank(w) for w in [w0, w1] + corners))

    def update(self, action):
        if 'UP' in action:
            self.current_speed_v = self.base_speed_v * 2.0
        elif 'DOWN' in action:
            self.current_speed_v = self.base_speed_v / 2.0
        else:
            self.current_speed_v = self.base_speed_v
        self.travel_total += self.current_speed_v
        self._extend()

    def render(self, surface=None, color=None, half_res_crop=None):
        '''draw both banks. half_res_crop=(x0, x1): draw on a half resolution canvas showing
        screen columns x0..x1, where canvas pixel i shows screen pixel 2i+1 (like pygame's
        2x nearest-neighbour scale of the screen)'''
        surface = surface or self.screen
        color = color or self.color
        h, width = self.screen_height, self.screen_width
        rows = {0, h}
        for start, _, _, _ in self.pieces:
            y = self.world(0) - start
            if 0 < y < h:
                rows.add(y)
        rows = sorted(rows)
        banks = [self.bank(self.world(y)) for y in rows]
        if half_res_crop is None:
            left = [(0, 0)] + [(b - 1, y) for b, y in zip(banks, rows)] + [(0, h)]
            right = [(width - 1, 0)] + [(width - b, y) for b, y in zip(banks, rows)] + [(width - 1, h)]
        else:
            x0 = half_res_crop[0]
            # last bank pixel b-1 -> last canvas column i with 2i+1 <= b-1-x0; first right bank
            # pixel width-b -> first canvas column i with 2i+1 >= width-b-x0
            left = ([(-1, -1)] + [(int((b - x0 - 2) // 2), y / 2) for b, y in zip(banks, rows)] +
                    [(-1, h / 2)])
            right = ([((half_res_crop[1] - x0) // 2, -1)] +
                     [(int(-((x0 + 1 - (width - b)) // 2)), y / 2) for b, y in zip(banks, rows)] +
                     [((half_res_crop[1] - x0) // 2, h / 2)])
        pg.draw.polygon(surface, color, left)
        pg.draw.polygon(surface, color, right)
