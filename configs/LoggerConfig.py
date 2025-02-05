import logging
import logging.config
import yaml
import os
import warnings

def setup_logging():
    config_file = os.path.join(os.path.dirname(__file__), './logging.yaml')
    with open(config_file, 'rt') as f:
        config = yaml.safe_load(f.read())

    logging.config.dictConfig(config)

    warnings.filterwarnings("ignore")
