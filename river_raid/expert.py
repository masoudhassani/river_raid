"""A scripted River Raid player that reads the true game state.

It hunts the closest enemy (aiming where the enemy will be when the bullet arrives), only shoots
when the bullet will hit something, refuels when the tank runs low, shoots spare fuel tanks, and
checks every move 40 frames ahead so it does not fly into enemies or banks.

It is not a strong player (it mostly dies on the banks), but it plays the way a human does, which
makes it a good teacher: `pretrain.py` trains the agent's network to imitate it before PPO.
An agent trained with PPO from scratch learns to sit in the middle of the river and shoot, and
never discovers that chasing enemies pays.
"""
from .game import ACTIONS

PLAYER_Y, PLAYER_W, PLAYER_H = 550, 28, 26
LOOK_AHEAD = 40   # frames


def trajectory(enemy, frames):
    '''enemy boxes for the next frames (it moves down 4 px per frame and bounces off its walls)'''
    x, vx, out = enemy.pos[0], enemy.current_speed_h, []
    for k in range(frames):
        out.append((x, enemy.pos[1] + 4 * k, enemy.cg[0], enemy.cg[1]))
        x += vx
        if x <= enemy.walls[0] or x + enemy.cg[0] >= enemy.walls[1]:
            vx = -vx
    return out


def predict_x(entity, frames):
    '''horizontal position of an entity after some frames'''
    if entity.type != 'enemy':
        return entity.pos[0]
    return trajectory(entity, frames + 1)[-1][0]


def hits_player(x, box):
    ex, ey, ew, eh = box
    return (PLAYER_Y <= ey + eh and PLAYER_Y + PLAYER_H >= ey and
            x < ex + ew and x + PLAYER_W > ex)


def bullet_frames(entity):
    '''frames until a bullet fired now reaches the entity (bullet 20 px/frame up, entity 4 down)'''
    return max(0, int((PLAYER_Y - (entity.pos[1] + entity.cg[1])) / 24))


class Expert:
    def __init__(self, refuel_below=0.55, refuel_until=0.95, spare_tank_above=0.75):
        self.refuel_below = refuel_below          # go for fuel below this fraction of a full tank
        self.refuel_until = refuel_until          # and keep refuelling up to this
        self.spare_tank_above = spare_tank_above  # shoot fuel tanks when above this
        self.refuelling = False

    def reset(self):
        self.refuelling = False

    def action(self, game):
        '''the index of the action to take (in ACTIONS)'''
        steer, shoot = self.act(game)
        name = {-1: 'LEFT', 0: 'NO_MOVE', 1: 'RIGHT'}[steer]
        if shoot:
            name = 'SHOOT' if steer == 0 else name + '_SHOOT'
        return ACTIONS.index(name)

    def act(self, game):
        '''returns (steer: -1, 0 or 1, shoot: bool)'''
        x0 = game.player.pos[0]
        self.walls = [self._walls_at(game, k) for k in range(LOOK_AHEAD)]
        self.trajectories = [trajectory(e, LOOK_AHEAD) for e in game.enemies
                             if e.alive and e.pos[1] < PLAYER_Y + PLAYER_H]
        target = self._target_x(game)
        lo = max(w[0] for w in self.walls)
        hi = min(w[1] for w in self.walls)
        if hi - lo > PLAYER_W + 8:
            target = min(max(target, lo + 4), hi - PLAYER_W - 4)
        else:
            target = (lo + hi) / 2 - PLAYER_W / 2
        want = (target > x0 + 2) - (target < x0 - 2)

        # try the move towards the target first; keep the move that stays safe the longest
        best, best_score = 0, -1
        for first in sorted((-1, 0, 1), key=lambda s: abs(s - want)):
            for follow in ('target', 0, -1, 1):
                safe = self._safe_frames(x0, first, follow, target)
                score = safe * 10 + (3 - abs(first - want)) + (follow == 'target')
                if score > best_score:
                    best, best_score = first, score
            if best_score >= LOOK_AHEAD * 10:
                break
        return best, self._should_shoot(game)

    def _walls_at(self, game, k):
        '''river banks at the plane's rows in k frames (the river scrolls down 4 px per frame)'''
        w1 = game.walls.return_wall_coordinate(PLAYER_Y - 4 * k)
        w2 = game.walls.return_wall_coordinate(PLAYER_Y + PLAYER_H - 4 * k)
        return max(w1[0], w2[0]), min(w1[1], w2[1])

    def _target_x(self, game):
        fuel = game.player.fuel / game.player.capacity
        if fuel < self.refuel_below:
            self.refuelling = True
        if fuel > self.refuel_until:
            self.refuelling = False
        if self.refuelling:
            tanks = [f for f in game.fuels if f.alive and PLAYER_Y - 480 <= f.pos[1] + f.cg[1]
                     and f.pos[1] <= PLAYER_Y + PLAYER_H]
            if tanks:
                tank = max(tanks, key=lambda f: f.pos[1])
                return tank.pos[0] + tank.cg[0] / 2 - PLAYER_W / 2
        doomed = self._bullet_target(game)
        enemies = [e for e in game.enemies
                   if e.alive and e.pos[1] + e.cg[1] < PLAYER_Y - 8 and e is not doomed]
        if enemies:
            enemy = max(enemies, key=lambda e: e.pos[1])           # the closest one
            ex = predict_x(enemy, bullet_frames(enemy) + 4)
            return ex + enemy.cg[0] / 2 - PLAYER_W / 2
        return game.settings['width'] / 2

    def _bullet_target(self, game):
        '''the enemy the bullet in flight is going to hit, if any'''
        b = game.bullet
        if b.state != 'fired':
            return None
        for e in game.enemies:
            if (e.alive and e.pos[1] < b.pos[1] and
                    b.pos[0] < e.pos[0] + e.cg[0] and b.pos[0] + b.cg[0] > e.pos[0]):
                return e
        return None

    def _safe_frames(self, x0, first, follow, target):
        '''how many frames the plane survives: `first` for 4 frames, then `follow`'''
        x = x0
        for k in range(LOOK_AHEAD):
            lo, hi = self.walls[k]
            if x < lo or x + PLAYER_W > hi:
                return k
            for path in self.trajectories:
                if hits_player(x, path[k]):
                    return k
            if k < 4:
                x += 4 * first
            elif follow == 'target':
                x += 4 * ((target > x + 2) - (target < x - 2))
            else:
                x += 4 * follow
        return LOOK_AHEAD

    def _should_shoot(self, game):
        '''shoot only if the bullet will hit an enemy, or a fuel tank we do not need'''
        if game.bullet.state == 'fired':
            return False
        bx = game.player.pos[0] + PLAYER_W // 2 - 1
        first = None
        for obj in [e for e in game.enemies if e.alive] + [f for f in game.fuels if f.alive]:
            if obj.pos[1] + obj.cg[1] > PLAYER_Y:
                continue
            ox = predict_x(obj, bullet_frames(obj))
            if bx < ox + obj.cg[0] and bx + 2 > ox and (first is None or obj.pos[1] > first.pos[1]):
                first = obj
        if first is None:
            return False
        if first.type == 'fuel':
            fuel = game.player.fuel / game.player.capacity
            return fuel > self.spare_tank_above and not self.refuelling
        return True
