from modules import RiverRaid
import time
import logging 
import numpy as np
from models.dqn_agent import Agent
import tensorflow as tf 
from models.cnn import CNN 

# PARAMETERS #########################
render = True               # if true, the gameplay will be shown
random_assets = True              # False for deterministic game
max_steps = 7000             # number of time steps per game
stack_size = 4              # number of consecutive frames to be stacked to represent a state
model_name = 'trainings/16x32_re_6980__825.00max__323.60avg_-281.00min__1592264617.model'
######################################

# GAME INITTIALIZATION ########################
env = RiverRaid(preset='AI', ai_agent=True, random=random_assets, init_enemy_spawn=220,
                init_prop_spawn=150, init_fuel_spawn=400)  
###############################################

# LOAD A TRAINED MODEL ########################
model = tf.keras.models.load_model(model_name)
print(model.summary())
###############################################

# START THE GAME ##############################
episode_reward = 0
env.reset()
is_running = True 
step = 0

# stack the current state with a 'no move' action
s, _, _ = env.step(env.action_space.actions[0]) 
current_state = [s] * stack_size 
current_state = np.array(current_state, dtype=np.int8)    

# each episode runs for max_steps / stack_size steps or until the agent dies
while is_running:
    step += 1
    if step > max_steps / stack_size:
        break

    ### SELECT AN ACTION ###############################
    s = np.array(current_state).reshape(-1, *current_state.shape)/env.enc_max  # make the state compatible with tensorflow
    q = model.predict(s)[0]    # [0] is used to get the first and only member of a list of list
    action_idx = np.argmax(q)
    action = env.action_space.actions[action_idx]
    # print('Agent  Action:{}'.format(action), end='\r')
    ####################################################

    ### STACK UP 4 FRAMES ##############################
    new_state = [0] * stack_size
    reward = 0
    for i in range(stack_size):
        s, r, is_running = env.step(action) 
        new_state[i] = s   # stacking
        reward += r        # accumulating the rewards

        # if in the middle of stacking, the agent dies, the rest of stack will be the same as the last state
        if not is_running:
            if i < stack_size - 1:
                for j in range(i+1,stack_size):
                    new_state[j] = s
            break 

    new_state = np.array(new_state)
    ####################################################
    
    current_state = new_state
    episode_reward += reward 

    # render an episode
    if render:
        env.render()

model = None 
env = None
print('Total Game Reward:',episode_reward)