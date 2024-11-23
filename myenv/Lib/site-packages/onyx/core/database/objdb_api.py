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

from .ufo_base import UfoBase
from .objdb import ObjDbBase, ObjDbClient, ObjDbError

from .. import database as onyx_db

from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from psycopg2.extensions import ISOLATION_LEVEL_READ_COMMITTED
from psycopg2.extensions import ISOLATION_LEVEL_SERIALIZABLE

import getpass

__all__ = [
    "UseDatabase",
    "ObjDbTransaction",
    "ObjDbQuery",
    "AddObj",
    "GetObj",
    "UpdateObj",
    "DelObj",
    "ClearDatedCache",
    "ObjTypes",
    "ObjNamesByType",
    "ExistsInDatabase",
]


###############################################################################
class UseDatabase(object):
    """
    Context manager used to setup the objdb client used by the api.
    """
    # -------------------------------------------------------------------------
    def __init__(self, database, user=None):
        if isinstance(database, ObjDbBase):
            self.clt = database
        elif isinstance(database, str):
            self.clt = ObjDbClient(database, user or getpass.getuser())
        else:
            raise ValueError("UseDatabase only accepts instances of clients "
                             "derived from ObjDbBase or a valid database name")

    # -------------------------------------------------------------------------
    def __enter__(self):
        self.prev_clt = onyx_db.obj_clt
        self.prev_obj_instances = onyx_db.obj_instances
        onyx_db.obj_clt = self.clt
        onyx_db.obj_instances = dict()

    # -------------------------------------------------------------------------
    def __exit__(self, *args, **kwds):
        onyx_db.obj_clt.close()
        onyx_db.obj_instances.clear()
        onyx_db.obj_clt = self.prev_clt
        onyx_db.obj_instances = self.prev_obj_instances
        # --- returns False so that all execptions raised will be propagated
        return False


###############################################################################
class ObjDbTransaction(object):
    """
    Description:
        Transaction context manager. All statements executed within the context
        manager will be committed at the end or rolled back if an error occurs.
    Inputs:
        name   - the transaction unique name (per session)
        level  - choose between:
                    READ_COMMITTED (default)
                    SERIALIZABLE
        on_err - callback function executed in case the transaction is rolled
                 back.
    """
    # -------------------------------------------------------------------------
    def __init__(self, name, level="READ_COMMITTED", on_err=None):
        self.name = name
        if level == "READ_COMMITTED":
            self.level = ISOLATION_LEVEL_READ_COMMITTED
        elif level == "SERIALIZABLE":
            self.level = ISOLATION_LEVEL_SERIALIZABLE
        else:
            raise NameError("Unrecognized isolation level {0:s}".format(level))
        self.conn = onyx_db.obj_clt.conn
        # --- callback function called in case of exception
        self.on_err = on_err

    # -------------------------------------------------------------------------
    def __enter__(self):
        if onyx_db.obj_clt.transaction is None:
            if onyx_db.obj_clt.transaction != self.name:
                onyx_db.obj_clt.transaction = self.name
                self.conn.set_isolation_level(self.level)
                self.conn.tpc_begin(self.name)
            else:
                raise ObjDbError("Multiple nested transactions with same name")

    # -------------------------------------------------------------------------
    def __exit__(self, exc_type, exc_value, traceback):
        if onyx_db.obj_clt.transaction == self.name:
            if exc_type is None:
                self.conn.tpc_commit()
            else:
                self.conn.tpc_rollback()
                if self.on_err is not None:
                    self.on_err()
            # --- release transaction lock
            onyx_db.obj_clt.transaction = None
            # --- restore isolation level
            self.conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        # --- returns False so that all execptions raised will be propagated
        return False


# -----------------------------------------------------------------------------
def ObjDbQuery(query, parms=None, attr=""):
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
        curs = onyx_db.obj_clt.conn.cursor()
    except AttributeError:
        raise ObjDbError("<{0:s}> does not support "
                         "queries".format(onyx_db.obj_clt.dbname))

    try:
        if parms is None:
            curs.execute(query)
        else:
            curs.execute(query, parms)
        return getattr(curs, attr, lambda: None)()
    finally:
        curs.close()


# -----------------------------------------------------------------------------
def AddObj(obj):
    """
    Description:
        Add a new UFO object to the database.
    Inputs:
        obj - can be either a UFO object or it's name. In the latter case,
              the object must have previously been created in memory.
    Returns:
        A reference to the added object.
    """
    # --- input validation
    if isinstance(obj, UfoBase):
        pass
    elif isinstance(obj, str):
        try:
            obj = onyx_db.obj_clt[obj]
        except KeyError:
            raise ObjDbError("No object to add with name {0:s}".format(obj))
    else:
        raise ObjDbError("Cannot persist objects that "
                         "don't inherit from UfoBase: {0!s}".format(type(obj)))

    return onyx_db.obj_clt.add(obj)


