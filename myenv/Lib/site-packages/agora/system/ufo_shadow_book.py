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

from onyx.core import b36encode, Structure
from onyx.core import UfoBase, GraphNodeDescriptor
from onyx.core import StructureField, ReferenceField

from .risk_decorators import WithRiskMethods

import uuid

__all__ = ["ShadowBook"]


###############################################################################
@WithRiskMethods
class ShadowBook(UfoBase):
    """
    Class used to represent a shadow book (i.e. a book whose children are not
    generated from trades and positions, but set manually).
    """
    Denominated = ReferenceField(obj_type="Currency")
    Children = StructureField(default=Structure())

    # -------------------------------------------------------------------------
    def __post_init__(self):
        self.Name = self.Name or "SB {0:s}".format(ShadowBook.random_name(16))

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
    @classmethod
    def random_name(cls, nchar=8):
        random = b36encode(bytes(str(uuid.uuid4()).replace("-", ""), "utf-8"))
        return random[:nchar]
