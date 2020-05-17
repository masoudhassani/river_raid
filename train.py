from modules import RiverRaid
import time
import logging 
import numpy as np
from models.dqn_agent import Agent

# LOGGING CONFIG ##############################
logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S')
###############################################
    
# TRAINING PARAMETERS #########################
render = True
render_every = 5            # every n episode
aggregate_stats_every = 5   # every n episode 
total_step_limit = 400
num_episodes = 50
learning_rate = 0.01
###############################################

# GAME INITTIALIZATION ########################
env = RiverRaid(preset='AI', ai_agent=True, init_enemy_spawn=150,
                init_prop_spawn=150, init_fuel_spawn=500)

print('Action Space:', env.action_space)
print('State Space:', env.observation_space)
###############################################

# Agent INIT ####################################
agent = Agent(input_shape=env.observation_space.n, 
            num_actions=env.action_space.n,
            learning_rate=learning_rate,
            enc_size=env.enc_size, epsilon_decay=True)
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
            break

        if np.random.random() > agent.epsilon:
            action_idx = np.argmax(agent.get_q(current_state))
            action = env.action_space.actions[action_idx]
        else:
            action, action_idx = env.action_space.sample() 
        
        new_state, reward, is_running = env.step(action) 
        episode_reward += reward

        agent.update_replay_memory((current_state, action_idx, reward, new_state, is_running))
        agent.train(is_running, step)

        current_state = new_state

        # env.discrete_render()
        if render and not episode % render_every:
            env.render()
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

    logging.info('espisode {} finished with score {}. current epsilon:{}'.format(episode, episode_reward, agent.epsilon))
    if episode >= num_episodes:
        logging.info('{} episode completed'.format(episode))
        exit(0)



