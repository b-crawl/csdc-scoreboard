import orm
from orm import Logfile
import sources
import os
import logging
import time
import modelutils
from typing import Optional
from model import (
    get_logfile_progress, 
    save_logfile_progress, 
    add_event
)

def _refresh_from_file(file, src, sess):
    logging.debug(file)
    logfile = get_logfile_progress(sess, file)
    logging.info("Refreshing from: {}".format(file))

    with open(logfile.source_url, 'rb') as f:
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
            logfile.current_key += len(line)
            if iter % 1000 == 0:  # don't spam commits
                sess.commit()
        logfile.current_key = f.tell()
        sess.commit()

# fetch newest data into the DB
def refresh(sources_file: str, sources_dir: str, fetch: Optional[bool]=True):
    t_i = time.time()
    source_data = sources.source_data(sources_file)

    if fetch:
        sources.download_sources(sources_file, sources_dir)

    with orm.get_session() as sess:
        for src in os.scandir(sources_dir):
            if not src.is_file() and src.name in source_data:
                expected_files = [sources.url_to_filename(x) for _, x in
                        source_data[src.name].items()]
                logging.debug('scanning {} files, expect [{}]'.format(src.name, ','.join(expected_files)))
                # it is important that this refresh first so we get begins
                # before ends!
                milestones = os.path.join(src.path,
                    sources.url_to_filename(source_data[src.name]["milestones"]))
                _refresh_from_file(milestones, src, sess)
                logfile = os.path.join(src.path,
                    sources.url_to_filename(source_data[src.name]["logfile"]))
                _refresh_from_file(logfile, src, sess)

    logging.info('Refreshed in {} seconds'.format(time.time() - t_i))
