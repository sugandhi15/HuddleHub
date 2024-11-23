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

from .objdb_api import ObjDbQuery, GetObj
from .ufo_base import get_base_classes, BaseField, MutableField, FieldError
from ..datatypes.date import Date
from ..datatypes.curve import Curve
from ..datatypes.gcurve import GCurve
from ..datatypes.hlocv import HlocvCurve
from ..datatypes.structure import Structure
from ..datatypes.table import Table
from ..datatypes.holiday_cal import HolidayCalendar

import pickle
import base64
import gzip
import numbers

__all__ = [
    "StringField",
    "SelectField",
    "IntField",
    "SelectIntField",
    "FloatField",
    "BoolField",
    "BinaryField",
    "DateField",
    "ListField",
    "DictField",
    "SetField",
    "CurveField",
    "GCurveField",
    "HlocvCurveField",
    "StructureField",
    "HolidayCalField",
    "ReferenceField",
    "TableField"
]


# -----------------------------------------------------------------------------
# --- serialize to plain string using base64 encoding
def pickle_loads(val):
    return pickle.loads(gzip.decompress(base64.b64decode(val)))


def pickle_dumps(val):
    return base64.b64encode(gzip.compress(pickle.dumps(val))).decode("utf-8")


###############################################################################
class StringField(BaseField):
    def validate(self, val):
        if not isinstance(val, str):
            raise FieldError(
                f"Invalid input {type(val)}(value: {val}) for <{repr(self)}>")


###############################################################################
class SelectField(StringField):
    def __init__(self, *args, **kwds):
        self.options = kwds.pop("options", None)
        super().__init__(*args, **kwds)
        if not all([isinstance(opt, str) for opt in self.options]):
            types = [type(opt) for opt in self.options]
            raise FieldError(
                "One or more optins are not of type str: {0!s}".format(types))

    def validate(self, val):
        super().validate(val)
        if val not in self.options:
            raise FieldError(
                "Illegal value {0!s} for <{1!r}>. "
                "Valid options are {2!s}".format(val, self, self.options))


###############################################################################
class IntField(BaseField):
    def __init__(self, *args, **kwds):
        self.positive = kwds.pop("positive", False)
        super().__init__(*args, **kwds)

    def validate(self, val):
        if not isinstance(val, int):
            raise FieldError(
                f"Invalid input {type(val)}(value: {val}) for <{repr(self)}>")
        if self.positive and val < 0:
            raise FieldError(
                "Input for <{0!r}> is not positive: {1:d}".format(self, val))


###############################################################################
class SelectIntField(IntField):
    def __init__(self, *args, **kwds):
        self.options = kwds.pop("options", None)
        super().__init__(*args, **kwds)
        if not all([isinstance(opt, int) for opt in self.options]):
            types = [type(opt) for opt in self.options]
            raise FieldError(
                "One or more optins are not of type int: {0!s}".format(types))

    def validate(self, val):
        super().validate(val)
        if val not in self.options:
            raise FieldError(
                "Illegal value {0!s} for <{1!r}>. "
                "Valid options are {2!s}".format(val, self, self.options))


###############################################################################
class FloatField(BaseField):
    def __init__(self, *args, **kwds):
        self.positive = kwds.pop("positive", False)
        super().__init__(*args, **kwds)

    def from_json(self, val):
        # --- force conversion to float
        return float(val)

    def validate(self, val):
        if not isinstance(val, float):
            raise FieldError(
                f"Invalid input {type(val)}(value: {val}) for <{repr(self)}>")
        if self.positive and val < 0.0:
            raise FieldError(
                "Input for <{0!r}> is not positive: {1:f}".format(self, val))


###############################################################################
class BoolField(BaseField):
    def validate(self, val):
        if not isinstance(val, bool):
            raise FieldError(
                "Invalid input {0!s} for <{1!r}>".format(type(val), self))


###############################################################################
class BinaryField(BaseField):
    def from_json(self, val):
        return gzip.decompress(base64.b64decode(val))

    def to_json(self, val):
        return base64.b64encode(gzip.compress(val)).decode("utf-8")

    def validate(self, val):
        if not isinstance(val, bytes):
            raise FieldError(
                "Invalid input {0!s} for <{1!r}>".format(type(val), self))


###############################################################################
class DateField(BaseField):
    def from_json(self, val):
        return Date.parse(val)

    def to_json(self, val):
        return val.isoformat()

    def validate(self, val):
        if not isinstance(val, Date):
            raise FieldError(
                "Invalid input {0!s} for <{1!r}>".format(type(val), self))


###############################################################################
class ListField(MutableField):
    def validate(self, val):
        if not isinstance(val, list):
            raise FieldError(
                "Invalid input {0!s} for <{1!r}>".format(type(val), self))


