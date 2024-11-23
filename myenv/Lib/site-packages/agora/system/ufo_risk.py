###############################################################################
#
#   Copyright: (c) 2020 Carlo Sbraccia
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

from onyx.core import Date, RDate
from onyx.core import UfoBase, GraphNodeDescriptor, ReferenceField

__all__ = ["Risk"]


###############################################################################
class Risk(UfoBase):
    """
    singleton class used to capture risk parameters.
    """
    RefIndex = ReferenceField(obj_type="EquityIndex")

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def StartDate(self, graph):
        return Date(2008, 6, 1)

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def EndDate(self, graph):
        return graph("Database", "PricingDate") + RDate("-1b")

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def VaRStartDate(self, graph):
        return graph(self, "VaREndDate") + RDate("-5y-0b")

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def VaREndDate(self, graph):
        return graph(self, "EndDate")

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def BetaStartDate(self, graph):
        return graph(self, "BetaEndDate") + RDate("-1y-0b")

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def BetaEndDate(self, graph):
        return graph(self, "EndDate")


# -----------------------------------------------------------------------------
def prepare_for_test():
    from onyx.core import GetVal, AddIfMissing
    from ..system.ufo_shadow_book import ShadowBook
    from ..system import ufo_database
    from ..system import trade_api

    AddIfMissing(Risk(Name="Risk"))

    ufo_database.prepare_for_test()
    trades = trade_api.prepare_for_test()

    book = AddIfMissing(ShadowBook(Name="TestBook", Denominated="GBP"))

    for trade in trades:
        book.Children += GetVal(trade, "Leaves")

    return [book]
