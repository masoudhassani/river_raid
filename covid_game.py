from modules import CovidRaid

game = CovidRaid(preset='Covid', block_size=5, init_enemy_spawn=600,
                init_prop_spawn=50)

is_running = True 
while is_running:
    is_running = game.update()
