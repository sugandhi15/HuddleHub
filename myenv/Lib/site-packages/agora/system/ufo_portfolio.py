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

from onyx.core import Structure, GraphNodeDescriptor, UfoBase
from onyx.core import ReferenceField,  StructureField, StringField

from .risk_decorators import WithRiskMethods

__all__ = ["Portfolio"]


###############################################################################
@WithRiskMethods
class Portfolio(UfoBase):
    """
    Class used to represent a Portfolio (i.e. a collection of books or other
    sub-portfolios).
    """
    Denominated = ReferenceField(obj_type="Currency")
    DisplayName = StringField()
    Children = StructureField()

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def Books(self, graph):
        """
        Return the list of of all books that are children of this portfolio.
        """
        books = set()
        for child in graph(self, "Children"):
            books.update(graph(child, "Books"))
        return books

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def Leaves(self, graph):
        leaves = Structure()
        for child, qty in graph(self, "Children").items():
            leaves += qty*graph(child, "Leaves")
        return leaves

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def MktValUSD(self, graph):
        mtm = 0.0
        for leaf, qty in graph(self, "Leaves").items():
            mtm += qty*graph(leaf, "MktValUSD")
        return mtm

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def MktVal(self, graph):
        denominated = graph(self, "Denominated")
        spot_fx = graph("{0:3s}/USD".format(denominated), "Spot")
        return graph(self, "MktValUSD") / spot_fx


# -----------------------------------------------------------------------------
def prepare_for_test():
    from onyx.core import AddIfMissing
    from . import ufo_currency
    from . import ufo_currency_cross

    ufo_currency.prepare_for_test()
    ufo_currency_cross.prepare_for_test()

    ports = [
        AddIfMissing(
            Portfolio(
                Name="TEST_PORTFOLIO", Denominated="USD",
                Children=Structure({"BOOK1": 1.0, "BOOK2": 1.0}))),
    ]

    return [port.Name for port in ports]
