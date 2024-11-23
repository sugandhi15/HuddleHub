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

from onyx.core import GetVal, OnyxTestCase
from .. import ufo_commod_contract

import unittest


###############################################################################
class UnitTest(OnyxTestCase):
    # -------------------------------------------------------------------------
    def setUp(self):
        super().setUp()
        (self.cnt, self.prc), *_ = ufo_commod_contract.prepare_for_test()

    def test_Ticker(self):
        tickers = GetVal(self.cnt, "Tickers")
        self.assertEqual(GetVal(self.cnt, "Ticker"), tickers["Bloomberg"])

    def test_UniqueId(self):
        cnt_id_str = "CO2 EUA {0:s}".format(GetVal(self.cnt, "DeliveryMonth"))
        self.assertEqual(GetVal(self.cnt, "UniqueId"), cnt_id_str)

    def test_Spot(self):
        self.assertEqual(GetVal(self.cnt, "Spot"), self.prc)


if __name__ == "__main__":
    from onyx.core import UseEphemeralDbs
    with UseEphemeralDbs():
        unittest.main(failfast=True)
