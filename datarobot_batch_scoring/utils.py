from functools import partial
from os.path import expanduser, isfile, join as path_join
from os import getcwd

import logging
import os
import six
import sys
import tempfile
import trafaret as t
from six.moves.configparser import ConfigParser

OptKey = partial(t.Key, optional=True)

input = six.moves.input

CONFIG_FILENAME = '.batch_scoring.ini'


def verify_objectid(id_):
    """Verify if id_ is a proper ObjectId. """
    if not len(id_) == 24:
        raise ValueError('id {} not a valid project/model id'.format(id_))


config_validator = t.Dict({
    OptKey('host'): t.String,
    OptKey('project_id'): t.contrib.object_id.MongoId >> str,
    OptKey('model_id'): t.contrib.object_id.MongoId >> str,
    OptKey('n_retry'): t.Int,
    OptKey('keep_cols'): t.String,
    OptKey('n_concurrent'): t.Int,
    OptKey('dataset'): t.String,
    OptKey('n_samples'): t.Int,
    OptKey('delimiter'): t.String,
    OptKey('out'): t.String,
    OptKey('user'): t.String,
    OptKey('password'): t.String,
    OptKey('datarobot_key'): t.String,
    OptKey('timeout'): t.Int,
    OptKey('api_token'): t.String,
    OptKey('create_api_token'): t.String,
    OptKey('pred_name'): t.String,
    OptKey('api_version'): t.Enum('v1', 'v2')
}).allow_extra('*')


logger = logging.getLogger('main')
root_logger = logging.getLogger()


class UI(object):

    def __init__(self, prompt, loglevel):
        self._prompt = prompt
        self._configure_logging(loglevel)

    def _configure_logging(self, level):
        """Configures logging for user and debug logging. """

        with tempfile.NamedTemporaryFile(prefix='datarobot_batch_scoring_',
                                         suffix='.log', delete=False) as fd:
            pass
        self.root_logger_filename = fd.name

        # user logger
        fs = '[%(levelname)s] %(message)s'
        hdlr = logging.StreamHandler()
        dfs = None
        fmt = logging.Formatter(fs, dfs)
        hdlr.setFormatter(fmt)
        logger.setLevel(level)
        logger.addHandler(hdlr)

        # root logger
        fs = '%(asctime)-15s [%(levelname)s] %(message)s'
        hdlr = logging.FileHandler(self.root_logger_filename, 'w+')
        dfs = None
        fmt = logging.Formatter(fs, dfs)
        hdlr.setFormatter(fmt)
        root_logger.setLevel(logging.DEBUG)
        root_logger.addHandler(hdlr)

    def prompt_yesno(self, msg):
        if self._prompt is not None:
            return self._prompt
        cmd = input('{} (yes/no)> '.format(msg)).strip().lower()
        while cmd not in ('yes', 'no'):
            cmd = input('Please type (yes/no)> ').strip().lower()
        return cmd == 'yes'

    def prompt_user(self):
        return input('user name> ').strip()

    def debug(self, msg):
        logger.debug(msg)

    def info(self, msg):
        logger.info(msg)

    def warning(self, msg):
        logger.warning(msg)

    def error(self, msg):
        logger.error(msg)
        if sys.exc_info()[0]:
            exc_info = True
        else:
            exc_info = False
        root_logger.error(msg, exc_info=exc_info)

    def fatal(self, msg):
        msg = ('{}\nIf you need assistance please send the log \n'
               'file {} to support@datarobot.com .').format(
                   msg, self.root_logger_filename)
        logger.error(msg)
        exc_info = sys.exc_info()
        root_logger.error(msg, exc_info=exc_info)
        sys.exit(1)

    def close(self):
        os.unlink(self.root_logger_filename)


def get_config_file():
    """
    Lookup for config file at user home directory or working directory.
    Returns
    -------
    str or None
        Path to config file or None if it not exists.
    """
    home_path = path_join(expanduser('~'), CONFIG_FILENAME)
    cwd_path = path_join(getcwd(), CONFIG_FILENAME)
    if isfile(home_path):
        return home_path
    elif isfile(cwd_path):
        return cwd_path
    return None


def parse_config_file(file_path):
    config = ConfigParser()
    config.read(file_path)
    if 'batch_scoring' not in config.sections():
        # We are return empty dict, because there is nothing in this file
        # that related to arguments to batch scoring.
        return {}
    parsed_dict = dict(config.items('batch_scoring'))
    return config_validator(parsed_dict)