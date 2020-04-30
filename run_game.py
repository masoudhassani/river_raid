from modules import RiverRaid

game = RiverRaid(preset='Basic', block_size=5, init_enemy_spawn=150,
                init_prop_spawn=150, init_fuel_spawn=500)

is_running = True 
while is_running:
    is_running = game.update()