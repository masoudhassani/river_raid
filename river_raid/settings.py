import yaml

from .assets import asset_path

REQUIRED = ('width', 'height', 'sound', 'player_speed', 'enemy_speed', 'num_lives')


def load_settings(preset='Basic', setting_path=None):
    """Load a preset from settings.yaml (replaces the old InitDeck class)."""
    with open(setting_path or asset_path('settings.yaml')) as f:
        settings = yaml.safe_load(f)

    if preset not in settings:
        raise KeyError('could not find preset {} in settings.yaml'.format(preset))
    preset_settings = settings[preset]
    missing = [k for k in REQUIRED if k not in preset_settings]
    if missing:
        raise KeyError('preset {} is missing {}'.format(preset, ', '.join(missing)))

    return {
        'width': int(preset_settings['width']),
        'height': int(preset_settings['height']),
        'player_speed': float(preset_settings['player_speed']),
        'enemy_speed': float(preset_settings['enemy_speed']),
        'sound': bool(int(preset_settings['sound'])),
        'num_lives': int(preset_settings['num_lives']),
    }
