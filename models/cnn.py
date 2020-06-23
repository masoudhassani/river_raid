from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Convolution2D, Flatten, Activation, Conv2D, MaxPooling2D, Dropout
from tensorflow.keras.optimizers import Adam, RMSprop
from tensorflow.keras.optimizers import schedules


class CNN:
    def __init__(self, input_shape, num_actions, learning_rate=0.001):
        self.model = Sequential()
        self.model.add(Conv2D(16, (8, 8), strides=(4, 4), input_shape=input_shape, data_format="channels_first"))
        self.model.add(Activation('relu'))

        self.model.add(Conv2D(32, (4, 4), strides=(2, 2), input_shape=input_shape, data_format="channels_first"))
        self.model.add(Activation('relu'))

        # self.model.add(Conv2D(64, (3, 3), strides=(1, 1)))
        # self.model.add(Activation('relu'))

        self.model.add(Flatten())
        self.model.add(Dense(256, activation='relu'))

        self.model.add(Dense(num_actions))

        adam=Adam(lr=learning_rate)
        self.model.compile(loss='mean_squared_error',
                        optimizer=adam)

        # self.model.compile(loss="mean_squared_error", 
        #                 optimizer=RMSprop(lr=learning_rate, 
        #                                     rho=0.95, 
        #                                     epsilon=0.01), 
        #                 metrics=["accuracy"]) 

        print(self.model.summary())
      
    # 'mean_squared_error'
    # 'sparse_categorical_crossentropy'