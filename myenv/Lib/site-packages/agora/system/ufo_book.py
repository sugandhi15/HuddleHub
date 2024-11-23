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

from onyx.core import Structure
from onyx.core import ObjDbQuery, UfoBase, GraphNodeDescriptor
from onyx.core import ReferenceField, StringField, SelectField

from .trade_api import ChildrenByBook
from .risk_decorators import WithRiskMethods

__all__ = ["Book"]


# --- query to get all assets traded in a given book, skipping all trades that
#     have been subsequently deleted or moved to a different book
ASSETS_BY_BOOK = """
SELECT DISTINCT(Objects.Data->>'Asset') AS Asset FROM (
    SELECT DISTINCT(Objects.Data->>'SecurityTraded') AS SecTraded FROM (
        SELECT Trade As TradeName FROM (
            SELECT Trade, SUM(Qty) AS TotQty
            FROM PosEffects WHERE Book=%s AND UnitType<>'ForwardCash'
            GROUP BY Trade)
        AS Pivot WHERE Pivot.TotQty<>0) AS Trades
    INNER JOIN Objects ON Objects.Name=Trades.TradeName) AS Tradables
INNER JOIN Objects ON Objects.Name=Tradables.SecTraded AND
                      Objects.Data->>'Asset'<>'';
"""


###############################################################################
@WithRiskMethods
class Book(UfoBase):
    """
    Class used to represent a trading book (either internal or external).
    """
    Group = ReferenceField(obj_type="Group")
    Denominated = ReferenceField(obj_type="Currency")
    BookType = SelectField(options=["ProfitCenter", "Counterparty"])
    DisplayName = StringField()
    Account = StringField()

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def Books(self, graph):
        return {self.Name}

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def Children(self, graph):
        pos_dt = graph("Database", "PositionsDate")
        return ChildrenByBook(graph(self, "Name"), pos_dt)

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

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def AttributionParms(self, graph):
        assets = graph(self, "Assets")
        return {
            "Country": {graph(asset, "Country") for asset in assets},
            "Region": {graph(asset, "Region") for asset in assets},
            "Sector": {graph(asset, "Sector") for asset in assets},
            "Subsector": {graph(asset, "Subsector") for asset in assets},
        }

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def Assets(self, graph):
        return {rec.asset for rec in
                ObjDbQuery(ASSETS_BY_BOOK, (self.Name, ), attr="fetchall")}


# -----------------------------------------------------------------------------
def prepare_for_test():
    from onyx.core import AddIfMissing
    from . import ufo_currency
    from . import ufo_currency_cross
    from . import ufo_group

    ufo_currency.prepare_for_test()
    ufo_currency_cross.prepare_for_test()
    groups = ufo_group.prepare_for_test()

    books = [
        AddIfMissing(Book(Name="TEST_BOOK1", Group=groups[0],
                          Denominated="USD", BookType="ProfitCenter")),
        AddIfMissing(Book(Name="TEST_BOOK2", Group=groups[0],
                          Denominated="USD", BookType="ProfitCenter")),
        AddIfMissing(Book(Name="TEST_CPTY1",
                          Denominated="USD", BookType="Counterparty")),
        AddIfMissing(Book(Name="TAXNCOSTS",
                          Denominated="USD", BookType="Counterparty")),
    ]

    return [book.Name for book in books]
