from modules import CovidRaid
import time

env = CovidRaid(preset='AI', ai_agent=True, init_enemy_spawn=300, init_people_spawn=500, 
                init_prop_spawn=50, init_fuel_spawn=800)

is_running = True 
while is_running:
    is_running = env.step(env.action_space.sample())
    env.render()
    # time.sleep(0.1)
