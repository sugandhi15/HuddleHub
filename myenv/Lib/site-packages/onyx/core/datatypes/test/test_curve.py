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

from ..date import Date
from ..curve import Curve

import numpy as np
import unittest
import pickle


# --- Unit tests
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

    def test_algebra(self):
        values = self.refcrv.values
        self.assertEqual(2.0*self.refcrv - self.refcrv*1.0, self.refcrv)
        self.assertEqual(2.0*self.refcrv / 2.0, self.refcrv)
        self.assertEqual(sum(1.0 / values), sum((1.0 / self.refcrv).values))
        self.assertEqual(sum(values*values),
                         sum((self.refcrv*self.refcrv).values))

    def test_pickling(self):
        new_crv = pickle.loads(pickle.dumps(self.refcrv, -1))
        self.assertEqual(new_crv, self.refcrv)

if __name__ == "__main__":
    unittest.main()
