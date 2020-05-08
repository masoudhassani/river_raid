from modules import RiverRaid, Agent
import time
import numpy as np

env = RiverRaid(preset='AI', ai_agent=True, init_enemy_spawn=150,
                init_prop_spawn=150, init_fuel_spawn=500)

print('Action Space:', env.action_space)
print('State Space:', env.observation_space)

#### 
is_running = True 
while is_running:
    action = env.agent.take_action(env)
    is_running, _ = env.step(action)
    # env.discrete_render()
    env.render()
    # time.sleep(0.1)