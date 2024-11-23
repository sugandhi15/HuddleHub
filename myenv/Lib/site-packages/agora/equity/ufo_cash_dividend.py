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

from onyx.core import ReferenceField, GetVal
from ..system.ufo_forward_cash import ForwardCash


###############################################################################
class CashDividend(ForwardCash):
    """
    Tradable class that represents a cash dividend payable/receivable.
    """
    Asset = ReferenceField(obj_type="EquityAsset")

    # -------------------------------------------------------------------------
    @property
    def ImpliedName(self):
        sym = GetVal(self.Asset, "Symbol")
        code = GetVal(GetVal(self.Asset, "Exchange"), "Code")
        pay_date = self.PaymentDate.strftime("%d%m%y")
        return ("DVD {0:s} {1:2s} {2:3s} "
                "{3:6s}").format(sym, code, self.Currency, pay_date)
