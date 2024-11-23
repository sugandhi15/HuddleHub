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

from ...datatypes.date import Date, DateError
from ..date_fns import LYY2Date, Date2LYY, Date2QQYY
from ..date_fns import CalcTerm, DateRange, CountBizDays

import unittest


# --- unit tests
class RegTest(unittest.TestCase):
    def setUp(self):
        # --- perform set-up actions, if any
        self.lyy_codes = ["F08", "G08", "H08", "J08", "K08", "M08",
                          "N08", "Q08", "U08", "V08", "X08", "Z08"]
        self.qqyy_codes = ["Q108", "Q108", "Q108", "Q208", "Q208", "Q208",
                           "Q308", "Q308", "Q308", "Q408", "Q408", "Q408"]
        self.dates = [Date.parse(lyy) for lyy in self.lyy_codes]

    def tearDown(self):
        # --- perform clean-up actions, if any
        pass

    def test_LYY2Date(self):
        self.assertRaises(DateError, LYY2Date, "W99")
        for lyy, d in zip(self.lyy_codes, self.dates):
            self.assertEqual(LYY2Date(lyy), d)

    def test_Date2LYY(self):
        self.assertRaises(DateError, Date2LYY, Date(1900, 1, 1))
        self.assertRaises(DateError, Date2LYY, Date(2100, 1, 1))
        for lyy, d in zip(self.lyy_codes, self.dates):
            self.assertEqual(Date2LYY(d), lyy)

    def test_Date2QQYY(self):
        self.assertRaises(DateError, Date2QQYY, Date(1900, 1, 1))
        self.assertRaises(DateError, Date2QQYY, Date(2100, 1, 1))
        for qqyy, d in zip(self.qqyy_codes, self.dates):
            self.assertEqual(Date2QQYY(d), qqyy)

    def test_CalcTerm(self):
        self.assertEqual(CalcTerm(Date(2006, 12, 31), Date(2007, 12, 31)), 1.0)
        # --- 2008 is a leap year
        self.assertEqual(CalcTerm(Date(2007, 12, 31),
                                  Date(2008, 12, 31), 366), 1.0)

    def test_DateRange(self):
        self.assertEqual(self.dates,
                         [d for d in DateRange(Date(2008, 1, 1),
                                               Date(2008, 12, 31), "+1m")])

    def test_CountBizDays(self):
        self.assertEqual(261, CountBizDays(Date(2007, 1, 1),
                                           Date(2007, 12, 31)))
        self.assertEqual(262, CountBizDays(Date(2008, 1, 1),
                                           Date(2008, 12, 31)))

if __name__ == "__main__":
    unittest.main()
