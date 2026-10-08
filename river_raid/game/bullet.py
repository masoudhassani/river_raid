from .entity import Entity

BULLET_CHANNEL = 6


class Bullet(Entity):

    def update(self, action, player_pos):
        # handle movements
        if self.state == 'fired':
            self.fire()
        else:
            self.pos = [player_pos[0]+self.player_cg[0]/2-self.cg[0]/2, player_pos[1]+4]

        # check if bullet is fired
        if 'SHOOT' in action and self.state == 'ready':
            self.state = 'fired'

        # check if the bullet left the screen
        self.check_state()

    def fire(self):
        if not self.sound_played:
            self.audio.play(BULLET_CHANNEL, self.sounds[0])
            self.sound_played = True

        self.pos[1] -= self.current_speed_v

    # check if the fired bullet is still in the screen
    def check_state(self):
        if self.pos[1] < 0:
            self.reload()

    def reload(self):
        self.state = 'ready'
        self.sound_played = False

    def render(self):
        if self.state == 'fired':
            self.screen.blit(self.icons[0], self.pos)
