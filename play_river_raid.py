"""Play River Raid yourself: arrows to steer / speed up / slow down, space to shoot, p to pause."""
from river_raid import RiverRaid

if __name__ == '__main__':
    game = RiverRaid(preset='Basic', render_mode='human', random=True, init_enemy_spawn=150,
                     init_prop_spawn=150, init_fuel_spawn=500)
    game.play()
    print('score:', game.score_value)
    game.close()
