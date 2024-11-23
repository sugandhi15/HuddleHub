###############################################################################
#
#   Copyright: (c) 2017 Carlo Sbraccia
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
###############################################################################

import logging
import logging.config
import json

__all__ = ["setup_logging_from_json_config"]

DEFAULT_LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        }
    },

    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "DEBUG",
            "formatter": "simple",
            "stream": "ext://sys.stdout"
        },
    },

    "root": {
        "level": "INFO",
        "handlers": ["console"]
    },
}


# -----------------------------------------------------------------------------
def setup_logging_from_json_config(
    config_file=None, default_config=DEFAULT_LOGGING_CONFIG):
    """
    Description:
        Load configuration options for logging from a json file.
    Inputs:
        config_file    - logging configuration file in json format (optional).
        default_config - default configuration used if config_file is not set.
    Returns:
        None
    """
    if config_file is None:
        config = default_config
    else:
        try:
            with open(config_file, "rt") as fin:
                config = json.load(fin)
        except FileNotFoundError:
            raise FileNotFoundError("logging configuration "
                "file {0:s} not found or readable".format(config_file))

    logging.config.dictConfig(config)
