def display_activations(activations, step=0, cmap=None, save=False, directory='.', data_format='channels_last'):
    """
    Plot the activations for each layer using matplotlib
    :param activations: dict - mapping layers to corresponding activations (1, output_h, output_w, num_filters)
    :param cmap: string - a valid matplotlib colormap to be used
    :param save: bool - if the plot should be saved
    :param directory: string - where to store the activations (if save is True)
    :param data_format: string - one of "channels_last" (default) or "channels_first".
    The ordering of the dimensions in the inputs. "channels_last" corresponds to inputs with
    shape (batch, steps, channels) (default format for temporal data in Keras) while "channels_first"
    corresponds to inputs with shape (batch, channels, steps).
    :return: None
    """
    import matplotlib.pyplot as plt
    import math
    import os
    index = 0
    for layer_name, acts in activations.items():
        print(layer_name, acts.shape, end=' ')
        if acts.shape[0] != 1:
            print('-> Skipped. First dimension is not 1.')
            continue

        print('')
        # channel first
        if data_format == 'channels_last':
            c = -1
        elif data_format == 'channels_first':
            c = 1
        else:
            raise Exception('Unknown data_format.')

        nrows = int(math.sqrt(acts.shape[c]) - 0.001) + 1  # best square fit for the given number
        ncols = int(math.ceil(acts.shape[c] / nrows))
        hmap = None
        if len(acts.shape) <= 2:
            """
            print('-> Skipped. 2D Activations.')
            continue
            """
            # no channel
            fig, axes = plt.subplots(1, 1, squeeze=False, figsize=(24, 24))
            img = acts[0, :]
            hmap = axes.flat[0].imshow([img], cmap=cmap)
            axes.flat[0].axis('off')
        else:
            fig, axes = plt.subplots(nrows, ncols, squeeze=True, figsize=(24, 24))
            for i in range(nrows * ncols):
                if i < acts.shape[c]:
                    if len(acts.shape) == 3:
                        if data_format == 'channels_last':
                            img = acts[0, :, i]
                        elif data_format == 'channels_first':
                            img = acts[0, i, :]
                        else:
                            raise Exception('Unknown data_format.')
                        hmap = axes.flat[i].imshow([img], cmap=cmap)
                    elif len(acts.shape) == 4:
                        if data_format == 'channels_last':
                            img = acts[0, :, :, i]
                        elif data_format == 'channels_first':
                            img = acts[0, i, :, :]
                        else:
                            raise Exception('Unknown data_format.')
                        hmap = axes.flat[i].imshow(img, cmap=cmap)
                axes.flat[i].axis('off')
        fig.suptitle(layer_name)
        # fig.subplots_adjust(right=0.8)
        # cbar = fig.add_axes([0.85, 0.15, 0.03, 0.7])
        # fig.colorbar(hmap, cax=cbar)
        if save:
            if not os.path.exists(directory):
                os.makedirs(directory)
            output_filename = os.path.join(directory, '{0}_{1}_{2}.png'.format(step, index, layer_name.split('/')[0]))
            plt.savefig(output_filename, bbox_inches='tight')
        else:
            plt.show()
        # pyplot figures require manual closing
        index += 1
        plt.close(fig)
