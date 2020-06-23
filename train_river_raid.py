from modules import RiverRaid
import time
import logging 
import numpy as np
from models.dqn_agent import Agent
import tensorflow as tf 

gpu_options = tf.compat.v1.GPUOptions(per_process_gpu_memory_fraction=0.6)
sess = tf.compat.v1.Session(config=tf.compat.v1.ConfigProto(gpu_options=gpu_options))

# LOGGING CONFIG ##############################
logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S')
###############################################
    
# TRAINING PARAMETERS #########################
render = True               # if true, the gameplay will be shown
render_every = 1            # every n episode
save_every = 200            # frequency of saving the model weights, number of episodes
aggregate_stats_every = 5   # every n episode 
max_steps = 650             # number of time steps per game
stack_size = 4              # number of consecutive frames to be stacked to represent a state
max_episodes = 20000        # number of games to play
learning_rate = 0.0001      # up to episode 5000: 0.001, up to episode 12000: 0.0002, rest: 0.0001  
min_reward_save = 300       # min reward threshold for saving a model weight
model_name = '16x32_re'
last_episode = 0
###############################################

# GAME INITTIALIZATION ########################
env = RiverRaid(preset='AI', ai_agent=True, random=True, init_enemy_spawn=160,
                init_prop_spawn=150, init_fuel_spawn=500) 

print('Action Space:', env.action_space)
print('State Space:', env.observation_space)
###############################################

# AGENT INIT ####################################
input_shape = (stack_size,) + env.observation_space.n
print('Network Input Shape:', input_shape)
print('State Encoding Size:', env.enc_max)
agent = Agent(input_shape=input_shape, 
            num_actions=env.action_space.n,
            learning_rate=learning_rate,
            max_epsilon=1.0, 
            min_epsilon=0.1, 
            epsilon_decay_steps=250000, 
            epsilon_decay=True,
            enc_max=env.enc_max) 
#################################################

# LOAD A PRETRAINED MODEL #######################
# uncomment the following to load a trained model
trained_model_name = 'trainings/16x32_re_11825__605.00max__340.80avg_-301.00min__1592715040.model'
last_episode = 11825
model = tf.keras.models.load_model(trained_model_name)
print(model.summary())
print('Starting from a trained model')
agent.main_model = model
agent.target_model = model
agent.max_epsilon = 0.1
#################################################

episode = last_episode
episode_rewards = []
while True:
    episode += 1
    agent.tensorboard.step = episode

    episode_reward = 0
    env.reset()
    is_running = True 
    step = 0

    # initialize the current state with a 'no move' action
    s, _, _ = env.step(env.action_space.actions[0]) 
    current_state = [s] * stack_size 
    current_state = np.array(current_state, dtype=np.int8)    

    # each episode runs for max_steps / stack_size steps or until the agent dies
    while is_running:
        step += 1
        if step > max_steps / stack_size:
            # reduce 501 points if agent finishes the upisode without any score
            if episode_reward == 0:
                episode_reward = -501   

            break

        if np.random.random() > agent.epsilon:
            action_idx = np.argmax(agent.get_q(current_state))
            action = env.action_space.actions[action_idx]
            print('Agent  Action:{}'.format(action), end='\r')

        else:
            action, action_idx = env.action_space.sample() 
            print('Random Action:{}'.format(action), end='\r')

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
           
        episode_reward += reward 
        agent.update_replay_memory((current_state, action_idx, reward, new_state, is_running))
        agent.train(is_running, step)

        # update the current state
        current_state = new_state

        # render an episode
        if render and not episode % render_every:
            env.render()
            env.discrete_render()

        # update epsilon
        agent.update_epsilon()

    episode_rewards.append(episode_reward)
    if not episode % aggregate_stats_every or episode == 1:
        average_reward = sum(episode_rewards[-aggregate_stats_every:])/len(episode_rewards[-aggregate_stats_every:])
        min_reward = min(episode_rewards[-aggregate_stats_every:])
        max_reward = max(episode_rewards[-aggregate_stats_every:])
        agent.tensorboard.update_stats(reward_avg=average_reward, 
                                        reward_min=min_reward, 
                                        reward_max=max_reward, 
                                        epsilon=agent.epsilon)
        
        # Save model, but only when min reward is greater or equal a set value
        if average_reward >= min_reward_save:
            agent.main_model.save(f'trainings/{model_name}_{episode}_{max_reward:_>7.2f}max_{average_reward:_>7.2f}avg_{min_reward:_>7.2f}min__{int(time.time())}.model')

    # save the model every 'save_every' episodes
    if not episode % save_every:
        agent.main_model.save(f'trainings/{model_name}_{episode}_{episode_reward}_{int(time.time())}.model')
    
    logging.info('espisode {} finished with score {}. current epsilon:{}'.format(episode, episode_reward, agent.epsilon))
    if episode >= max_episodes:
        logging.info('{} episode completed'.format(episode))
        exit(0)



