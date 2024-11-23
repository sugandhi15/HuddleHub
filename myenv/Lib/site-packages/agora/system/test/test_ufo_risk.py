###############################################################################
#
#   Copyright: (c) 2015-2020 Carlo Sbraccia
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

from onyx.core import GetVal, Structure, OnyxTestCase
from .. import ufo_risk
import unittest


###############################################################################
class UnitTest(OnyxTestCase):
    # -------------------------------------------------------------------------
    def setUp(self):
        super().setUp()
        self.book, *_ = ufo_risk.prepare_for_test()

    def compareStructures(self, first, second, places):
        diff = first - second
        for value in diff.values():
            self.assertAlmostEqual(value, 0.0, places)

    def test_MktVal(self):
        self.assertAlmostEqual(GetVal(self.book, "MktVal"), 200.0, 8)

    def test_MktValUSD(self):
        self.assertAlmostEqual(GetVal(self.book, "MktValUSD"), 300.0, 8)

    def test_Deltas(self):
        ref_deltas = Structure({"EQ NG/ LN": -2000.0})
        self.compareStructures(GetVal(self.book, "Deltas"), ref_deltas, 4)

    def test_Exposures(self):
        self.assertAlmostEqual(GetVal(self.book, "GrossExposure"), 18000.0, 4)
        self.assertAlmostEqual(GetVal(self.book, "NetExposure"), -18000.0, 4)

    def test_FX(self):
        GetVal(self.book, "FxExposures")
        ref_fx = Structure({
            "EUR/USD": 11869.565217391306,
            "GBP/USD": -8900.0
        })
        self.compareStructures(GetVal(self.book, "FxExposures"), ref_fx, 8)


if __name__ == "__main__":
    from onyx.core import UseEphemeralDbs
    with UseEphemeralDbs():
        unittest.main(failfast=True)
