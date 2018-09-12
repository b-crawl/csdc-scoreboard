import os
import logging
import yaml
import refresh
import model
import orm
import csdc
import web
import time
import datetime

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
    t_i = time.time()
    now = datetime.datetime.now()
    oldmask = os.umask(18)
    for wk in csdc.weeks:
        if wk.start > now:
            continue
        scorepage = os.path.join(CONFIG['www dir'],"{}.html".format(wk.number))

        with open(scorepage, 'w') as f:
            f.write(web.scorepage(wk))
    logging.info("Rebuilt score pages in {} seconds.".format(time.time() -
        t_i))

    standings = os.path.join(CONFIG['www dir'],"standings.html")
    with open(standings, 'w') as f:
        f.write(web.standingspage())

    index = os.path.join(CONFIG['www dir'],"index.html")
    with open(index, 'w') as f:
        f.write(web.overviewpage())

    rules = os.path.join(CONFIG['www dir'],"rules.html")
    with open(rules, 'w') as f:
        f.write(web.rulespage())
    os.umask(oldmask)
