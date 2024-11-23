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

from ..datatypes.curve import Curve
from ..datatypes.hlocv import HlocvCurve
from .tsdb import TsDbClient, TsDbError

from onyx.core import database as onyx_db

from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from psycopg2.extensions import ISOLATION_LEVEL_READ_COMMITTED

import getpass

__all__ = [
    "TsDbUseDatabase",
    "TsDbTransaction",
    "TsDbQuery",
    "TsDbGetRowBy",
    "TsDbUpsertCurve",
    "TsDbGetCurve",
]


###############################################################################
class TsDbUseDatabase(object):
    """
    Context manager used to setup the tsdb client used by the api.
    """
    def __init__(self, database, user=None):

        if isinstance(database, TsDbClient):
            self.clt = database
        elif isinstance(database, str):
            self.clt = TsDbClient(database, user or getpass.getuser())
        else:
            raise ValueError("UseDatabase only accepts instances "
                             "of TsDbClient or a valid database name")

    def __enter__(self):
        self.prev_clt = onyx_db.ts_clt
        onyx_db.ts_clt = self.clt

    def __exit__(self, exc_type, exc_value, traceback):
        onyx_db.ts_clt.close()
        onyx_db.ts_clt = self.prev_clt
        # --- returns False so that all execptions raised will be propagated
        return False


###############################################################################
class TsDbTransaction(object):
    """
    Transaction context manager.
    """
    def __init__(self, name):
        self.name = name

    def __enter__(self):
        onyx_db.ts_clt.conn.set_isolation_level(ISOLATION_LEVEL_READ_COMMITTED)
        onyx_db.ts_clt.conn.tpc_begin(self.name)

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            onyx_db.ts_clt.conn.tpc_commit()
        else:
            onyx_db.ts_clt.conn.tpc_rollback()
        # --- restore isolation level
        onyx_db.ts_clt.conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        # --- returns False so that all execptions raised will be propagated
        return False


# -----------------------------------------------------------------------------
def TsDbQuery(query, parms=None, attr=""):
    """
    Description:
        Perform a db-query.
    Inputs:
        query - the SQL query as a valid string.
        parms - parameters, if any, that are passed to the query
        attr  - cursor attribute, such as fetchone or fetchall.
    Returns:
        The result of the query.
    """
    try:
        curs = onyx_db.ts_clt.conn.cursor()
    except AttributeError:
        raise TsDbError("{0:s} does not support "
                        "queries".format(onyx_db.ts_clt.dbname))

    try:
        if parms is None:
            curs.execute(query)
        else:
            curs.execute(query, parms)
        return getattr(curs, attr, lambda: None)()
    finally:
        curs.close()


# -----------------------------------------------------------------------------
def TsDbGetRowBy(table, name, date=None, strict=False):
    """
    Description:
        Fetch a a single row from database.
    Inputs:
        table  - the table in TsDb
        name   - the name of the time series as stored in database
        date   - the required date (if None fetch the most recend row)
        strict - if True, raise exception if row is not found. Otherwise
                 return most recent matching row.
    Returns:
        The database row.
    """
    return onyx_db.ts_clt.get_row_by(table, name, date, strict)


# -----------------------------------------------------------------------------
def TsDbUpsertCurve(name, crv):
    """
    Description:
        Add/update curve to the database.
    Inputs:
        name - the name of the time series as stored in database
        crv  - the curve to upsert
    Returns:
        None.
    """
    if isinstance(crv, HlocvCurve):
        onyx_db.ts_clt.upsert_curve(name, crv, "HLOCV")
    elif isinstance(crv, Curve):
        onyx_db.ts_clt.upsert_curve(name, crv, "CRV")
    else:
        raise ValueError("Unrecognized curve type: {0:s}".format(type(crv)))


# -----------------------------------------------------------------------------
def TsDbGetCurve(name, start=None, end=None, crv_type="CRV", field=None):
    """
    Description:
        Fetch a plain time series from to the database.
    Inputs:
        name     - the name of the time series as stored in database
        start    - start date, inclusive
        end      - end date, inclusive
        crv_type - choose between CRV and HLOCV
        field    - for HLOCV curves, select the specific field to return
                   among: High, Low, Open, Close, Volume
                   If None, and HLOCV curve is returned instead.
    Returns:
        The time series as a curve.
    """
    if crv_type == "CRV":
        return onyx_db.ts_clt.get_curve(name, start, end)
    elif crv_type == "HLOCV":
        return onyx_db.ts_clt.get_hlocv(name, start, end, field)
    else:
        raise ValueError("Unrecognized curve type: {0:s}".format(crv_type))
