###############################################################################
#
#   Copyright: (c) 2015-2018 Carlo Sbraccia
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

from onyx.core import Date, Knot, GetVal, OnyxTestCase
from .. import ufo_currency_cross
import unittest


###############################################################################
class UnitTest(OnyxTestCase):
    # -------------------------------------------------------------------------
    def setUp(self):
        super().setUp()
        self.marks = ufo_currency_cross.prepare_for_test()

    def test_Spot(self):
        for cross, value in self.marks.items():
            self.assertEqual(GetVal(cross, "Spot"), value)

    def test_Last(self):
        for cross, value in self.marks.items():
            self.assertIsInstance(GetVal(cross, "Last"), Knot)
            self.assertEqual(GetVal(cross, "Last"),
                             Knot(Date.today(), value))

    def test_GetCurve(self):
        for cross, value in self.marks.items():
            crv = GetVal(cross, "GetCurve")
            self.assertTrue(len(crv) > 0)
            self.assertEqual(crv.back.date, Date.today())
            self.assertEqual(crv.back.value, value)


if __name__ == "__main__":
    from onyx.core import UseEphemeralDbs
    with UseEphemeralDbs():
        unittest.main(failfast=True)
