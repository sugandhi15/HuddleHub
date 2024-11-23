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

from onyx.core import GraphNodeDescriptor
from onyx.core import ObjNamesByType, UfoBase, StringField, ListField

__all__ = ["Category"]


###############################################################################
class Category(UfoBase):
    """
    Class used to collect instances of classes listed in ObjTypes that match
    the following pattern:
        graph(instance, "Attribute") == graph(self, "TargetValue")
    """
    ObjTypes = ListField()
    Attribute = StringField()
    TargetValue = StringField()

    # -------------------------------------------------------------------------
    def __post_init__(self):
        self.TargetValue = self.TargetValue or self.Name

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def Items(self, graph):
        attr = graph(self, "Attribute")
        value = graph(self, "TargetValue")
        types = graph(self, "ObjTypes")
        names = [
            name for obj_type in types for name in ObjNamesByType(obj_type)]
        return sorted([name for name in names if graph(name, attr) == value])


# -----------------------------------------------------------------------------
def prepare_for_test():
    from onyx.core import AddIfMissing

    AddIfMissing(Category(
        Name="Nth. America", ObjTypes=["EquityAsset"], Attribute="Region"))
    AddIfMissing(Category(
        Name="Nth. Europe", ObjTypes=["EquityAsset"], Attribute="Region"))
    AddIfMissing(Category(
        Name="Cnt. Europe", ObjTypes=["EquityAsset"], Attribute="Region"))

    AddIfMissing(Category(
        Name="USA", ObjTypes=["EquityAsset"], Attribute="Country"))
    AddIfMissing(Category(
        Name="United Kingdom", ObjTypes=["EquityAsset"], Attribute="Country"))
    AddIfMissing(Category(
        Name="Germany", ObjTypes=["EquityAsset"], Attribute="Country"))
