from modules import RiverRaid

env = RiverRaid(preset='Basic', ai_agent=False, random=False, init_enemy_spawn=50,
                init_prop_spawn=50, init_fuel_spawn=500)

env.reset()
is_running = True 
while is_running:
    action = env.agent.take_action(env)
    _, _, is_running = env.step(action)
    env.render()