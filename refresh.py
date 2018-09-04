import orm
from orm import Logfile
import sources
import os
import logging
import time
import json
import modelutils
from model import (
    get_logfile_progress, 
    save_logfile_progress, 
    add_event
)

def _refresh_from_file(file, src, sess):
    logging.debug(file.path)
    logfile = get_logfile_progress(sess, src)

    with open(logfile.path, 'rb') as f:
        logging.debug('offset: {}'.format(logfile.current_key))
        f.seek(logfile.current_key)
        iter = 0
        for line in f:
            try:
                data = modelutils.logline_to_dict(line.decode())
                data["src_abbr"] = src.name
                if not ('type' in data and data['type'] == 'crash'):
                    add_event(sess, data)
            except KeyError as e:
                logging.error('key {} not found'.format(e))
            except Exception as e:  # how scandalous! Don't want one broken line to break everything
                logging.exception('Something unexpected happened, skipping this event')
            iter += 1
            logfile.offset += len(line)
            if iter % 1000 == 0:  # don't spam commits
                sess.commit()
        logfile.current_key = f.tell()
        sess.commit()

def refresh_static(sources_dir):
    t_i = time.time()
    with orm.get_session() as sess:
        for src in os.scandir(sources_dir):
            for file in os.scandir(src.path):
                if file.is_file() and not file.name.startswith('.'):
                    _refresh_from_file(file, src, sess)
    logging.info('Refreshed static in {} seconds'.format(time.time() - t_i))

# fetch newest data into the DB
def refresh(sources_file, sources_dir):
    t_i = time.time()
    source_data = sources.source_data(sources_file)
    sources.download_sources(sources_file, sources_dir)

    with orm.get_session() as sess:
        for src in os.scandir(sources_dir):
            if not src.is_file() and src.name in source_data:
                expected_files = [sources.url_to_filename(x) for x in source_data[src.name]]
                logging.debug('scanning {} files, expect [{}]'.format(src.name, ','.join(expected_files)))
                for file in os.scandir(src.path):
                    if file.is_file() and file.name in expected_files:
                        _refresh_from_file(file, src, sess)

    logging.info('Refreshed in {} seconds'.format(time.time() - t_i))
