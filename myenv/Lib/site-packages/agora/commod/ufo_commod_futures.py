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

from onyx.core import Structure, DateOffset
from onyx.core import GraphNodeDescriptor, GetVal
from onyx.core import FloatField, StringField, ReferenceField

from .ufo_commod_forward import CommodForward
from ..system.tradable_api import AgingTradableObj, AddByInference
from ..system.tradable_api import HashStoredAttrs
from ..system.ufo_forward_cash import ForwardCash

__all__ = ["CommodFutures"]


###############################################################################
class CommodFutures(AgingTradableObj):
    """
    Tradable class that represents a commodity futures contract with physical
    delivery.
    """
    Asset = ReferenceField(obj_type="CommodCnt")
    FixedPrice = FloatField(positive=True)

    # --- the settlement currency can differ from the denomination of the asset
    SettlementCcy = ReferenceField(obj_type="Currency")

    # --- fx rate uesd to convert the fixed price (which is expressed in the
    #     currency of the asset) to the settlement currency
    SettlementFx = FloatField()

    # --- the date rule for the cash payment, defaults to 2 biz days after
    #     settlement
    PaymentDateRule = StringField("+2b")

    # -------------------------------------------------------------------------
    def __post_init__(self):
        asset_ccy = GetVal(self.Asset, "Denominated")

        self.SettlementCcy = self.SettlementCcy or asset_ccy

        if self.SettlementFx is None:
            # --- default to spot
            if asset_ccy == self.SettlementCcy:
                fx = 1.0
            else:
                asset_cross = "{0:3s}/USD".format(asset_ccy)
                sett_cross = "{0:3s}/USD".format(self.SettlementCcy)
                fx = GetVal(asset_cross, "Spot") / GetVal(sett_cross, "Spot")

            self.SettlementFx = fx

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def Leaves(self, graph):
        asset = graph(self, "Asset")
        mul = graph(asset, "Multiplier")
        lot = graph(asset, "ContractSize")
        cal = graph(asset, "HolidayCalendar")

        sett_fx = graph(self, "SettlementFx")
        sett_date = graph(asset, "FutSettDate")
        pay_rule = graph(self, "PaymentDateRule")

        fwd_info = {
            "Asset": graph(asset, "CommodAsset"),
            "AvgStartDate": sett_date,
            "AvgEndDate": sett_date,
            "AvgType": "LAST",
            "Margined": True,
        }
        cash_info = {
            "Currency": graph(self, "SettlementCcy"),
            "PaymentDate": DateOffset(sett_date, pay_rule, cal),
        }

        fwd_sec = AddByInference(CommodForward(**fwd_info), True)
        cash_sec = AddByInference(ForwardCash(**cash_info), True)

        # --- use list-based constructor to enforce key ordering
        return Structure([
            (fwd_sec.Name,  lot),
            (cash_sec.Name, -lot*mul*sett_fx*graph(self, "FixedPrice"))
        ])

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def MktValUSD(self, graph):
        mtm = 0.0
        for sec, qty in graph(self, "Leaves").items():
            mtm += qty*graph(sec, "MktValUSD")
        return mtm

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def MktVal(self, graph):
        sett_ccy = graph(self, "SettlementCcy")
        spot_fx = graph("{0:3s}/USD".format(sett_ccy), "Spot")
        return graph(self, "MktValUSD") / spot_fx

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def ExpirationDate(self, graph):
        asset = graph(self, "Asset")
        cnt = graph(asset, "GetContract", graph(self, "DeliveryMonth"))
        return graph(cnt, "FutSettDate")

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def NextTransactionDate(self, graph):
        return graph(self, "ExpirationDate")

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def TradeTypes(self, graph):
        mapping = super().TradeTypes
        mapping.update({
            "Delivery": "DeliverySecurities",
        })
        return mapping

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def ExpectedTransaction(self, graph):
        return "Delivery"

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def DeliverySecurities(self, graph):
        """
        Delivery of physical commodity: here we only include the cash leg
        """
        asset = graph(self, "Asset")
        sett_ccy = graph(self, "SettlementCcy")
        sett_date = graph(asset, "FutSettDate")
        pay_rule = graph(self, "PaymentDateRule")
        cal = graph(asset, "HolidayCalendar")

        mul = graph(asset, "Multiplier")
        lot = graph(asset, "ContractSize")

        cash = ForwardCash(Currency=sett_ccy,
                           PaymentDate=DateOffset(sett_date, pay_rule, cal))

        return [
            {"Security": AddByInference(cash, in_memory=True),
             "Quantity": -mul*lot*graph(self, "FixedPrice")},
        ]

    # -------------------------------------------------------------------------
    #  this property is used by edit screens
    @GraphNodeDescriptor()
    def AssetSpot(self, graph):
        return graph(graph(self, "Asset"), "Spot")

    # -------------------------------------------------------------------------
    @property
    def ImpliedName(self):
        mkt = GetVal(self.Asset, "Market")
        sym = GetVal(self.Asset, "Symbol")
        cnt = GetVal(self.Asset, "DeliveryMonth")
        mush = HashStoredAttrs(self, 3)
        return ("CmdFUT {0:s} {1:s} {2:3s}"
                " {3:3s} {{0:2d}}").format(mkt, sym, cnt, mush)


# -----------------------------------------------------------------------------
def prepare_for_test():
    from . import ufo_commod_contract
    from ..system import ufo_forward_cash

    cnt, prc = ufo_commod_contract.prepare_for_test()[0]
    ufo_forward_cash.prepare_for_test()

    info = {
        "Asset": cnt,
        "FixedPrice": prc - 0.1,
    }

    securities = [AddByInference(CommodFutures(**info))]

    return [sec.Name for sec in securities]
