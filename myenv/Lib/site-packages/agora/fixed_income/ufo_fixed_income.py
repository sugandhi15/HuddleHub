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

from onyx.core import Date
from onyx.core import GraphNodeDescriptor, ReferenceField, DateField

from ..system.tradable_api import TradableObj, AddByInference, HashStoredAttrs
from ..system.ufo_forward_cash import ForwardCash

__all__ = ["FixedIncome"]


###############################################################################
class FixedIncome(TradableObj):
    """
    Tradable object for a generic fixed income security.
    """
    Asset = ReferenceField(obj_type="Asset")

    # --- last known payment date: this is used to get a new ImpliedName
    #     every time a coupon or principal is paid (needed by the aging
    #     mechanism).
    LastPaymentDate = DateField(default=Date.low_date())

    # -------------------------------------------------------------------------
    def __post_init__(self):
        pass

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def MktVal(self, graph):
        asset = graph(self, "Asset")
        return graph(asset, "Spot") + graph(asset, "AccruedInterest")

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def MktValUSD(self, graph):
        den = graph(graph(self, "Asset"), "Denominated")
        fx = graph("{0:3s}/USD".format(den), "Spot")
        return fx*graph(self, "MktVal")

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def NextTransactionDate(self, graph):
        asset = graph(self, "Asset")
        return min(graph(asset, "NextCouponDate"), graph(asset, "Maturity"))

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def TradeTypes(self, graph):
        mapping = super().TradeTypes
        mapping.update({
            "Coupon": "CouponSecurities",
            "Principal": "PrincipalSecurities",
        })
        return mapping

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def ExpectedTransaction(self, graph):
        nxt_cpn_dt = graph(graph(self, "Asset"), "NextCouponDate")
        ntd = graph(self, "NextTransactionDate")
        if ntd == nxt_cpn_dt:
            return "Coupon"
        else:
            return "Principal"

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def CouponSecurities(self, graph):
        asset = graph(self, "Asset")
        ccy = graph(asset, "Denominated")
        ntd = graph(self, "NextTransactionDate")

        # --- the rolled the fixed income instrument
        rolled = self.clone()
        rolled.LastPaymentDate = ntd

        # --- the payment leg
        cash = ForwardCash(Currency=ccy, PaymentDate=ntd)
        qty = graph(asset, "Coupon") / graph(asset, "CouponFrequency")

        securities = [
            {"Security": AddByInference(rolled, in_memory=True),
             "Quantity": 1.0},
            {"Security": AddByInference(cash, in_memory=True),
             "Quantity": qty},
        ]

        return securities

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def PrincipalSecurities(self, graph):
        asset = graph(self, "Asset")
        ccy = graph(asset, "Denominated")
        ntd = graph(self, "NextTransactionDate")

        # --- the payment leg
        cash = ForwardCash(Currency=ccy, PaymentDate=ntd)

        securities = [
            {"Security": AddByInference(cash, in_memory=True),
             "Quantity": 1.0},
        ]

        return securities

    # -------------------------------------------------------------------------
    @property
    def ImpliedName(self):
        mush = HashStoredAttrs(self, 4)
        return "FI {0:s} {1:4s} {{0:2d}}".format(self.Asset, mush)
