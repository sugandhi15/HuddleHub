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

from onyx.core import RDate, Structure, DateOffset
from onyx.core import GraphNodeDescriptor, GetVal
from onyx.core import IntField, FloatField, DateField
from onyx.core import StringField, SelectField, ReferenceField

from ..system.tradable_api import AgingTradableObj, AddByInference
from ..system.tradable_api import HashStoredAttrs
from ..system.ufo_forward_cash import ForwardCash
from .ufo_commod_forward import CommodForward
from .ufo_commod_nrby import AVERAGING_TYPES


###############################################################################
class CommodSwap(AgingTradableObj):
    """
    Tradable class that represents a commodity swap contract.
    """
    Asset = ReferenceField(obj_type="CommodAsset")
    AvgStartDate = DateField()
    AvgEndDate = DateField()
    AvgType = SelectField(options=AVERAGING_TYPES)
    RollType = IntField(default=0)
    Quantity = IntField()
    FixedPrice = FloatField()
    Denominated = ReferenceField(obj_type="Currency", default="USD")
    PaymentRule = StringField(default="+5b")

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor("Property")
    def Leaves(self, graph):
        asset = graph(self, "Asset")
        qty = graph(self, "Quantity")
        price = graph(self, "FixedPrice")
        sd = graph(self, "AvgStartDate")
        ed = graph(self, "AvgEndDate")
        one_month = RDate("+1m")
        den = graph(self, "Denominated")
        payment_rule = graph(self, "PaymentDateRule")
        cal = graph(asset, "HolidayCalendar")
        avg_type = graph(self, "AvgType")
        roll_type = graph(self, "RollType")

        # --- settlement on a monthly basis
        leaves = Structure()
        while sd < ed:
            mth_ed = min(ed, DateOffset(sd, "+e"))
            fwd_info = {
                "Asset": asset,
                "AvgStartDate": sd,
                "AvgEndDate": mth_ed,
                "AvgType": avg_type,
                "RollType": roll_type,
            }
            sec = AddByInference(CommodForward(**fwd_info), True)
            leaves[sec.Name] = qty

            # --- cash leg
            cash_info = {
                "Currency": den,
                "PaymentDate": DateOffset(mth_ed, payment_rule, cal),
            }
            sec = AddByInference(ForwardCash(**cash_info), True)
            leaves[sec.Name] = -qty*price

            sd += one_month

        return leaves

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor("Property")
    def UndiscountedValue(self, graph):
        fx = graph("{0:3s}/USD".format(graph(self, "Denominated")), "Spot")
        return graph(self, "UndiscountedValueUSD") / fx

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor("Property")
    def MktVal(self, graph):
        fx = graph("{0:3s}/USD".format(graph(self, "Denominated")), "Spot")
        return graph(self, "MktValUSD") / fx

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor("Property")
    def UndiscountedValueUSD(self, graph):
        val = 0.0
        for sec, qty in graph(self, "Leaves").items():
            val += qty*graph(sec, "UndiscountedValueUSD")
        return val

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor("Property")
    def MktValUSD(self, graph):
        val = 0.0
        for sec, qty in graph(self, "Leaves").items():
            val += qty*graph(sec, "MktValUSD")
        return val

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor("Property")
    def ExpirationDate(self, graph):
        securities = graph(self, "Leaves").keys()
        return max([GetVal(sec, "ExpirationDate") for sec in securities])

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor("Property")
    def NextTransactionDate(self, graph):
        securities = graph(self, "Leaves").keys()
        return max([GetVal(sec, "NextTransactionDate") for sec in securities])

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor("Property")
    def NextTransactionEvent(self, graph):
        return "Settlement"

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor("Property")
    def NextTransactionSecurity(self, graph):
        return None

    # -------------------------------------------------------------------------
    @property
    def ImpliedName(self, graph):
        mkt = GetVal(self.Asset, "Market")
        sym = GetVal(self.Asset, "Symbol")
        return ("CmdSWP {0:s} {1:s} {2:8s} "
                "{0:2d").format(mkt, sym, HashStoredAttrs(self, 8))
