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
"""
Implements base and meta classes for universal financial objects (UFOs) and all
persistable fields.
"""

from ..datatypes.date import Date

import numpy as np
import getpass
import json
import copy

__all__ = ["FieldError", "UfoError", "UfoBase"]

USER = getpass.getuser()
SPECIAL = ("Name", "ObjType", "Version",
           "ChangedBy", "TimeCreated", "LastUpdated")
SKIP = {"_data", "_json_fields"}.union(SPECIAL)


# -----------------------------------------------------------------------------
def get_base_classes(cls):
    yield cls.__name__
    for base in cls.__bases__:
        yield from get_base_classes(base)


###############################################################################
class custom_encoder(json.JSONEncoder):
    # -------------------------------------------------------------------------
    def default(self, obj):
        if isinstance(obj, Date):
            return {
                "__type__": "Date",
                "isostring": obj.isoformat(),
            }
        elif isinstance(obj, np.float32):
            return {
                "__type__": "np.float32",
                "value": float(obj),
            }
        elif isinstance(obj, np.float):
            return {
                "__type__": "np.float",
                "value": float(obj),
            }
        elif isinstance(obj, np.int64):
            return {
                "__type__": "np.int64",
                "value": int(obj),
            }
        elif isinstance(obj, np.integer):
            return {
                "__type__": "np.integer",
                "value": int(obj),
            }

        # --- let the base class default method raise the TypeError
        return json.JSONEncoder.default(self, obj)


###############################################################################
class custom_decoder(json.JSONDecoder):
    # -------------------------------------------------------------------------
    def __init__(self, *args, **kdws):
        super().__init__(*args, object_hook=self.dict_to_object, **kdws)

    # -------------------------------------------------------------------------
    def dict_to_object(self, obj):
        try:
            typename = obj.pop("__type__")
        except KeyError:
            return obj
        if typename == "Date":
            try:
                return Date.parse(obj["isostring"])
            except KeyError:
                return Date(**obj)
        elif typename == "np.float":
            return np.float64(obj["value"])
        elif typename == "np.float32":
            return np.float32(obj["value"])
        elif typename == "np.integer":
            return np.int32(obj["value"])
        elif typename == "np.int64":
            return np.int64(obj["value"])
        else:
            # --- put this back together
            obj["__type__"] = typename
            return obj


###############################################################################
class FieldError(Exception):
    pass


###############################################################################
class BaseField(object):
    # -------------------------------------------------------------------------
    def __init__(self, default=None):
        if default is not None:
            self.validate(default)
        self.name = None
        self.default = default

    # -------------------------------------------------------------------------
    def __get__(self, instance, cls):
        if instance is None:
            # --- it's convenient to return the descriptor itself when accessed
            #     on the class so that getattr(type(obj)), "fieldname") works
            return self
        try:
            return instance._data[self.name]
        except KeyError:
            instance._data[self.name] = self.default
            return self.default

    # -------------------------------------------------------------------------
    def __set__(self, instance, val):
        self.validate(val)
        instance._data[self.name] = val

    # -------------------------------------------------------------------------
    def from_json(self, val):
        """
        This method is used to prepare the field value for json reverse
        serialization (needed for data types that are not naturally supported
        by json format).
        """
        return val

    # -------------------------------------------------------------------------
    def to_json(self, val):
        """
        This method is used to prepare the field value for json serialization
        (needed for data types that are not naturally supported by json
        format).
        """
        return val

    # -------------------------------------------------------------------------
    def validate(self, val):
        pass

    # -------------------------------------------------------------------------
    def __repr__(self):
        return "{0:s} {1!s}".format(self.__class__.__name__, self.name)


###############################################################################
class MutableField(BaseField):
    pass


###############################################################################
class UfoError(Exception):
    pass


