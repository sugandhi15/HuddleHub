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
from .. import ufo_exchange
import unittest


###############################################################################
class UnitTest(OnyxTestCase):
    # -------------------------------------------------------------------------
    def setUp(self):
        super().setUp()
        ufo_exchange.prepare_for_test()

    def test_Code(self):
        self.assertEqual(GetVal("XNYS Exchange", "Code"), "US")
        self.assertEqual(GetVal("XLON Exchange", "Code"), "LN")
        self.assertEqual(GetVal("XEUR Exchange", "Code"), "EUX")


if __name__ == "__main__":
    from onyx.core import UseEphemeralDbs
    with UseEphemeralDbs():
        unittest.main(failfast=True)
