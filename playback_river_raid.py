from modules import RiverRaid
import time
import logging 
import numpy as np
from models.dqn_agent import Agent
from models.utils import display_activations
import tensorflow as tf 
from models.cnn import CNN 
from keract import get_activations, display_heatmaps

# PARAMETERS #########################
render = True               # if true, the gameplay will be shown
random_assets = True              # False for deterministic game
max_steps = 70000             # number of time steps per game
stack_size = 4              # number of consecutive frames to be stacked to represent a state
model_name = 'trained_models/river_raid.model'
######################################

# GAME INITTIALIZATION ########################
env = RiverRaid(preset='AI', ai_agent=True, random=random_assets, init_enemy_spawn=160,
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
    vis_state = [0] * stack_size    # this is created for visualization of convolutional layers
    reward = 0
    for i in range(stack_size):
        s, r, is_running = env.step(action) 
        new_state[i] = s   # stacking
        vis_state[i] = np.transpose(s)
        reward += r        # accumulating the rewards

        # if in the middle of stacking, the agent dies, the rest of stack will be the same as the last state
        if not is_running:
            if i < stack_size - 1:
                for j in range(i+1,stack_size):
                    new_state[j] = s
            break 

    new_state = np.array(new_state)
    vis_state = np.array(vis_state)
    ####################################################
    
    current_state = new_state
    episode_reward += reward 

    # visualize convolutional layers
    visualize_states= vis_state.reshape(1,vis_state.shape[0], vis_state.shape[1], vis_state.shape[2])
    activations = get_activations(model, visualize_states)
    subset = {'conv2d': activations['conv2d']}
    display_activations(subset, step, cmap=None, save=True, directory='vis', data_format='channels_first')

    # render an episode
    if render:
        env.render()

model = None 
env = None
print('Total Game Reward:',episode_reward)

'''
    Layer (type)                 Output Shape              Param #
    =================================================================
    conv2d (Conv2D)              (None, 16, 36, 36)        4112
    _________________________________________________________________
    activation (Activation)      (None, 16, 36, 36)        0
    _________________________________________________________________
    conv2d_1 (Conv2D)            (None, 32, 17, 17)        8224
    _________________________________________________________________
    activation_1 (Activation)    (None, 32, 17, 17)        0
    _________________________________________________________________
    flatten (Flatten)            (None, 9248)              0
    _________________________________________________________________
    dense (Dense)                (None, 256)               2367744
    _________________________________________________________________
    dense_1 (Dense)              (None, 6)                 1542
''' 