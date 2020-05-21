import numpy as np 

class ObservationSpace:
    def __init__(self, w, h, player, wall, enc_max=4, block_size=4, crop_h=200, crop_v=0):
        # game screen dimensions
        self.w = w
        self.h = h 

        # this is a list whose first element is the instance of player class
        # and its second element is the wall's encoding value        
        self.player = player

        # this is a list whose first element is the instance of wall class
        # and its second element is the wall's encoding value
        self.wall = wall 

        # maximum of encoding values. number of entities+2
        # for example, if we have enemy and fuel, enc_size is 4
        self.enc_max = enc_max    
        self.block_size = block_size
        self.crop_h = crop_h
        self.crop_v = crop_v 

        # reset the state
        self.reset()
        self.n = (self.state.shape[0], self.state.shape[1], self.state.shape[2])


    '''
    reset the state
    '''
    def reset(self):
        self.state = np.zeros([int((self.w-self.crop_h)/self.block_size), 
                                int(self.h/self.block_size), 1], dtype=np.uint8)

    '''
    return the game state
    to reduce the action/state space size, we discretize each game frame
    using the block size. This is equivalent to image size reduction.
    in our case block size is the increment that the player,
    enemy and other props have in every time step.
    with the current FPS, block size is equal to the player speed.

    we consider 5+ different encoding values for each block which represent:
    empty             -> 0
    wall              -> 1
    player            -> 2
    fuel              -> 3
    enemy             -> 4
    additional entity -> 5

    we crop pixles from the right and left of the screen since player cannot go there.
    For a 600x600 screen, block size of 4, and 5 possible encoding values,
    the state space dimension is 150x150x5
    '''
    def update(self, entities):
        # reset the state
        self.reset()

        #### PLAYER ###################################
        self.fill_state_array(self.player[0], self.player[1])
        ###############################################   
             
        #### ENTITIES #################################
        # entities is a list of sublists. first element of each sublist is
        # a list of instances of an entity such as list of enemies,
        # the second element of each sublist if the encoding value for that entity
        for ent in entities:
            for e in ent[0]:
                self.fill_state_array(e, ent[1])
        ###############################################        

        #### WALL #####################################
        for i in range(int(self.h/self.block_size)):
            wall = self.wall[0].return_wall_coordinate(i*self.block_size)
            for j in range(int((wall[0]-self.crop_h/2)/self.block_size)):
                self.state[j][i][0] = self.wall[1]
            for j in range(int((wall[1]-self.crop_h/2)/self.block_size), 
                            int((self.w-self.crop_h)/self.block_size)):
                self.state[j][i][0] = self.wall[1]
        ############################################### 

        self.state = self.state/self.enc_max
        return self.state#, self.state_reshaped

    '''
    fill self.state with encoding values assigned to each asset 
    '''
    def fill_state_array(self, instance, value):  
        # find the origin position in the discretized space
        pos = [int((instance.pos[0]-self.crop_h/2)/self.block_size),
               int((instance.pos[1])/self.block_size)]
        # find the size of cg box in the discretized space
        width = int(instance.cg[0]/self.block_size)
        height = int(instance.cg[1]/self.block_size)

        # assign instance value to the state subset
        # take care of assets which are leaving the screen
        for i in range(width+1):
            for j in range(height+1):
                self.state[pos[0]+i][min(pos[1]+j, 
                            int(self.h/self.block_size)-1)][0] = value

    def __str__(self):
        return ('Discrete {}'.format(self.n))