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

from .gcurve import GCurve, CurveError

import numpy as np
import enum

__all__ = ["HlocvCurve", "HlocvCurveError"]


###############################################################################
class Fields(enum.IntEnum):
    High = 0
    Low = 1
    Open = 2
    Close = 3
    Volume = 4


# -----------------------------------------------------------------------------
class HlocvCurveError(CurveError):
    pass


###############################################################################
class HlocvCurve(GCurve):
    """
    Class representing a HLOCV curve, generally used for daily stock prices. It
    inherits from the generic GCurve.
    """
    # --- this is the default datatype for a HlocvCurve
    dtype = np.float64

    # -------------------------------------------------------------------------
    def __init__(self, dates=None, values=None):
        if values is not None and len(values):
            _, nfields = np.array(values).shape
            if nfields != len(Fields):
                raise HlocvCurveError("values should be an "
                                      "array/list of n rows "
                                      "and 5 columns (one for each field)")

        super().__init__(dates, values)

    def __setitem__(self, date, val):
        val = np.array(val, dtype=self.dtype)
        idx = self.dates.searchsorted(date)
        if idx == len(self.dates):
            self.dates = np.append(self.dates, date)
            self.values = np.vstack([self.values, val])
        elif self.dates[idx] == date:
            self.values[idx,:] = val  # analysis:ignore
        else:
            self.dates = np.insert(self.dates, idx, date)
            self.values = np.insert(self.values, idx, val, axis=0)

    def __delitem__(self, date):
        idx = self.dates.searchsorted(date)
        if self.dates[idx] == date:
            self.dates = np.delete(self.dates, idx)
            self.values = np.delete(self.values, idx, axis=0)
        else:
            raise IndexError

    # -------------------------------------------------------------------------
    #  methods to return arrays for a specific HLOCV field:
    #    - highs
    #    - lows
    #    - opens
    #    - closes
    #    - volumes
    @property
    def highs(self):
        return self.values[:,Fields.High]  # analysis:ignore

    @property
    def lows(self):
        return self.values[:,Fields.Low]  # analysis:ignore

    @property
    def opens(self):
        return self.values[:,Fields.Open]  # analysis:ignore

    @property
    def closes(self):
        return self.values[:,Fields.Close]  # analysis:ignore

    @property
    def volumes(self):
        return self.values[:,Fields.Volume]  # analysis:ignore

    # -------------------------------------------------------------------------
    def curve(self, field="close"):
        """
        Description:
            Convert a HLOCV curve to a scalar curve.
        Inputs:
            field - choose among High, Low, Open, Close, Volume
        Returns:
            A new Curve.
        """
        idx = getattr(Fields, field)
        return self.create_raw(self.dates, self.values[:,idx]) # analysis:ignore
