import numpy as np
import random
from collections import deque
import time
import random
from tensorflow.keras.callbacks import TensorBoard
from .cnn import CNN 
from .modified_tensor_board import  ModifiedTensorBoard

REPLAY_MEMORY_SIZE = 1000000
MIN_REPLAY_MEMORY_SIZE = 20000
MINIBATCH_SIZE = 32
MODEL_NAME = '16x32'
UPDATE_TARGET_EVERY = 5   # every n episodes 

class Agent:
    def __init__(self, input_shape, num_actions, epsilon_decay=False, epsilon=0.01,
                max_epsilon=1.0, min_epsilon=0.1, epsilon_decay_steps=100000, 
                gamma=0.99,learning_rate=0.01, enc_max=255):
        self.input_shape = input_shape
        self.num_actions = num_actions

        # additional arguments 
        self.epsilon_decay = epsilon_decay
        self.max_epsilon = max_epsilon
        self.min_epsilon = min_epsilon
        self.epsilon_decay_steps = epsilon_decay_steps
        self.gamma = gamma
        self.learning_rate = learning_rate
        self.enc_max = enc_max

        # select epsilon 
        if self.epsilon_decay:
            self.epsilon = self.max_epsilon
        else:
            self.epsilon = epsilon
        
        # main model, this is what we use for fitting, it gets trained every step
        self.main_model = CNN(input_shape, num_actions, self.learning_rate).model

        # target model, this what we use for prediction
        self.target_model = CNN(input_shape, num_actions, self.learning_rate).model 
        self.target_model.set_weights(self.main_model.get_weights())

        # replay memory 
        self.replay_memory = deque(maxlen=REPLAY_MEMORY_SIZE)

        # tensorboard initialization, it is the modified version of stock tensorboard
        # to reduce the frequency of log file update
        self.tensorboard = ModifiedTensorBoard(log_dir='logs/{}-{}.h5'.format(MODEL_NAME, int(time.time())))

        # when we update the targt model
        self.update_target_model_counter = 0

        # this is used to update epsilon
        self.step = 0

    def update_replay_memory(self, transition):
        self.replay_memory.append(transition)

    def get_q(self, state):
        s = np.array(state).reshape(-1, *state.shape)/self.enc_max   # make the state compatible with tensorflow (x,x,x,x)
        q = self.main_model.predict(s)[0]    # [0] is used to get the first and only member of a list of list
        return(q)

    def train(self, is_running, step):
        if len(self.replay_memory) < MIN_REPLAY_MEMORY_SIZE:
            return

        minibatch = random.sample(self.replay_memory, MINIBATCH_SIZE)

        current_states = np.array([transition[0] for transition in minibatch])/self.enc_max
        current_q_list = self.main_model.predict(current_states)

        new_current_states = np.array([transition[3] for transition in minibatch])/self.enc_max
        future_q_list = self.target_model.predict(new_current_states)

        X = []
        y = []

        for idx, (current_state, action, reward, new_current_state, not_terminal) in enumerate(minibatch):
            if not_terminal:
                max_future_q = np.max(future_q_list[idx])
                new_q = reward + self.gamma * max_future_q

            else:
                new_q = reward

            current_q = current_q_list[idx]
            current_q[action] = new_q

            X.append(current_state)
            y.append(current_q)

        self.main_model.fit(np.array(X)/self.enc_max, np.array(y), batch_size=MINIBATCH_SIZE,
                            verbose=0, shuffle=False, callbacks=[self.tensorboard] if not is_running else None)

        if not is_running:
            self.update_target_model_counter += 1

        # If counter reaches set value, update target network with weights of main network
        if self.update_target_model_counter > UPDATE_TARGET_EVERY:
            self.target_model.set_weights(self.main_model.get_weights())
            self.update_target_model_counter = 0     

    def update_epsilon(self):
        if self.epsilon_decay:
            self.epsilon = self.max_epsilon - self.step*((self.max_epsilon-self.min_epsilon)/self.epsilon_decay_steps)
            self.epsilon = max(self.min_epsilon, self.epsilon)      
            self.step += 1      
