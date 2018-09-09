import os
import logging
import yaml
import refresh
import model
import orm
import csdc

SOURCES_DIR = './sources'
CONFIG_FILE = 'config.yml'
if not os.path.isfile(CONFIG_FILE):
    CONFIG_FILE = 'config_default.yml'

CONFIG = yaml.safe_load(open(CONFIG_FILE, encoding='utf8'))

logging_level = logging.NOTSET
if 'logging level' in CONFIG and hasattr(logging, CONFIG['logging level']):
    logging_level = getattr(logging, CONFIG['logging level'])

logging.basicConfig(level=logging_level)

if __name__=='__main__':
    orm.initialize(CONFIG['db uri'])
    model.setup_database()
    refresh.refresh(CONFIG['sources file'], SOURCES_DIR)
    
    csdc.initialize_weeks()
    print(csdc.score(csdc.weeks[0]))