###############################################################################
class DictField(MutableField):
    def validate(self, val):
        if not isinstance(val, dict):
            raise FieldError(
                "Invalid input {0!s} for <{1!r}>".format(type(val), self))


###############################################################################
class SetField(MutableField):
    def from_json(self, val):
        return val if val is None else set(val)

    def to_json(self, val):
        return val if val is None else list(val)

    def validate(self, val):
        if not isinstance(val, set):
            raise FieldError(
                "Invalid input {0!s} for <{1!r}>".format(type(val), self))


###############################################################################
class CurveField(MutableField):
    def from_json(self, val):
        if val is None:
            return val
        knts = [(Date.parse(r["date"]), r["value"]) for r in val]
        return Curve.create_raw([d for d, v in knts], [v for d, v in knts])

    def to_json(self, crv):
        if crv is None:
            return crv
        else:
            return [{"date": d.isoformat(), "value": v} for d, v in crv]

    def validate(self, val):
        if not isinstance(val, Curve):
            raise FieldError(
                "Invalid input {0!s} for <{1!r}>".format(type(val), self))


###############################################################################
class GCurveField(MutableField):
    def from_json(self, val):
        if val is None:
            return val
        knts = [(Date.parse(r["date"]), pickle_loads(r["value"])) for r in val]
        return GCurve.create_raw([d for d, v in knts], [v for d, v in knts])

    def to_json(self, crv):
        if crv is None:
            return crv
        else:
            return [{"date": d.isoformat(),
                     "value": pickle_dumps(v)} for d, v in crv]

    def validate(self, val):
        if not isinstance(val, GCurve):
            raise FieldError(
                "Invalid input {0!s} for <{1!r}>".format(type(val), self))


###############################################################################
class HlocvCurveField(MutableField):
    def from_json(self, val):
        if val is None:
            return val
        knts = [(Date.parse(row["date"]), row["value"]) for row in val]
        return HlocvCurve.create_raw(
            [d for d, v in knts], [v for d, v in knts])

    def to_json(self, crv):
        if crv is None:
            return crv
        else:
            return [{"date": d.isoformat(),
                     "value": v.tolist()} for d, v in crv]

    def validate(self, val):
        if not isinstance(val, HlocvCurve):
            raise FieldError(
                "Invalid input {0!s} for <{1!r}>".format(type(val), self))


###############################################################################
class StructureField(MutableField):
    def from_json(self, val):
        return val if val is None else Structure(val)

    def to_json(self, val):
        return val if val is None else list(zip(val.keys(), val.values()))

    def validate(self, val):
        if not isinstance(val, Structure):
            raise FieldError(
                "Invalid input {0!s} for <{1!r}>".format(type(val), self))
        # --- all keys should be strings
        if not all(isinstance(k, str) for k in val.keys()):
            FieldError(
                "<{0!r}>, structure keys need to be strings".format(self))
        # --- all values should be numbers
        if not all(isinstance(v, numbers.Number) for v in val.values()):
            FieldError(
                "<{0!r}>, structure values need to be numbers".format(self))


###############################################################################
class TableField(MutableField):
    def from_json(self, val):
        return val if val is None else Table(val)

    def to_json(self, val):
        return val if val is None else val.to_list()

    def validate(self, val):
        if not isinstance(val, Table):
            raise FieldError(
                "Invalid input {0!s} for <{1!r}>".format(type(val), self))


###############################################################################
class HolidayCalField(MutableField):
    def from_json(self, val):
        if val is None:
            return val
        else:
            return HolidayCalendar([Date.parse(d) for d in val])

    def to_json(self, val):
        return val if val is None else [d.isoformat() for d in val.holidays]

    def validate(self, val):
        if not isinstance(val, HolidayCalendar):
            raise FieldError(
                "Invalid input {0!s} for <{1!r}>".format(type(val), self))


###############################################################################
class ReferenceField(StringField):
    def __init__(self, *args, **kwds):
        self.obj_type = kwds.pop("obj_type", None)
        super().__init__(*args, **kwds)

    def validate(self, val):
        # --- accept None as special value used to mark the reference as
        #     undefined
        if val is None:
            return
        if not isinstance(val, str):
            raise FieldError(
                "Invalid input {0!s} for <{1!r}>".format(type(val), self))
        if self.obj_type is None:
            res = ObjDbQuery("""SELECT EXISTS "
                                (SELECT 1 FROM Objects
                                 WHERE ObjName=%s) AS "exists";""",
                             parms=(val,), attr="fetchone")
            if res.exists:
                raise FieldError(
                    "Object {0:s} not found in database".format(val))
        else:
            bases = set(get_base_classes(GetObj(val).__class__))

            if self.obj_type not in bases:
                msg = ("Object {0:s} exists in database, "
                       "but it is not instance of a subclass of {1:s}")
                raise FieldError(msg.format(val, self.obj_type))
