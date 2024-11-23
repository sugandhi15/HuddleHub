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

from onyx.core import Structure, GraphNodeDescriptor, ObjDbQuery
from onyx.core import DiscardInheritedAttribute

from .ufo_portfolio import Portfolio
from .risk_decorators import WithRiskMethods

import json

__all__ = ["Group"]

GET_ITEMS = "SELECT Name FROM Objects WHERE ObjType=%s AND Data @> %s;"


###############################################################################
@WithRiskMethods
@DiscardInheritedAttribute(["Children"])
class Group(Portfolio):
    """
    Class used to represent a trading group. Group is a subclass of portfolio
    and its children are all the books that are assigned to the group itself.
    """
    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def Children(self, graph):
        kids = {book: 1 for book in graph(self, "Books")}
        return Structure(kids)

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def Books(self, graph):
        parms = ("Book", json.dumps({"Group": graph(self, "Name")}))
        results = ObjDbQuery(GET_ITEMS, parms, attr="fetchall")
        return sorted([res.name for res in results])

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def Traders(self, graph):
        parms = ("Trader", json.dumps({"Group": graph(self, "Name")}))
        results = ObjDbQuery(GET_ITEMS, parms, attr="fetchall")
        return sorted([res.name for res in results])


# -----------------------------------------------------------------------------
def prepare_for_test():
    from onyx.core import AddIfMissing

    groups = [
        AddIfMissing(Group(Name="TEST_GROUP"))
    ]

    return [group.Name for group in groups]
