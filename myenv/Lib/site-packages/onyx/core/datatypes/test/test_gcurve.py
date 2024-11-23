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
from ..gcurve import GCurve, Knot, CurveError

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
        self.refcrv = GCurve(self.dates, self.values)

    def tearDown(self):
        # --- perform clean-up actions, if any
        pass

    def test_len(self):
        self.assertEqual(len(self.refcrv), 12)

    def test_repr(self):
        self.assertEqual(self.refcrv, eval(repr(self.refcrv)))

    def test_constructurs(self):
        # --- test the raw constructor
        crv = GCurve.create_raw(self.refcrv.dates, self.refcrv.values)

        # --- do comparison between curve objects
        self.assertEqual(crv, self.refcrv)

        # --- create a second curve by adding knots iteratively
        crv = GCurve()
        val = 0.0
        for d in self.dates:
            val += 1.0
            crv[d] = val

        # --- do comparison between curve objects
        self.assertEqual(crv, self.refcrv)

        # --- do the comparison of their string representation
        self.assertEqual(crv.__str__(), self.refcrv.__str__())

        # --- check constructor exceptions
        d = Date.today()
        self.assertRaises(CurveError, GCurve, [d, d], [1, 1])
        self.assertRaises(CurveError, GCurve,
                          ([Date(2008, 1, 1), Date(2008, 12, 1)], [1, 1, 1]))

    def test_get(self):
        # --- get an existing knot
        self.assertEqual(self.refcrv[Date(2008, 6, 1)], 6.0)
        # --- test exceptions are raised when the knot is missing
        self.assertRaises(IndexError,
                          self.refcrv.__getitem__, Date(2007, 6, 1))
        self.assertRaises(IndexError,
                          self.refcrv.__getitem__, Date(2008, 6, 15))
        self.assertRaises(IndexError,
                          self.refcrv.__getitem__, Date(2009, 6, 1))

    def test_set(self):
        value = 666
        # --- set at the front of the curve
        date = Date(2007, 1, 1)
        self.refcrv[date] = value
        self.assertEqual(self.refcrv[date], value)
        knot = self.refcrv.front
        self.assertEqual(knot.date, date)
        self.assertEqual(knot.value, value)

        # --- set an existing knot
        date = Date(2008, 6, 1)
        self.assertEqual(self.refcrv[date], 6)
        self.refcrv[date] = value
        self.assertEqual(self.refcrv[date], value)

        # --- set missing knot in the middle
        date = Date(2008, 6, 15)
        self.assertRaises(IndexError, self.refcrv.__getitem__, date)
        self.refcrv[date] = value
        self.assertEqual(self.refcrv[date], value)

        # --- set at the back of the curve
        date = Date.today()
        self.refcrv[date] = value
        self.assertEqual(self.refcrv[date], value)
        knot = self.refcrv.back
        self.assertEqual(knot.date, date)
        self.assertEqual(knot.value, value)

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
        self.assertEqual(self.refcrv.front, Knot(Date(2008, 1, 1), 1.0))
        self.assertEqual(self.refcrv.front.date, Date(2008, 1, 1))
        self.assertEqual(self.refcrv.front.value, 1.0)
        self.assertEqual(self.refcrv.back, Knot(Date(2008, 12, 1), 12.0))
        self.assertEqual(self.refcrv.back.date, Date(2008, 12, 1))
        self.assertEqual(self.refcrv.back.value, 12.0)

    def test_dates_and_values(self):
        values = np.array([1.0, 2.0, 3.0, 4.0, 5.0,
                           6.0, 7.0, 8.0, 9.0, 10.0, 11.0, 12.0])
        self.assertEqual(sum(self.refcrv.values - values), 0.0)
        dates = np.array([733042, 733073, 733102, 733133, 733163, 733194,
                          733224, 733255, 733286, 733316, 733347, 733377])
        self.assertEqual(sum(self.refcrv.ordinals - dates), 0.0)

    def test_pickling(self):
        new_crv = pickle.loads(pickle.dumps(self.refcrv, -1))
        self.assertEqual(new_crv, self.refcrv)

    def test_crop(self):
        sd = Date.parse("N08")
        ed = Date.parse("X08")
        dates = [Date.parse(d) for d in ["N08", "Q08", "U08", "V08", "X08"]]
        values = [7, 8, 9, 10, 11]
        crv = GCurve(dates, values, dtype=float)
        self.assertEqual(self.refcrv.crop(sd, ed), crv)
        self.assertEqual(self.refcrv.crop(Date(2008, 6, 15),
                                          Date(2008, 11, 15)), crv)
        dates = [Date.parse(d) for d in
                 ["N08", "Q08", "U08", "V08", "X08", "Z08"]]
        values = [7, 8, 9, 10, 11, 12]
        crv = GCurve(dates, values, dtype=float)
        self.assertEqual(self.refcrv.crop(Date(2008, 6, 15),
                                          Date(2009, 12, 31)), crv)


if __name__ == "__main__":
    unittest.main()
