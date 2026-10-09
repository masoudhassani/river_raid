from ..assets import NO_AUDIO
from .entity import Entity


class Player(Entity):
    channels = {
        'engine-normal': 0,
        'engine-fast': 1,
        'engine-slow': 2,
        'fuel-up': 3,
        'fuel-critical': 4,
        'tank-filled': 5,
    }

    def __init__(self, scr, name, ent_type, cg, pos, icon_list, v_speed, h_speed,
                 player_cg=(), sound_list=(), life_span=999999, capacity=100, dec_factor=1,
                 inc_factor=1, low_fuel=0.2, audio=NO_AUDIO):
        super().__init__(scr, name, ent_type, cg, pos, icon_list, v_speed, h_speed,
                         player_cg, sound_list, life_span, audio)

        self.capacity = capacity           # initial fuel capacity
        self.dec_factor = dec_factor       # fuel decrease factor per step
        self.inc_factor = inc_factor       # fuel increase factor per step
        self.low_fuel = low_fuel           # percentage of capacity for low fuel alert
        self.fuel = capacity

    def update(self, action, fuel_col=False, close_enemies=0):
        # handle movements
        if 'LEFT' in action:
            self.move_left()
        elif 'RIGHT' in action:
            self.move_right()

        # handle speed
        if 'UP' in action:
            self.speed_up()
        elif 'DOWN' in action:
            self.slow_down()
        else:
            self.current_speed_h = self.base_speed_h
            self.current_speed_v = self.base_speed_v

        # check player life
        self.current_icon = self.icons[0] if self.alive else self.icons[1]

        # update travel distance
        self.update_odometer()

        # play engine sound
        self.play_sound(0, 'engine-normal', loops=-1)

        # check the remaining fuel
        self.check_fuel(fuel_col, close_enemies)

        return self.travel_total

    def move_right(self):
        self.pos[0] += self.current_speed_h

    def move_left(self):
        self.pos[0] -= self.current_speed_h

    def play_sound(self, sound_idx, channel, loops=-1):
        if self.alive:
            self.audio.play_if_idle(self.channels[channel], self.sounds[sound_idx], loops)
        else:
            self.audio.pause(self.channels[channel])

    def stop_sound(self, channel):
        self.audio.stop(self.channels[channel])

    def pause(self):
        for key in self.channels:
            self.stop_sound(key)

    def reset(self):
        self.alive = True
        self.pos = self.init_pos.copy()
        self.fuel = self.capacity
        self.pause()

    def check_fuel(self, fuel_col, close_enemies):
        # fuel up if player is colliding with fuel tank
        if fuel_col:
            self.fuel += self.inc_factor
            self.play_sound(3, 'fuel-up')
            # tank filled alert
            if self.fuel >= 0.95 * self.capacity:
                self.stop_sound('fuel-up')
                self.play_sound(5, 'tank-filled')
            else:
                self.stop_sound('tank-filled')

        # regular fuel consumption
        else:
            self.fuel -= self.dec_factor * self.current_speed_v
            self.stop_sound('tank-filled')
            self.stop_sound('fuel-up')

        # fuel down if in vicinity of enemy
        self.fuel -= self.dec_factor * close_enemies * self.current_speed_v*5

        # cap the fuel between 0 and self.capacity
        self.fuel = min(max(0, self.fuel), self.capacity)

        # low fuel alert
        if self.fuel < self.low_fuel * self.capacity:
            self.play_sound(4, 'fuel-critical')
        else:
            self.stop_sound('fuel-critical')
