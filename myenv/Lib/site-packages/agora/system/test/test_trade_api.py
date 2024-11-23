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

from onyx.core import GetVal, Structure, OnyxTestCase
from .. import trade_api
import unittest


###############################################################################
class UnitTest(OnyxTestCase):
    def setUp(self):
        super().setUp()
        self.cash_trade, self.cfd_trade = trade_api.prepare_for_test()

    def compareStructures(self, first, second, places):
        self.assertEqual(first.keys(), second.keys())
        for key, value in first.items():
            self.assertAlmostEqual(value, second[key], places)

    def test_MktValUSD(self):
        self.assertAlmostEqual(GetVal(self.cash_trade, "MktValUSD"), 150.0, 8)
        self.assertAlmostEqual(GetVal(self.cfd_trade, "MktValUSD"), 150.0, 8)

    def test_Deltas(self):
        ref = Structure([("EQ NG/ LN", -1000.0)])
        self.compareStructures(GetVal(self.cash_trade, "Deltas"), ref, 4)
        self.compareStructures(GetVal(self.cfd_trade, "Deltas"), ref, 4)

    def test_Exposures(self):
        usd_exposure = 13500.0
        eur_exposure = usd_exposure / 1.15
        # --- cash trade is denominated in EUR (PaymentUnit is EUR)
        self.assertAlmostEqual(eur_exposure,
                               GetVal(self.cash_trade, "GrossExposure"), 4)
        self.assertAlmostEqual(-eur_exposure,
                               GetVal(self.cash_trade, "NetExposure"), 4)
        # --- cfd trade is denominated in USD (PaymentUnit is not set)
        self.assertAlmostEqual(usd_exposure,
                               GetVal(self.cfd_trade, "GrossExposure"), 4)
        self.assertAlmostEqual(-usd_exposure,
                               GetVal(self.cfd_trade, "NetExposure"), 4)


if __name__ == "__main__":
    from onyx.core import UseEphemeralDbs
    with UseEphemeralDbs():
        unittest.main(failfast=True)
