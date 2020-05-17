from tensorflow.keras.callbacks import TensorBoard
import tensorflow as tf
import numpy as np

class ModifiedTensorBoard(TensorBoard):

    # Overriding init to set initial step and writer (we want one log file for all .fit() calls)
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.step = 1
        self.writer = tf.compat.v1.summary.FileWriter(self.log_dir)

    # Overriding this method to stop creating default log writer
    def set_model(self, model):
        pass

    # Overrided, saves logs with our step number
    # (otherwise every .fit() will start writing from 0th step)
    def on_epoch_end(self, epoch, logs=None):
        self.update_stats(**logs)

    # Overrided
    # We train for one batch only, no need to save anything at epoch end
    def on_batch_end(self, batch, logs=None):
        pass

    # Overrided, so won't close writer
    def on_train_end(self, _):
        pass

    # Custom method for saving own metrics
    # Creates writer, writes custom metrics and closes writer
    def update_stats(self, **stats):
        # self.writer.add_session_log(stats)
        self._write_logs(stats, self.step)
        self.step += 1

    def _write_logs(self, logs, index):
        import tensorflow as tf
        for name, value in logs.items():
            if name in ['batch', 'size']:
                continue
            if name.startswith('val_'):
                # writer = self.val_writer
                name = name[4:]  # remove val_
            else:
                writer = self.writer
            summary = tf.Summary()
            summary_value = summary.value.add()
            if isinstance(value, np.ndarray):
                summary_value.simple_value = value.item()
            else:
                summary_value.simple_value = value
            summary_value.tag = name
            writer.add_summary(summary, index)
        self.writer.flush()
        # self.val_writer.flush()