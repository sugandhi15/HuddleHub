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

import datetime
import unittest
import pickle


# --- Unit tests
class RegTest(unittest.TestCase):
    def setUp(self):
        # --- perform set-up actions, if any
        pass

    def tearDown(self):
        # perform clean-up actions, if any
        pass

    def test_constructors(self):
        self.assertEqual(Date.today(), datetime.date.today())
        self.assertLessEqual(Date.now(), datetime.datetime.now())
        ref = "01-Jan-2008"
        self.assertEqual(Date(2008, 1, 1).__str__(), ref)
        self.assertEqual(Date.parse("01Jan08").__str__(), ref)
        self.assertEqual(Date.parse("01 Jan 08").__str__(), ref)
        self.assertEqual(Date.parse("01-Jan-08").__str__(), ref)
        self.assertEqual(Date.parse("F08").__str__(), ref)
        # --- test conversion to float and back
        ref = Date(2008, 1, 1)
        self.assertEqual(Date.parse(ref.ordinal), ref)
        ref = Date(2008, 1, 1, 10, 33, 48, 0)
        self.assertEqual(Date.parse(ref.ordinal), ref)

    def test_date_algebra(self):
        d0 = Date(2008, 1, 1)
        d1 = Date(2008, 12, 31)
        dt = d1 - d0
        self.assertEqual(dt.days, 366 - 1)
        d0 = Date(2009, 1, 1)
        d1 = Date(2009, 12, 31)
        dt = d1 - d0
        self.assertEqual(dt.days, 365 - 1)
        # --- date comparisons
        self.assertTrue(Date(2008, 1, 1) < Date(2009, 1, 1))
        self.assertFalse(Date(2008, 1, 1) == Date(2009, 1, 1))
        self.assertTrue(Date(2008, 1, 1) != Date(2009, 1, 1))
        self.assertFalse(Date(2008, 1, 1) > Date(2009, 1, 1))
        # --- now between Date and datetime objects
        self.assertTrue(Date(2008, 1, 1) == datetime.date(2008, 1, 1))
        self.assertTrue(Date(2009, 1, 1) != datetime.date(2008, 1, 1))
        self.assertTrue(Date(2009, 1, 1) > datetime.date(2008, 1, 1))
        self.assertTrue(Date(2008, 1, 1) == datetime.datetime(2008, 1, 1))
        self.assertTrue(Date(2009, 1, 1) != datetime.datetime(2008, 1, 1))
        self.assertTrue(Date(2009, 1, 1) > datetime.datetime(2008, 1, 1))

    def test_pickling(self):
        d0 = Date(1977, 6, 8)
        d1 = pickle.loads(pickle.dumps(d0, 2))
        # --- check that data representations are identical
        self.assertEqual(d0, d1)
        # --- check that string representations are identical
        self.assertEqual(d0.__str__(), d1.__str__())

    def test_is_weekday(self):
        from calendar import THURSDAY
        self.assertFalse(Date(2008, 1, 1).is_weekday(THURSDAY))
        self.assertTrue(Date(2009, 1, 1).is_weekday(THURSDAY))

if __name__ == "__main__":
    unittest.main()
