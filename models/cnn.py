from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Convolution2D, Flatten, Activation, Conv2D, MaxPooling2D, Dropout
from tensorflow.keras.optimizers import Adam


class CNN:
    def __init__(self, input_shape, num_actions, learning_rate):
        self.model = Sequential()
        self.model.add(Conv2D(256, (8, 8), strides=(4, 4), input_shape=input_shape))
        self.model.add(Activation('relu'))
        self.model.add(MaxPooling2D(2,2))
        self.model.add(Dropout(0.2))

        self.model.add(Conv2D(256, (4, 4), strides=(2, 2)))
        self.model.add(Activation('relu'))
        self.model.add(MaxPooling2D(2,2))
        self.model.add(Dropout(0.2))

        self.model.add(Flatten())
        self.model.add(Dense(64))

        self.model.add(Dense(num_actions, activation='linear'))

        adam=Adam(lr=learning_rate)
        self.model.compile(loss='mean_squared_error',
                        optimizer=adam)
        print(self.model.summary())
      
    # 'mean_squared_error'
    # 'sparse_categorical_crossentropy'