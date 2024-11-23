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

from onyx.core import GetVal, GetObj, Structure, ChildrenSet, OnyxTestCase
from ..ufo_cash_balance import CashBalance
from .. import ufo_forward_cash
import unittest


###############################################################################
class UnitTest(OnyxTestCase):
    # -------------------------------------------------------------------------
    def setUp(self):
        super().setUp()
        self.fwdusd, self.fwdeur, *_ = ufo_forward_cash.prepare_for_test()

    def test_Leaves(self):
        self.assertEqual(GetVal(self.fwdusd, "Leaves"),
                         Structure([(self.fwdusd, 1.0)]))

    def test_MktVal(self):
        self.assertEqual(GetVal(self.fwdusd, "MktVal"), 1.0)
        self.assertEqual(GetVal(self.fwdeur, "MktVal"), 1.0)

    def test_MktValUSD(self):
        self.assertEqual(GetVal(self.fwdusd, "MktValUSD"), 1.00)
        self.assertEqual(GetVal(self.fwdeur, "MktValUSD"), 1.15)

    def test_TradeTypes(self):
        tt = {
            "Pay/Receive": "PayReceiveSecurities",
            "Buy": "BuySecurities",
            "Sell": "SellSecurities"
        }
        self.assertEqual(GetVal(self.fwdusd, "TradeTypes"), tt)

    def test_ExpectedSecurities(self):
        sec_fwdusd = GetObj(self.fwdusd)
        self.assertEqual(GetVal(self.fwdusd, "ExpectedSecurities", "Buy"),
                         [{"Security": sec_fwdusd, "Quantity": 1.0}])
        self.assertEqual(GetVal(self.fwdusd, "ExpectedSecurities", "Sell"),
                         [{"Security": sec_fwdusd, "Quantity": -1.0}])
        self.assertEqual(GetVal(self.fwdusd,
                                "ExpectedSecurities", "Pay/Receive"),
                         [{"Security": CashBalance(Currency="USD"),
                           "Quantity": 1.0}])

    def test_Children(self):
        kids = ChildrenSet((self.fwdusd, "MktValUSD"), "Spot")
        self.assertEqual(kids, {"USD/USD"})
        kids = ChildrenSet((self.fwdeur, "MktValUSD"), "Spot")
        self.assertEqual(kids, {"EUR/USD"})


if __name__ == "__main__":
    from onyx.core import UseEphemeralDbs
    with UseEphemeralDbs():
        unittest.main(failfast=True)