###############################################################################
class UfoMetaClass(type):
    # -------------------------------------------------------------------------
    def __new__(mcl, name, bases, nmspc):
        if "__init__" in nmspc:
            raise UfoError("Classes derived from UfoBase"
                           "cannot implement the __init__ method")

        json_flds = set()

        # --- inherit StoredAttrs of all UFO bases (if any)
        for base in bases:
            if hasattr(base, "_json_fields"):
                json_flds.update(base._json_fields)

        # --- add class specific StoredAttrs and set their name
        for attr_name, attr in nmspc.items():
            if isinstance(attr, BaseField):
                json_flds.add(attr_name)
                attr.name = attr_name

        # --- StoredAttrs is a set with the list of persisted attributes
        nmspc["StoredAttrs"] = json_flds.union(SPECIAL)

        # --- json_flds is a special attribute
        nmspc["_json_fields"] = json_flds

        return super().__new__(mcl, name, bases, nmspc)

    # -------------------------------------------------------------------------
    #  class instantiation
    def __call__(cls, *args, **kwds):
        """
        This method is the one invoked to create a new instance of a class. In
        turn, it invokes the __new__ method of the associated class.
        NB: this method will not be invoked when an object is de-serialized.
        """
        if len(args):
            raise UfoError("Classes derived from UfoBase cannot "
                           "be instantiated with positional arguments")

        # --- create an instance of the class
        instance = cls.__new__(cls)

        # --- set default values for the special attributes
        now = Date.now()

        setattr(instance, "Name", kwds.pop("Name", None))
        setattr(instance, "ObjType", kwds.pop("ObjType", cls.__name__))
        setattr(instance, "Version", kwds.pop("Version", 0))
        setattr(instance, "ChangedBy", kwds.pop("ChangedBy", USER))
        setattr(instance, "TimeCreated", kwds.pop("TimeCreated", now))
        setattr(instance, "LastUpdated", kwds.pop("LastUpdated", now))

        # --- set stored attributes based on input values
        for attr, val in kwds.items():
            if attr in instance._json_fields:
                setattr(instance, attr, val)
            else:
                raise UfoError("Unrecognized stored "
                               "attribute for {0!s}: {1:s}".format(cls, attr))

        # --- call post-initialization method if available
        if hasattr(cls, "__post_init__"):
            instance.__post_init__()

        return instance


###############################################################################
class UfoBase(metaclass=UfoMetaClass):
    # -------------------------------------------------------------------------
    def __new__(cls, *args, **kwds):
        # --- the instance is created using the super-class __new__ method
        instance = super().__new__(cls, *args, **kwds)

        # --- the _data attribute, which will store the values of all the
        #     stored attributes, is initialized here to an empty dictionary.
        instance._data = {}

        # --- for each mutable field with non-trivial default value, make a
        #     deepcopy of such default value to avoid it being shared across
        #     multiple instances.
        for field_name in instance._json_fields:
            field = getattr(cls, field_name)
            if isinstance(field, MutableField) and field.default is not None:
                setattr(instance, field_name, copy.deepcopy(field.default))

        return instance

    # -------------------------------------------------------------------------
    def to_json(self):
        if self.Name == "":
            raise UfoError("Name attribute cannot be an empty string")

        cls = self.__class__

        # --- create json object
        json_data = {name: getattr(cls, name).to_json(getattr(self, name))
                     for name in self._json_fields}

        return json.dumps(json_data, cls=custom_encoder)

    # -------------------------------------------------------------------------
    def from_json(self, values, skip_missing_attrs):
        cls = self.__class__
        for name, value in json.loads(values, cls=custom_decoder).items():
            try:
                self._data[name] = getattr(cls, name).from_json(value)
            except AttributeError:
                if not skip_missing_attrs:
                    raise

    # -------------------------------------------------------------------------
    def __eq__(self, other):
        self_attrs = self.StoredAttrs.difference(SKIP)
        other_attrs = other.StoredAttrs.difference(SKIP)

        if self_attrs != other_attrs:
            return False

        for attr in self_attrs:
            if getattr(self, attr) != getattr(other, attr):
                return False

        return True

    # -------------------------------------------------------------------------
    def __repr__(self):
        return "<{0:s} {1!s}>".format(self.ObjType, self.Name)

    # -------------------------------------------------------------------------
    def clone(self, **overrides):
        """
        Create a copy of current object and apply optional overrides.
        """
        # --- create timestamp
        now = Date.now()

        # --- create a new instance from current stored attributes and
        #     overwrite the special attributes. Finally, overrides are applied.
        #     NB: attributes with None as value are excluded as it is assumed
        #         they weren't set explicitly.
        stored = {attr: copy.deepcopy(getattr(self, attr))
                  for attr in self.StoredAttrs}
        stored = {attr: val for attr, val in stored.items() if val is not None}
        stored.update({
            "Name": None,
            "Version": 0,
            "TimeCreated": now,
            "LastUpdated": now,
            "ChangedBy": USER.upper(),
        })
        stored.update(overrides)

        return self.__class__(**stored)

    # -------------------------------------------------------------------------
    def copy_from(self, other):
        """
        Overwrite all attributes with those of another instance.
        """
        if self.ObjType != other.ObjType:
            raise TypeError("Can only copy from an object of the same type")
        for attr in other.StoredAttrs:
            if attr in SKIP:
                continue
            setattr(self, attr, getattr(other, attr))
