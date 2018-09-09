import os
import logging
import yaml
import refresh
import model
import orm
import csdc
import web
import time

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
    
    t_i = time.time()
    csdc.initialize_weeks()
    oldmask = os.umask(18)
    for wk in csdc.weeks:
        scorepage = os.path.join(CONFIG['www dir'],"{}.html".format(wk.number))

        with open(scorepage, 'w') as f:
            f.write(web.scorepage(wk))
    logging.info("Rebuilt score pages in {} seconds.".format(time.time() -
        t_i))
    os.umask(oldmask)
