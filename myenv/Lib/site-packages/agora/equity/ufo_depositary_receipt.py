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

from onyx.core import ReferenceField, FloatField, GetVal, GraphNodeDescriptor
from onyx.core import DiscardInheritedAttribute, InheritAsProperty
from onyx.core import RetainedFactory

from .ufo_equity_asset import EquityAsset

__all__ = ["DepositaryReceipt"]

DISCARD = ["RiskProxy"]
REPLACE = ["Country", "Region", "Sector", "Subsector"]


###############################################################################
@InheritAsProperty(REPLACE, "Parent")
@DiscardInheritedAttribute(DISCARD)
class DepositaryReceipt(EquityAsset):
    """
    class used to represent a depositary receipt (GDR, ADR, etc).
    """
    # --- a reference to the local listing for this company
    Parent = ReferenceField(obj_type="EquityAsset")
    # --- one depositary receipt corresponds to these many shares in the
    #     local listing
    Conversion = FloatField(default=1.0)

    # -------------------------------------------------------------------------
    def __post_init__(self):
        # --- here we don't want to call EquityAsset's __post_init__ method
        #     but rather that of its super-class: this to avoid trying to set
        #     properties that have been inherited as properties.
        super(EquityAsset, self).__post_init__()

        exchange_code = GetVal(self.Exchange, "Code")

        self.Name = self.name_fmt.format(self.Symbol, exchange_code)

        # --- name of the time-series that store historical adjusted prices,
        #     historical closes (marks) and dividends
        fields = self.Symbol, exchange_code
        self.TimeSeries = "EQ-TS {0:s} {1:s}".format(*fields)
        self.Marks = "EQ-MKS {0:s} {1:s}".format(*fields)
        self.Dividends = "EQ-DIV {0:s} {1:s}".format(*fields)

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def RiskProxy(self, graph):
        return graph(self, "Parent")

    # -------------------------------------------------------------------------
    @RetainedFactory()
    def Spot(self, graph):
        """
        Return the official close value as of MktDataDate (or the most recent
        close if ForceStrict is False) in the Denominated currency.
        """
        fx = graph(self, "DenominatedToLocal")
        return self.spot_local_ccy() * graph(self, "Multiplier") / fx

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def DenominatedToLocal(self, graph):
        parent = graph(self, "Parent")
        den_to_usd = "{0:3s}/USD".format(GetVal(self, "Denominated"))
        loc_to_usd = "{0:3s}/USD".format(GetVal(parent, "Denominated"))
        return graph(den_to_usd, "Spot") / graph(loc_to_usd, "Spot")

    # -------------------------------------------------------------------------
    def spot_local_ccy(self):
        """
        Return (off-graph) spot of the depositary receipt converted to the
        currency of the local listing.
        This gymnastic is needed to reflect the proper FX risk.
        """
        spot = GetVal(GetVal(self, "Marks"), "Price")
        return spot * GetVal(self, "DenominatedToLocal")
