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

from onyx.core import GetVal, GraphNodeDescriptor
from onyx.core import IntField, DateField
from onyx.core import SelectField, BoolField, ReferenceField

from .ufo_commod_nrby import AVERAGING_TYPES, CommodNrby
from ..system.tradable_api import NamedByInference, AddByInference
from ..system.tradable_api import HashStoredAttrs

__all__ = ["CommodForward"]


###############################################################################
class CommodForward(NamedByInference):
    """
    class that represents the floating leg of a commodity forward or futures
    contract that is settled in cash.
    """
    Asset = ReferenceField(obj_type="CommodAsset")
    AvgStartDate = DateField()
    AvgEndDate = DateField()
    AvgType = SelectField(options=AVERAGING_TYPES)
    RollType = IntField(default=0)
    Margined = BoolField(default=False)
    Denominated = ReferenceField(obj_type="Currency")

    # -------------------------------------------------------------------------
    def __post_init__(self):
        # --- set defaults for attributes inherited from Asset
        for attr in ["Denominated"]:
            if getattr(self, attr) is None:
                setattr(self, attr, GetVal(self.Asset, attr))

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def Nearby(self, graph):
        # --- create the nearby object in memory
        info = {
            "Asset": graph(self, "Asset"),
            "StartDate": graph(self, "AvgStartDate"),
            "EndDate": graph(self, "AvgEndDate"),
            "AvgType": graph(self, "AvgType"),
            "RollType": graph(self, "RollType"),
        }
        nrby = AddByInference(CommodNrby(**info), in_memory=True)
        return graph(nrby, "Name")

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def MktVal(self, graph):
        avg_val = graph(graph(self, "Nearby"), "AverageValue")
        if graph(self, "Margined"):
            df = 1.0
        else:
            pd = graph("Database", "PricingDate")
            ed = graph(self, "ExpirationDate")
            ccy = graph(self, "Denominated")
            df = graph(ccy, "DiscountFactor", ed, pd)
        return df*avg_val

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def MktValUSD(self, graph):
        fx = graph("{0:3s}/USD".format(graph(self, "Denominated")), "Spot")
        return fx*graph(self, "MktVal")

    # -------------------------------------------------------------------------
    @property
    def ImpliedName(self):
        mkt = GetVal(self.Asset, "Market")
        sym = GetVal(self.Asset, "Symbol")
        mush = HashStoredAttrs(self, 8)
        return "CmdFWD {0:s} {1:s} {2:8s} {{0:2d}}".format(mkt, sym, mush)
