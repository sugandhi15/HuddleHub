###############################################################################
#
#   Copyright: (c) 2015-2018 Carlo Sbraccia
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

from ..datatypes.date import Date
from ..datatypes.gcurve import GCurve
from ..datatypes.curve import Curve
from ..database.ufo_base import UfoBase, BaseField, custom_decoder
from ..database.ufo_fields import FloatField
from ..database.objdb import ObjNotFound
from ..database.objdb_api import ObjDbQuery
from .graph_api import GetVal, GraphNodeDescriptor

from .. import database as onyx_db

import json

__all__ = [
    "Archivable",
    "MktIndirectionFactory",
    "EnforceArchivableEntitlements",
]

GET_HISTORY_QUERY = """
SELECT Date, Value FROM Archive
WHERE Name=%s AND Attribute=%s AND Date BETWEEN %s AND %s ORDER BY Date;"""

GET_MOST_RECENT = """
SELECT MAX(Date) FROM Archive
WHERE Name=%s AND Attribute=%s AND Date <= %s"""


# -----------------------------------------------------------------------------
def empty():
    pass

def empty_with_docstring():
    """Empty function with docstring."""
    pass

BYTECODE_OF_EMPTY = empty.__code__.co_code
BYTECODE_OF_EMPTY_WITH_DOCSTRING = empty_with_docstring.__code__.co_code

def has_empty_body(func):
    """
    Helper function used to tell if a function has an empty body.
    """
    if func.__doc__:
        return func.__code__.co_code == BYTECODE_OF_EMPTY_WITH_DOCSTRING
    else:
        return func.__code__.co_code == BYTECODE_OF_EMPTY


###############################################################################
class Archivable(UfoBase):
    """
    Base class for all archivable UFO objects.
    """

    # -------------------------------------------------------------------------
    def last_before(self, attr, date=None):
        """
        Description:
            Return the date of the most recent archived record before a given
            date.
        Inputs:
            attr - the required attribute
            date - look for dated records with date earlier than this value.
        Returns:
            A Date.
        """
        date = date or Date.high_date()
        res = ObjDbQuery(
            GET_MOST_RECENT, (self.Name, attr, date), attr="fetchone")
        if res.max is None:
            raise ObjNotFound(
                "{0!s} not found for any date earlier"
                "than {1:s}".format((self.Name, attr), date))
        else:
            return res.max

    # -------------------------------------------------------------------------
    def get_dated(self, attr, date, strict=False, refresh=False):
        """
        Description:
            Get the value of an archived attribute as of a given date.
        Inputs:
            attr    - the attribute to archive
            date    - the archive date
            strict  - if true, raise an ObjNotFound exception if a record
                      cannot be found for the required date
            refresh - if true, force reloading archived record from backend
        Returns:
            A (Date, value) tuple
        """
        # --- get the instance of the field descriptor that is storing
        #     the attribute descriptor itself
        field = getattr(self.__class__, attr).field

        # --- load from database and de-serialize value
        date, value = onyx_db.obj_clt.get_dated(
            self.Name, attr, date, strict=strict, refresh=refresh)

        return date, field.from_json(value)

    # -------------------------------------------------------------------------
    def set_dated(self, attr, date, value, overwrite=False):
        """
        Description:
            Set the value of an archived attribute.
        Inputs:
            attr      - the attribute to archive
            date      - the archive date
            value     - the value to archive
            overwrite - if true, existing records can be overwritten
        """
        # --- get the instance of the field descriptor that is storing
        #     the attribute descriptor itself
        field = getattr(self.__class__, attr).field
        # --- make sure value is compatible with the field_type
        field.validate(value)
        # --- serialize value
        value = field.to_json(value)

        onyx_db.obj_clt.set_dated(
            self.Name, attr, date, value, overwrite=overwrite)

    # -------------------------------------------------------------------------
    def delete(self):
        """
        Invoked when the archived object is deleted from database.
        """
        ObjDbQuery("DELETE FROM Archive WHERE Name=%s", parms=(self.Name,))

    # -------------------------------------------------------------------------
    def get_history(self, attr, start=None, end=None):
        start = start or Date.low_date()
        end = end or Date.high_date()

        # --- get the instance of the field descriptor that is stored
        #     the VT descriptor itself
        field = getattr(self.__class__, attr).field

        parms = (self.Name, attr, start, end)
        rows = ObjDbQuery(GET_HISTORY_QUERY, parms, attr="fetchall")

        # --- usually json.loads is called by get_dated before returning the
        #     value but here we are processing results from a raw query
        def convert(val):
            return field.from_json(json.loads(val, cls=custom_decoder))

        knots = [(Date.parse(r[0]), convert(r[1])) for r in rows]

        if isinstance(field, FloatField):
            return Curve([d for d, v in knots], [v for d, v in knots])
        else:
            return GCurve([d for d, v in knots], [v for d, v in knots])


