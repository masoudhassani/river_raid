from modules import CovidRaid

game = CovidRaid(preset='Covid', block_size=5, init_enemy_spawn=300, init_people_spawn=500, 
                init_prop_spawn=50, init_fuel_spawn=800)

is_running = True 
while is_running:
    is_running = game.update()
