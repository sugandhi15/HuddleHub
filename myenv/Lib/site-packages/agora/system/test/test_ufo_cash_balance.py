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
from .. import ufo_cash_balance
import unittest


###############################################################################
class UnitTest(OnyxTestCase):
    # -------------------------------------------------------------------------
    def setUp(self):
        super().setUp()
        self.securities = ufo_cash_balance.prepare_for_test()

        assert "CASH USD" in self.securities
        assert "CASH EUR" in self.securities
        assert "CASH GBP" in self.securities

    def test_Leaves(self):
        self.assertEqual(GetVal("CASH USD", "Leaves"),
                         Structure([("CASH USD", 1.0)]))

    def test_MktVal(self):
        self.assertEqual(GetVal("CASH USD", "MktVal"), 1.0)
        self.assertEqual(GetVal("CASH EUR", "MktVal"), 1.0)
        self.assertEqual(GetVal("CASH GBP", "MktVal"), 1.0)

    def test_MktValUSD(self):
        self.assertEqual(GetVal("CASH USD", "MktValUSD"), 1.00)
        self.assertEqual(GetVal("CASH EUR", "MktValUSD"), 1.15)
        self.assertEqual(GetVal("CASH GBP", "MktValUSD"), 1.50)

    def test_ExpectedSecurities(self):
        sec = GetObj("CASH USD")
        self.assertEqual(GetVal("CASH USD", "ExpectedSecurities", "Buy"),
                         [{"Security": sec, "Quantity": 1.0}])
        self.assertEqual(GetVal("CASH USD", "ExpectedSecurities", "Sell"),
                         [{"Security": sec, "Quantity": -1.0}])

    def test_Children(self):
        kids = ChildrenSet(("CASH USD", "MktValUSD"), "Spot")
        self.assertEqual(kids, {"USD/USD"})
        kids = ChildrenSet(("CASH EUR", "MktValUSD"), "Spot")
        self.assertEqual(kids, {"EUR/USD"})
        kids = ChildrenSet(("CASH GBP", "MktValUSD"), "Spot")
        self.assertEqual(kids, {"GBP/USD"})


if __name__ == "__main__":
    from onyx.core import UseEphemeralDbs
    with UseEphemeralDbs():
        unittest.main(failfast=True)
