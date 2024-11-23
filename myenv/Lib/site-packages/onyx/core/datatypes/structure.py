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

import collections

__all__ = ["Structure", "StructureError"]


###############################################################################
class StructureError(Exception):
    """
    Base class for all Structure exceptions.
    """
    pass


###############################################################################
class Structure(collections.UserDict):
    """
    A Structure is a dictionary that only accepts numerical values and
    implements algebraic manipulations such as:
        - addition and subtraction of structures item by item
        - addition and multiplication by a scalar
    """
    # -------------------------------------------------------------------------
    def __setitem__(self, key, value):
        try:
            value + 0.0
        except TypeError:
            raise StructureError(
                "Incorrect value for pair {0!s}: {1!s}, "
                "only numerical values are acceptable".format(key, value))
        super().__setitem__(key, value)

    # -------------------------------------------------------------------------
    #  addition methods

    def __iadd__(self, other):
        if isinstance(other, Structure):
            for key, value in other.items():
                self[key] = self.get(key, 0.0) + value
        else:
            for key in self:
                self[key] += other
        return self

    def __add__(self, other):
        struct = self.copy()
        if isinstance(other, Structure):
            for key, value in other.items():
                struct[key] = struct.get(key, 0.0) + value
        else:
            for key in struct:
                struct[key] += other
        return struct

    def __radd__(self, scalar):
        struct = self.copy()
        for key in struct:
            struct[key] += scalar
        return struct

    # -------------------------------------------------------------------------
    #  subtraction methods

    def __isub__(self, other):
        if isinstance(other, Structure):
            for key, value in other.items():
                self[key] = self.get(key, 0.0) - value
        else:
            for key in self:
                self[key] -= other
        return self

    def __sub__(self, other):
        struct = self.copy()
        if isinstance(other, Structure):
            for key, value in other.items():
                struct[key] = struct.get(key, 0.0) - value
        else:
            for key in struct:
                struct[key] -= other
        return struct

    def __rsub__(self, scalar):
        struct = self.copy()
        for key in struct:
            struct[key] = scalar - struct[key]
        return struct

    # -------------------------------------------------------------------------
    #  multiplication methods

    def __imul__(self, scalar):
        if isinstance(scalar, Structure):
            raise StructureError(
                "Multiplication of two Structures is not supported")
        try:
            scalar + 0.0
        except TypeError:
            raise StructureError(
                "Multiplication by non-numeric scalar is not supported")
        for key in self:
            self[key] *= scalar
        return self

    def __mul__(self, scalar):
        if isinstance(scalar, Structure):
            raise StructureError(
                "Multiplication of two Structures is not supported")
        try:
            scalar + 0.0
        except TypeError:
            raise StructureError(
                "Multiplication by non-numeric scalar is not supported")
        struct = self.copy()
        for key in struct:
            struct[key] *= scalar
        return struct

    def __rmul__(self, scalar):
        try:
            scalar + 0.0
        except TypeError:
            raise StructureError(
                "Multiplication by non-numeric scalar is not supported")
        struct = self.copy()
        for key in struct:
            struct[key] *= scalar
        return struct

    # -------------------------------------------------------------------------
    def __deepcopy__(self, memo):
        clone = self.copy()
        memo[id(self)] = clone
        return clone

    # -------------------------------------------------------------------------
    def drop_zeros(self, ndigits=None):
        """
        Description:
            Drop items with zero value (up to a given number of digits) in
            place.
        Inputs:
            ndigits - if set, values are rounded to the required number of
                      digits before testing for equality to zero.
        Returns:
            The clensed Structure.
        """
        if ndigits is None:
            self.data = {k: v for k, v in self.items() if v != 0.0}
        else:
            self.data = {
                k: v for k, v in self.items() if round(v, ndigits) != 0.0}

        return self

    # -------------------------------------------------------------------------
    @classmethod
    def to_dict(cls, value):
        """
        Convert recursively a structure into a dictionary.
        """
        if isinstance(value, cls):
            return {
                key: cls.to_dict(val) for key, val in value.items()}
        else:
            return value