###############################################################################
class MktIndirectionFactory(object):
    """
    Description:
        Factory decorator that implements a descriptor protocol used for market
        data indirection.
    Inputs:
        field_type - a valid field-type constructor (must be a subclass of
                     BaseField).
        obj        - name of the object exposing value types with the current
                     market data date and a flag dictating if archived values
                     need to be looked up in strict mode or not (default is
                     "Database").
        mdd_attr   - name of the attribute for market data date (default
                     is "MktDataDate").
        fs_attr    - name of the attribute for force strict flag (default
                     is "ForceStrict").

    THIS DECORATOR CAN ONLY BE APPLIED TO METHODS OF A SUBCLASS OF Archivable.

    Typical use is as follows:
        @MktIndirectionFactory(FloatField)
        def MarketizedAttr(self, graph):
            pass

    or:
        @MktIndirectionFactory(FloatField)
        def MarketizedAttr(self, graph):
            default implementation...

    MarketizedAttr is created as a Property node descriptor that fetches
    archived data by accessing the corresponding dated record and, optionally,
    defaults (in case of missing dated record) to executing the function
    itself.
    Type consistency with the field type is enforced.
    """
    # -------------------------------------------------------------------------
    def __init__(self, field_type, obj="Database",
                 mdd_attr="MktDataDate", fs_attr="ForceStrict"):
        if not issubclass(field_type, BaseField):
            raise ValueError(
                "field_type must be an instance of a class derived from "
                "BaseField. Got {0!s} instead".format(field_type.__class__))

        self.field = field_type()
        self.obj = obj
        self.mdd_attr = mdd_attr
        self.fs_attr = fs_attr

    # -------------------------------------------------------------------------
    def __call__(self, func):
        func_name = func.__name__
        func_empty = has_empty_body(func)

        # --- descriptor protocol: getter
        def getter(instance, graph):
            mdd = graph(self.obj, self.mdd_attr)  # market data date
            fs = graph(self.obj, self.fs_attr)  # force strict
            try:
                _, value = instance.get_dated(func_name, mdd, fs)
            except ObjNotFound:
                if func_empty:
                    raise
                else:
                    value = func(instance, graph)
            return value

        getter.__name__ = func_name

        # --- create a property descriptor and add the appropriate
        #     field attribute to it
        descriptor = GraphNodeDescriptor()(getter)
        descriptor.field = self.field

        return descriptor


###############################################################################
class EnforceArchivableEntitlements(object):
    """
    Description:
        Decorator class used to enforce compliance with Archivable
        entitlements.
    Inputs:
        obj  - target object as defined in database (or memory)
        attr - target attribute (a stored attribute or a method of a ufo
               class decorated by @GraphNodeDescriptor())

    Typical use is as follows:

        @EnforceArchivableEntitlements("Database", "ArchivedOverwritable")
        class my_ufo_class(Archivable):
        ...
    """
    # -------------------------------------------------------------------------
    def __init__(self, obj, attr):
        self.obj = obj
        self.attr = attr

    # -------------------------------------------------------------------------
    def __call__(self, cls):
        if not issubclass(cls, Archivable):
            raise ValueError(
                "enforce_archivable_entitlements can "
                "only be applied to a subclass of Archivable")

        # --- override set_dated to enforce compliance with the required value
        #     type
        def set_dated(instance, attr, date, value):
            overwrite = GetVal(self.obj, self.attr)
            instance.__set_dated_raw(attr, date, value, overwrite)

        # --- rename original set_dated and replace it with a new version
        cls.__set_dated_raw = cls.set_dated
        cls.set_dated = set_dated

        return cls
