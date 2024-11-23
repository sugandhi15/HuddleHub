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

from onyx.core import GetVal, ChildrenSet, OnyxTestCase
from .. import ufo_commod_futures

import unittest


###############################################################################
class UnitTest(OnyxTestCase):
    # -------------------------------------------------------------------------
    def setUp(self):
        super().setUp()
        self.sec, *_ = ufo_commod_futures.prepare_for_test()

    # -------------------------------------------------------------------------
    def test_MktVal(self):
        self.assertAlmostEqual(GetVal(self.sec, "MktVal"), 100, 8)

    # -------------------------------------------------------------------------
    def test_MktValUSD(self):
        self.assertAlmostEqual(GetVal(self.sec, "MktValUSD"), 115, 8)

    # -------------------------------------------------------------------------
    def test_TradeTypes(self):
        tt = {
            "Buy": "BuySecurities",
            "Sell": "SellSecurities",
            "Delivery": "DeliverySecurities",
        }
        self.assertEqual(GetVal(self.sec, "TradeTypes"), tt)

    # -------------------------------------------------------------------------
    def test_Children(self):
        kids = ChildrenSet((self.sec, "MktValUSD"), "Spot")
        self.assertEqual(kids, {GetVal(self.sec, "Asset"), "EUR/USD"})


if __name__ == "__main__":
    from onyx.core.utils.unittest import UseEphemeralDbs
    with UseEphemeralDbs():
        unittest.main(failfast=True)
