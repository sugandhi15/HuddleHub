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

from ..hlocv import HlocvCurve
from ..date import Date

import numpy as np
import unittest
import pickle


# --- Unit tests
class RegTest(unittest.TestCase):
    def setUp(self):
        # --- set the seed to get predictable values
        np.random.seed(666)

        # --- generate random values
        x = np.cumsum(np.random.standard_normal(12+1))

        # --- create a test curve
        dates = [Date.parse(d)
                 for d in ["F08", "G08", "H08", "J08", "K08", "M08",
                           "N08", "Q08", "U08", "V08", "X08", "Z08"]]

        xh = lambda k: max(x[k], x[k+1])  # analysis:ignore
        xl = lambda k: min(x[k], x[k+1])  # analysis:ignore

        values = [(xh(k), xl(k), x[k], x[k+1], 100) for k in range(len(dates))]
        self.refcrv = HlocvCurve(dates, values)

    def tearDown(self):
        # --- perform clean-up actions, if any
        pass

    def test_set(self):
        value = [1.0, 2.0, 3.0, 4.0, 5.0]
        # --- set at the front of the curve
        date = Date(2007, 1, 1)
        self.refcrv[date] = value
        self.assertTrue(np.allclose(self.refcrv[date], value))
        knot = self.refcrv.front
        self.assertEqual(knot.date, date)
        self.assertTrue(np.allclose(knot.value, value))

        # --- set an existing knot
        date = Date(2008, 6, 1)
        self.assertTrue(np.allclose(self.refcrv[date],
                                    np.array([2.72447971, 2.70545145,
                                              2.70545145, 2.72447971, 100.0])))
        self.refcrv[date] = value
        self.assertTrue(np.allclose(self.refcrv[date], value))

        # --- set missing knot in the middle
        date = Date(2008, 6, 15)
        self.assertRaises(IndexError, self.refcrv.__getitem__, date)
        self.refcrv[date] = value
        self.assertTrue(np.allclose(self.refcrv[date], value))

        # --- set at the back of the curve
        date = Date.today()
        self.refcrv[date] = value
        self.assertTrue(np.allclose(self.refcrv[date], value))
        knot = self.refcrv.back
        self.assertEqual(knot.date, date)
        self.assertTrue(np.allclose(knot.value, value))

    def test_del(self):
        # --- delete an existing knot
        del self.refcrv[Date(2008, 6, 1)]
        self.assertFalse(Date(2008, 6, 1) in self.refcrv)
        # --- delete a missing knot
        self.assertRaises(IndexError,
                          self.refcrv.__delitem__, Date(2008, 6, 1))
        self.assertRaises(IndexError,
                          self.refcrv.__delitem__, Date(2009, 6, 1))

    def test_has(self):
        self.assertFalse(Date(2007, 6, 1) in self.refcrv)
        self.assertTrue(Date(2008, 6, 1) in self.refcrv)
        self.assertFalse(Date(2008, 6, 15) in self.refcrv)
        self.assertFalse(Date(2009, 6, 1) in self.refcrv)

    def test_back_and_front(self):
        self.assertEqual(self.refcrv.front.date, Date(2008, 1, 1))
        self.assertAlmostEqual(self.refcrv.front.value[0], 1.30415409, 8)
        self.assertEqual(self.refcrv.back.date, Date(2008, 12, 1))
        self.assertAlmostEqual(self.refcrv.back.value[0], 2.29092902, 8)

    def test_pickling(self):
        new_crv = pickle.loads(pickle.dumps(self.refcrv, 2))
        self.assertEqual(new_crv, self.refcrv)
        self.assertEqual(new_crv.__str__(), self.refcrv.__str__())

if __name__ == "__main__":
    unittest.main()
