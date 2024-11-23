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

from ...datatypes.date import Date
from ...datatypes.curve import Curve
from ..curve_fns import Interpolate, ApplyAdjustments

import numpy as np
import unittest


# --- unit tests
class RegTest(unittest.TestCase):
    def setUp(self):
        # --- create a first curve by passing arrays of dates and values
        self.dates = [Date.parse(d)
                      for d in ["F08", "G08", "H08", "J08", "K08", "M08",
                                "N08", "Q08", "U08", "V08", "X08", "Z08"]]
        self.values = np.cumsum(np.ones(12))
        self.refcrv = Curve(self.dates, self.values)

    def tearDown(self):
        # --- perform clean-up actions, if any
        pass

    def test_interpolate(self):
        dt = Date(2009, 1, 1)
        self.assertEqual(12, Interpolate(self.refcrv, dt))
        self.assertEqual(12, Interpolate(self.refcrv, dt, "Step"))
        self.assertEqual(12, Interpolate(self.refcrv, dt, "Linear"))

        dt = Date(2007, 1, 1)
        self.assertEqual(1, Interpolate(self.refcrv, dt))
        self.assertEqual(1, Interpolate(self.refcrv, dt, "Step"))
        self.assertEqual(1, Interpolate(self.refcrv, dt, "Linear"))

        dt = Date(2008, 11, 16)
        self.assertEqual(11, Interpolate(self.refcrv, dt))
        self.assertEqual(11, Interpolate(self.refcrv, dt, "Step"))
        self.assertEqual(11.5, Interpolate(self.refcrv, dt, "Linear"))

    def test_apply_adjustments(self):
        adj_crv = Curve([Date(2008, 6, 15)], [0.1])
        ref_crv = Curve(self.refcrv.dates,
                        [0.1, 0.2, 0.3, 0.4, 0.5, 0.6,
                         7.0, 8.0, 9.0, 10.0, 11.0, 12.0])

        adjusted = ApplyAdjustments(self.refcrv, adj_crv)

        self.assertTrue(np.all(adjusted.dates == ref_crv.dates))
        self.assertTrue(np.allclose(adjusted.values, ref_crv.values))

if __name__ == "__main__":
    unittest.main()
