###############################################################################
#
#   Copyright: (c) 2015 Carlo Sbraccia
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

from ..database.objdb import ObjDbBase, ObjDbClient
from ..database.objdb_api import UseDatabase
from ..database.tsdb import TsDbClient
from ..database.tsdb_api import TsDbUseDatabase
from ..depgraph.graph_api import UseGraph

import contextlib
import configparser
import getpass
import logging
import os

__all__ = ["load_system_configuration", "OnyxInit", "OnyxStartup"]

# --- this is the global instance of ConfigParser that is used to store
#     configuration parameters loaded from the onyx_config.ini file
__config = None

logger = logging.getLogger(__name__)


###############################################################################
class ConfigParserWithLists(configparser.ConfigParser):
    """
    A ConfigParser subclass extended to support list items represented as
    follows:

    [section]
    list = value1, value2, ....
    """
    # -------------------------------------------------------------------------
    def getlist(self, section, option):
        items = self.get(section, option).splitlines()
        return [item.strip() for item in items if item != ""]


# -----------------------------------------------------------------------------
def load_system_configuration(filenames=None):
    """
    Description:
        Load configuration options from one or more INI files. Return the
        cached value if called more than once (in that case, filenames will be
        ignored).
    Inputs:
        filenames - a list of possible config file paths. By default, looks for
                    a onyx_config.ini in the following folders (stops at the
                    first match):
                        $ONYXPATH
                        $HOME
                        $USERPROFILE
                        .
    Returns:
        An instance of configparser.ConfigParser
    """
    global __config

    if __config is None:
        __config = ConfigParserWithLists()

        if filenames is None:
            filepath = os.getenv("ONYXPATH",
                                 os.getenv("HOME",
                                           os.getenv("USERPROFILE", "./")))
            filenames = [os.path.join(filepath, "onyx_config.ini")]

        files = __config.read(filenames)

        if not len(files):
            logger.warning("couldn't find any of the specified "
                           "config files: {0!s}".format(filenames))

    return __config


# -----------------------------------------------------------------------------
def OnyxInit(objdb=None, tsdb=None, user=None,
             host=None, configfile=None, with_graph=True):
    """
    Description:
        Activate onyx databases and graph using the respective context
        managers.
    Inputs:
        objdb - an instance of an ObjDb client or the name of a valid ObjDb
        tsdb  - an instance of an TsDb client or the name of a valid TsDb
        user  - the database user
        host  - the database host
        configfile - the full path of the config.ini file
        with_graph - optionally, initialize system without graph
    Returns:
        A stack of context managers.
    """
    config = load_system_configuration(configfile)

    objdb = objdb or config.get("database", "objdb", fallback="ProdDb")
    tsdb = tsdb or config.get("database", "tsdb", fallback="TsDb")
    user = user or config.get("database", "user", fallback=getpass.getuser())
    host = host or config.get("database", "host", fallback=None)

    if isinstance(objdb, ObjDbBase):
        objdb_clt = objdb
    else:
        objdb_clt = ObjDbClient(objdb, user, host)

    if isinstance(tsdb, TsDbClient):
        tsdb_clt = tsdb
    else:
        tsdb_clt = TsDbClient(tsdb, user, host)

    stack = contextlib.ExitStack()
    stack.enter_context(UseDatabase(objdb_clt))
    stack.enter_context(TsDbUseDatabase(tsdb_clt))
    if with_graph:
        stack.enter_context(UseGraph())

    return stack


# -----------------------------------------------------------------------------
def OnyxStartup(objdb=None, tsdb=None, user=None, host=None, configfile=None):
    """
    Description:
        Load onyx environment and open connections to backends.
    Typical Usage:
        In an interactive shell:
            globals().update(OnyxStartup())
    """
    import onyx.core

    stack = OnyxInit(objdb, tsdb, user, host, configfile)
    stack.__enter__()
    logger.info("Onyx has been fired up... Good luck!!!")

    return {key: value
            for key, value in onyx.core.__dict__.items()
            if not key.startswith("__")}
