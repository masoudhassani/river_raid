from modules import RiverRaid, Agent
import time

env = RiverRaid(preset='AI', ai_agent=True, init_enemy_spawn=150,
                init_prop_spawn=150, init_fuel_spawn=500)

agent = Agent()

is_running = True 
while is_running:
    action = agent.take_action(env)
    is_running = env.step(action)
    env.render()
    # time.sleep(0.1)