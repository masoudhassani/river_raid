from .entity import Entity


class Enemy(Entity):

    def update(self, action):
        # handle speed
        if 'UP' in action:
            self.speed_up()
        elif 'DOWN' in action:
            self.slow_down()
        else:
            self.current_speed_h = self.base_speed_h * self.sign(self.current_speed_h)
            self.current_speed_v = self.base_speed_v

        # handle movements
        self.move()

        # bounce off the river banks
        self.check_walls()

    def move(self):
        self.pos[0] += self.current_speed_h
        self.pos[1] += self.current_speed_v

    def check_walls(self):
        # left wall collision
        if self.pos[0] <= self.walls[0]:
            self.current_speed_h *= -1

        # right wall collision
        if self.pos[0] + self.cg[0] >= self.walls[1]:
            self.current_speed_h *= -1

    def is_active(self):
        return self.pos[1] <= self.screen_height and self.alive
