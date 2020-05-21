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
render = True
render_every = 1            # every n episode
save_every = 200
aggregate_stats_every = 5   # every n episode 
total_step_limit = 500
num_episodes = 100000
learning_rate = 0.002
min_reward_save = 350
model_name = '32x64x64_d2'
###############################################

# GAME INITTIALIZATION ########################
env = RiverRaid(preset='AI', ai_agent=True, random=False, init_enemy_spawn=120,
                init_prop_spawn=150, init_fuel_spawn=500) 

print('Action Space:', env.action_space)
print('State Space:', env.observation_space)
###############################################

# Agent INIT ####################################
agent = Agent(input_shape=env.observation_space.n, 
            num_actions=env.action_space.n,
            learning_rate=learning_rate,
            enc_max=env.enc_max, epsilon_decay=True)
###############################################

episode = 0 
episode_rewards = []
while True:
    agent.tensorboard.step = episode

    episode += 1
    episode_reward = 0
    current_state = env.reset()
    is_running = True 
    step = 0

    while is_running:
        step += 1
        if step > total_step_limit:
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

        new_state, reward, is_running = env.step(action) 
        episode_reward += reward 

        agent.update_replay_memory((current_state, action_idx, reward, new_state, is_running))
        agent.train(is_running, step)

        current_state = new_state

        # render an episode
        if render and not episode % render_every:
            env.render()
            env.discrete_render()
        # time.sleep(0.1)

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
    if episode >= num_episodes:
        logging.info('{} episode completed'.format(episode))
        exit(0)



