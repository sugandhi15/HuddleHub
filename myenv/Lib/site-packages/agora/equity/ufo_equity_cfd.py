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

from onyx.core import Date, RDate, Structure, GraphNodeDescriptor, GetVal
from onyx.core import FloatField, DateField, ReferenceField

from ..system.tradable_api import AgingTradableObj
from ..system.tradable_api import AddByInference, HashStoredAttrs
from ..system.ufo_forward_cash import ForwardCash
from ..system.ufo_cfd_fixed_leg import CfdFixedLeg
from ..system.ufo_cfd_floating_leg import CfdFloatingLeg
from .ufo_corporate_actions import CASH_ACTIONS

__all__ = ["EquityCFD"]


###############################################################################
class EquityCFD(AgingTradableObj):
    """
    Tradable class that represents a contract for difference on a equity asset.
    """
    Asset = ReferenceField(obj_type="EquityAsset")
    FixedPrice = FloatField(positive=True)

    # --- the settlement currency can differ from the denomination of the asset
    SettlementCcy = ReferenceField(obj_type="Currency")

    # --- fx rate uesd to convert the fixed price (which is expressed in the
    #     currency of the asset) to the settlement currency
    SettlementFx = FloatField()

    # --- last known ex-dividend date: this is used to get a new ImpliedName
    #     every time a dividend is paid (needed by the aging mechanism).
    LastDvdDate = DateField(default=Date.low_date())

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
        """
        Return a Structure with security names as keys and net quantities as
        values.
        """
        asset = graph(self, "Asset")
        ccy = graph(self, "SettlementCcy")

        prc = graph(self, "FixedPrice")
        mul = graph(asset, "Multiplier")
        fx = graph(self, "SettlementFx")

        # --- leaves are created in memory
        floating = AddByInference(CfdFloatingLeg(Asset=asset), True)
        fixed = AddByInference(CfdFixedLeg(Currency=ccy), True)

        return Structure({
            floating.Name: 1.0,
            fixed.Name: -prc*mul*fx,
        })

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
    def GetLastDvdDate(self, graph):
        """
        Return the last known ex-dividend date.
        """
        return graph(graph(self, "Asset"), "GetDividends").back.date

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def NextTransactionDate(self, graph):
        start = graph(self, "LastDvdDate") + RDate("1d")
        actions = graph(graph(self, "Asset"), "NextExDateActions", start)
        return actions[0]["Ex-Date"]

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def TradeTypes(self, graph):
        mapping = super().TradeTypes
        mapping.update({
            "ExDate": "ExDateSecurities",
        })
        return mapping

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def ExpectedTransaction(self, graph):
        return "ExDate"

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def ExDateSecurities(self, graph):
        ccy = graph(graph(self, "Asset"), "Denominated")
        start = graph(self, "LastDvdDate") + RDate("1d")
        ntd = graph(self, "NextTransactionDate")
        actions = graph(graph(self, "Asset"), "NextExDateActions", start)

        # --- the rolled cash-equity
        rolled = self.clone()
        rolled.LastDvdDate = ntd

        securities = [
            {"Security": AddByInference(rolled, in_memory=True),
             "Quantity": 1.0}]

        for action in actions:
            action_type = action["Dividend Type"]
            if action_type in CASH_ACTIONS:
                if ntd != action["Ex-Date"]:
                    raise RuntimeError("WTF ?!?")
                # --- dividend receivable
                pay_date = action["Payable Date"] or Date.high_date()
                pay_qty = action["Dividend Amount"]
                cash = ForwardCash(Currency=ccy, PaymentDate=pay_date)

                securities += [
                    {"Security": AddByInference(cash, in_memory=True),
                     "Quantity": pay_qty}]

            elif action_type == "Rights Issue":
                # --- by default assume that the rights issue is on the same
                #     share class (it's not always the case)
                securities += [
                    {"Security": AddByInference(rolled, in_memory=True),
                     "Quantity": 1.0 - action["Dividend Amount"]}]

            else:
                err_msg = ("Action type for {0:s} is "
                           "{1:s}").format(self.Asset, action_type)
                raise NotImplementedError(err_msg)

        return securities

    # -------------------------------------------------------------------------
    #  this property is used by edit screens
    @GraphNodeDescriptor()
    def AssetSpot(self, graph):
        return graph(graph(self, "Asset"), "Spot")

    # -------------------------------------------------------------------------
    @property
    def ImpliedName(self):
        sym = GetVal(self.Asset, "Symbol")
        code = GetVal(GetVal(self.Asset, "Exchange"), "Code")
        mush = HashStoredAttrs(self, 4)
        return ("EqCFD {0:s} {1:2s} {2:3s} {3:4s} "
                "{{0:2d}}").format(sym, code, self.SettlementCcy, mush)


###############################################################################
class EquityCFDCalc(EquityCFD):
    """
    Calculator class.
    """
    PriceAdjust = FloatField(default=0.0)

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def TradableFactory(self, graph):
        """
        Return a list of tradables objects that replicate the calculator.
        """
        info = {"Asset": graph(self, "Asset"),
                "FixedPrice": graph(self, "FixedPrice"),
                "SettlementCcy": graph(self, "SettlementCcy"),
                "SettlementFx": graph(self, "SettlementFx")}
        return [EquityCFD(**info)]

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def AssetSpot(self, graph):
        return graph(self, "PriceAdjust") + graph(graph(self, "Asset"), "Spot")

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def MktValUSD(self, graph):
        dnpv = 0.0
        for sec, qty in graph(self, "Leaves").items():
            dnpv += qty*graph(sec, "MktValUSD")
        return dnpv + graph(self, "PriceAdjust")

    # -------------------------------------------------------------------------
    def spot_settlement_fx(self):
        ccy1 = GetVal(GetVal(self, "Asset"), "Denominated")
        ccy2 = GetVal(self, "SettlementCcy")
        cross1 = "{0:3s}/USD".format(ccy1)
        cross2 = "{0:3s}/USD".format(ccy2)
        fx_rate = GetVal(cross1, "Spot") / GetVal(cross2, "Spot")

        return fx_rate


# -----------------------------------------------------------------------------
def prepare_for_test():
    from . import ufo_equity_asset
    from ..system import ufo_forward_cash

    ufo_equity_asset.prepare_for_test()
    ufo_forward_cash.prepare_for_test()

    info = {
        "Asset": "EQ NG/ LN",
        "FixedPrice": 910.0,
    }

    securities = [AddByInference(EquityCFD(**info))]

    return [sec.Name for sec in securities]