# -----------------------------------------------------------------------------
def GetObj(name, refresh=False, skip_missing_attrs=False):
    """
    Description:
        Retrieve an UFO object from the database. It first looks for the
        object in the database cache and finally in the database itself.
    Inputs:
        name    - the object's name.
        refresh - if True, ignore database cache.
        skip_missing_attrs - if True quietly ignore any attributes that are
                             defined in the persisted json object but not in
                             the class definition.
    Returns:
        A reference to the looked-up object.
    """
    # --- input validation
    if not isinstance(name, str):
        raise ObjDbError("GetObj only retrives objects by name. "
                         "{0!s} was passed instead".format(type(name)))

    return onyx_db.obj_clt.get(name, refresh, skip_missing_attrs)


# -----------------------------------------------------------------------------
def UpdateObj(obj):
    """
    Description:
        Update the persisted version of an UFO object.
    Inputs:
        obj - can be either an UFO object or it's name. In the latter case, the
              object must have previously been modified by setting one of its
              attributes with SetVal. Therefore an instance of the object
              must exist in the graph.
    Returns:
        A reference to the updated object.
    """
    # --- input validation
    if isinstance(obj, UfoBase):
        pass
    elif isinstance(obj, str):
        # --- object passed by name: assume attributes have been set through
        #     the graph API
        try:
            obj = onyx_db.obj_clt[obj]
        except KeyError:
            raise ObjDbError("Nothing to update for {0:s}".format(obj))
    else:
        raise ObjDbError("UpdateObj must be fed either "
                         "an object derived from UfoBase or it's name")

    return onyx_db.obj_clt.update(obj)


# -----------------------------------------------------------------------------
def DelObj(obj):
    """
    Description:
        Deletes an UFO object from database. If available, the delete method
        of the object is called before deleting it.
    Inputs:
        obj - can be either an UFO object or it's name.
    Returns:
        None.
    """
    # --- make sure that the object exists in database
    if not isinstance(obj, UfoBase):
        obj = GetObj(obj)

    # --- we need a serializable transaction here to make sure that any action
    #     on dependent objects (see delete method of the object itself)
    #     is atomic
    with ObjDbTransaction("delete", level="SERIALIZABLE"):
        onyx_db.obj_clt.delete(obj)


# -----------------------------------------------------------------------------
def ClearDatedCache(name, attr=None):
    """
    Description:
        Clear the cache of dated attributes for a given object.
    Inputs:
        name - the object's name.
        attr - if specified clears the cache for the relevant attribute only
    Returns:
        None.
    """
    obj = onyx_db.obj_clt.get(name)
    try:
        if attr is None:
            delattr(obj, "dated_attributes_cache")
        else:
            obj.dated_attributes_cache = {
                (a, d): v 
                for (a, d), v in obj.dated_attributes_cache.items()
                if a != attr}

    except AttributeError:
        pass


# -----------------------------------------------------------------------------
def ExistsInDatabase(obj):
    """
    Description:
        Check if an object with the given name exists in database.
    Inputs:
        obj - can be either an UFO object or it's name.
    Returns:
        True if obj exists in database.
   """
    # --- input validation
    if isinstance(obj, UfoBase):
        obj = obj.Name
    elif not isinstance(obj, str):
        raise TypeError("ExistsInDatabase requires either a "
                        "string or an instance of a UfoBase class")

    return obj in onyx_db.obj_clt


# -----------------------------------------------------------------------------
def ObjTypes():
    """
    Description:
        Return a set with names of all object types stored in database.
    Returns:
        A set.
    """
    try:
        curs = onyx_db.obj_clt.conn.cursor()
    except AttributeError:
        raise ObjDbError("<{0:s}> does not "
                         "support queries".format(onyx_db.obj_clt.dbname))

    curs.execute("SELECT DISTINCT(ObjType) FROM ClassDefinitions;")
    return {row.objtype for row in curs.fetchall()}


# -----------------------------------------------------------------------------
def ObjNamesByType(obj_type=None):
    """
    Description:
        Return a list of all objects of the given type that are stored in
        database..
    Inputs:
        obj_type - the object type. If None, return all objects.
    Returns:
        A list.
   """
    try:
        curs = onyx_db.obj_clt.conn.cursor()
    except AttributeError:
        raise ObjDbError("<{0:s}> does not "
                         "support queries".format(onyx_db.obj_clt.dbname))

    if obj_type is None:
        curs.execute("SELECT Name FROM Objects;")
    else:
        curs.execute("SELECT Name "
                     "FROM Objects WHERE ObjType=%s;", (obj_type,))

    return [row.name for row in curs.fetchall()]
