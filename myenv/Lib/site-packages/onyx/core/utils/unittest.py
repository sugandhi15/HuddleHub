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

from ..database.objdb import ObjNotFound
from ..database.objdb_api import GetObj, AddObj, UseDatabase
from ..database.tsdb_api import TsDbUseDatabase
from ..depgraph.graph_api import CreateInMemory
from .startup import OnyxInit, load_system_configuration
from .base36 import unique_id

from ..database.objdb import ObjDbClient
from ..database.tsdb import TsDbClient

import psycopg2
import psycopg2.extensions as psycopg2_ext
from psycopg2 import sql

import unittest

__all__ = [
    "AddIfMissing",
    "UseEphemeralDbs",
    "ObjDbTestCase",
    "TsDbTestCase",
    "OnyxTestCase",
]

CREATE_CMD = "CREATE DATABASE {};"
DROP_CMD = "DROP DATABASE {};"
TERMINATE_OTHER_CONNECTIONS = """
SELECT pg_terminate_backend(pg_stat_activity.pid)
FROM pg_stat_activity
WHERE pg_stat_activity.datname = %s
  AND pid <> pg_backend_pid();
"""

# -----------------------------------------------------------------------------
def AddIfMissing(obj, in_memory=False):
    try:
        return GetObj(obj.Name)
    except ObjNotFound:
        if in_memory:
            return CreateInMemory(obj)
        else:
            return AddObj(obj)


###############################################################################
class UseEphemeralDbs():
    # -------------------------------------------------------------------------
    def __init__(self):
        config = load_system_configuration()
        uuid = unique_id()
        self.user = config.get("test", "user")
        self.objdb = "{0:s}_objdb_{1:s}".format(self.user, uuid).lower()
        self.tsdb = "{0:s}_tsdb_{1:s}".format(self.user, uuid).lower()
        config.set("test", "objdb", self.objdb)
        config.set("test", "tsdb", self.tsdb)
        self.conn = psycopg2.connect(dbname="postgres", user=self.user)
        self.conn.set_isolation_level(psycopg2_ext.ISOLATION_LEVEL_AUTOCOMMIT)

    # -------------------------------------------------------------------------
    def __enter__(self):
        curs = self.conn.cursor()
        curs.execute(sql.SQL(CREATE_CMD).format(sql.Identifier(self.objdb)))
        curs.execute(sql.SQL(CREATE_CMD).format(sql.Identifier(self.tsdb)))
        return self

    # -------------------------------------------------------------------------
    def __exit__(self, *args, **kwds):
        curs = self.conn.cursor()
        curs.execute(TERMINATE_OTHER_CONNECTIONS, (self.objdb,))
        curs.execute(sql.SQL(DROP_CMD).format(sql.Identifier(self.objdb)))
        curs.execute(TERMINATE_OTHER_CONNECTIONS, (self.tsdb,))
        curs.execute(sql.SQL(DROP_CMD).format(sql.Identifier(self.tsdb)))


###############################################################################
class ObjDbTestCase(unittest.TestCase):
    # -------------------------------------------------------------------------
    @classmethod
    def setUpClass(cls):
        config = load_system_configuration()
        objdb = config.get("test", "objdb")
        user = config.get("test", "user")

        if objdb == config.get("database", "objdb"):
            raise RuntimeError("Trying to run unittests on "
                               "production database ObjDb={0:s}".format(objdb))

        cls.objdb = objdb
        cls.user = user
        cls.clt = ObjDbClient(objdb, user, check=False)

        # --- create tables and functions
        cls.clt.initialize()

    # -------------------------------------------------------------------------
    @classmethod
    def tearDownClass(cls):
        # --- cleanup tables and functions
        cls.clt.cleanup()
        cls.clt.close()

    # -------------------------------------------------------------------------
    def setUp(self):
        self.context = UseDatabase(database=self.objdb, user=self.user)
        self.context.__enter__()
        self.addCleanup(self.context.__exit__, None, None, None)


###############################################################################
class TsDbTestCase(unittest.TestCase):
    # -------------------------------------------------------------------------
    @classmethod
    def setUpClass(cls):
        config = load_system_configuration()
        tsdb = config.get("test", "tsdb")
        user = config.get("test", "user")

        if tsdb == config.get("database", "tsdb"):
            raise RuntimeError("Trying to run unittests on "
                               "production database TsDb={0:s}".format(tsdb))

        cls.tsdb = tsdb
        cls.user = user
        cls.clt = TsDbClient(tsdb, user, check=False)

        # --- create tables and functions
        cls.clt.initialize()

    # -------------------------------------------------------------------------
    @classmethod
    def tearDownClass(cls):
        # --- cleanup tables and functions
        cls.clt.cleanup()
        cls.clt.close()

    # -------------------------------------------------------------------------
    def setUp(self):
        self.context = TsDbUseDatabase(database=self.tsdb, user=self.user)
        self.context.__enter__()
        self.addCleanup(self.context.__exit__, None, None, None)


###############################################################################
class OnyxTestCase(unittest.TestCase):
    # -------------------------------------------------------------------------
    @classmethod
    def setUpClass(cls):
        config = load_system_configuration()
        objdb = config.get("test", "objdb")
        tsdb = config.get("test", "tsdb")
        user = config.get("test", "user")
        host = config.get("test", "host", fallback=None)

        if objdb == config.get("database", "objdb"):
            raise RuntimeError("Trying to run unittests on "
                               "production database ObjDb={0:s}".format(objdb))
        if tsdb == config.get("database", "tsdb"):
            raise RuntimeError("Trying to run unittests on "
                               "production database TsDb={0:s}".format(tsdb))

        cls.obj_clt = ObjDbClient(objdb, user, host, check=False)
        cls.ts_clt = TsDbClient(tsdb, user, host, check=False)

        cls.objdb = objdb
        cls.tsdb = tsdb
        cls.user = user
        cls.host = host

        # --- create tables and functions
        cls.obj_clt.initialize()
        cls.ts_clt.initialize()

    # -------------------------------------------------------------------------
    @classmethod
    def tearDownClass(cls):
        # --- cleanup tables and functions
        cls.obj_clt.cleanup()
        cls.obj_clt.close()
        cls.ts_clt.cleanup()
        cls.ts_clt.close()

    # -------------------------------------------------------------------------
    def setUp(self):
        self.context = OnyxInit(
            objdb=self.objdb, tsdb=self.tsdb, user=self.user, host=self.host)
        self.context.__enter__()
        self.addCleanup(self.context.__exit__, None, None, None)

