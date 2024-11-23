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
from ..rdate import RDate

import datetime
import unittest


# --- Unit tests
class RegTest(unittest.TestCase):
    def setUp(self):
        # --- perform set-up actions, if any
        pass

    def tearDown(self):
        # --- perform clean-up actions, if any
        pass

    def test_apply_rule(self):
        zero_shift = RDate("+0d")
        for d in (datetime.date.today(), datetime.datetime.now()):
            self.assertEqual(d + zero_shift, d)

    def test_exceptions(self):
        zero_shift = RDate("+0d")
        with self.assertRaises(ValueError):
            "abc" + zero_shift

    def test_daterule(self):
        d0 = Date(2008, 1, 1)
        self.assertEqual(d0 + RDate("+e+1m"), Date(2008, 2, 29))
        self.assertEqual(d0 + RDate("+e+25d+1y+1m+0J"), Date(2009, 3, 1))
        d0 = Date(2008, 1, 5)
        self.assertEqual(d0 + RDate("+0b"), Date(2008, 1, 7))
        self.assertEqual(d0 + RDate("+5b"), Date(2008, 1, 11))
        self.assertEqual(d0 + RDate("-0b"), Date(2008, 1, 4))
        self.assertEqual(d0 + RDate("-5b"), Date(2007, 12, 31))
        d0 = Date(2008, 4, 28)
        self.assertEqual(d0 + RDate("A"), Date(2008, 1, 1))
        self.assertEqual(d0 + RDate("q"), Date(2008, 4, 1))
        self.assertEqual(d0 + RDate("Q"), Date(2008, 6, 30))
        self.assertEqual(d0 + RDate("E"), Date(2008, 12, 31))
        d0 = Date(2008, 6, 18)
        self.assertEqual(d0 + RDate("-1M"), Date(2008, 6, 16))
        self.assertEqual(d0 + RDate("+1M"), Date(2008, 6, 23))
        self.assertEqual(d0 + RDate("-1F"), Date(2008, 6, 13))
        self.assertEqual(d0 + RDate("+1F"), Date(2008, 6, 20))
        # --- last monday and friday of the month
        self.assertEqual(d0 + RDate("+e-1M"), Date(2008, 6, 30))
        self.assertEqual(d0 + RDate("+e-1F"), Date(2008, 6, 27))

if __name__ == "__main__":
    unittest.main()
