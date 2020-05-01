from modules import RiverRaid
import time

env = RiverRaid(preset='Basic', ai_agent=False, init_enemy_spawn=150,
                init_prop_spawn=150, init_fuel_spawn=500)

is_running = True 
while is_running:
    is_running = env.step(env.action_space.sample())
    env.render()
    # time.sleep(0.1)