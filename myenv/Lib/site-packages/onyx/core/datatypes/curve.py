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

from .gcurve import GCurve

import numpy as np

__all__ = ["Curve"]


# -----------------------------------------------------------------------------
def is_numlike(obj):
    """
    Helper function used to determine if an object behaves like a number.
    """
    try:
        obj + 1.0
    except TypeError:
        return False
    else:
        return True


###############################################################################
class Curve(GCurve):
    """
    Curve class based on GCurve and supporting numerical values only.
    """
    # --- this is the default datatype for a Curve
    dtype = np.float64

    # -------------------------------------------------------------------------
    #  A few methods for simple curve algebra. It's always assumed that the
    #  two curves are already aligned
    def __add__(self, other):
        if isinstance(other, self.__class__):
            return self.create_raw(self.dates, self.values + other.values)
        else:
            return self.create_raw(self.dates, self.values + other)

    def __sub__(self, other):
        if isinstance(other, self.__class__):
            return self.create_raw(self.dates, self.values - other.values)
        else:
            return self.create_raw(self.dates, self.values - other)

    def __mul__(self, other):
        if isinstance(other, self.__class__):
            return self.create_raw(self.dates, self.values * other.values)
        elif is_numlike(other):
            return self.create_raw(self.dates, self.values * other)
        else:
            TypeError("cannot multiply a {0:s} "
                      "by a {1:s}".format(self.__class__, other.__class__))

    def __truediv__(self, other):
        if isinstance(other, self.__class__):
            return self.create_raw(self.dates, self.values / other.values)
        elif is_numlike(other):
            return self.create_raw(self.dates, self.values / other)
        else:
            TypeError("cannot multiply a {0:s} "
                      "by a {1:s}".format(self.__class__, other.__class__))

    def __radd__(self, scalar):
        return self.create_raw(self.dates, scalar + self.values)

    def __rsub__(self, scalar):
        return self.create_raw(self.dates, scalar - self.values)

    def __rmul__(self, scalar):
        return self.create_raw(self.dates, scalar * self.values)

    def __rtruediv__(self, scalar):
        return self.create_raw(self.dates, scalar / self.values)
