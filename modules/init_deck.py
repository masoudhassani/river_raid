import yaml
import os.path
import sys
import logging

class InitDeck():

    def __init__(self, setting_path='settings.yaml', preset='Basic'):
        logging.basicConfig(level=logging.INFO)

        if not os.path.exists(setting_path):
            logging.warn('Could not find {}'.format(setting_path))
            sys.exit(1)
        else:
            with open(setting_path,'r') as f:
                setting = yaml.load(f, Loader=yaml.BaseLoader)
                if not preset in setting:
                    logging.warn('Cound not find preset {}'.format(preset))
                    sys.exit(1)
                else:
                    setting_preset = preset

                    if not "width" in setting[setting_preset]:
                        logging.warn('width tag missing in {}'.format(setting_path))
                        sys.exit(1)
                    else:
                        self.width = int(setting[setting_preset]["width"])

                    if not "height" in setting[setting_preset]:
                        logging.warn('height tag missing in {}'.format(setting_path))
                        sys.exit(1)
                    else:
                        self.height = int(setting[setting_preset]["height"])

                    if not "sound" in setting[setting_preset]:
                        logging.warn('sound tag missing in {}'.format(setting_path))
                        sys.exit(1)
                    else:
                        self.sound = (setting[setting_preset]["sound"])

                    if not "speed" in setting[setting_preset]:
                        logging.warn('speed tag missing in {}'.format(setting_path))
                        sys.exit(1)
                    else:
                        self.speed = (setting[setting_preset]["speed"])     
        
    def load(self):
        setting = {
            'width': self.width,
            'height': self.height,
            'speed': float(self.speed),
            'sound': self.sound
        }
        return setting