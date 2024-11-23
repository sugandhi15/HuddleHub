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

from onyx.core import GetVal, GraphNodeDescriptor, ReferenceField

from .tradable_api import NamedByInference

__all__ = ["CfdFloatingLeg"]


###############################################################################
class CfdFloatingLeg(NamedByInference):
    """
    Floating leg of the CFD.
    """
    Asset = ReferenceField(obj_type="Asset")

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def MktVal(self, graph):
        return graph(graph(self, "Asset"), "Spot")

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def MktValUSD(self, graph):
        den = graph(graph(self, "Asset"), "Denominated")
        fx = graph("{0:3s}/USD".format(den), "Spot")
        return fx*graph(self, "MktVal")

    # -------------------------------------------------------------------------
    @property
    def ImpliedName(self):
        uid = GetVal(self.Asset, "UniqueId")
        return "CfdFloating {0:s}".format(uid)
