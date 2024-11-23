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

from onyx.core import GetVal, UfoBase, GraphNodeDescriptor
from onyx.core import FloatField, ReferenceField, StringField

from .price_curves_api import prices_for_risk

import abc

__all__ = ["WithAssetAttributes", "Asset"]


###############################################################################
class WithAssetAttributes(UfoBase):
    """
    This class is used to expose stored attributes that are common to all
    assets or to classes that act as parents for assets (such as CommodAsset).
    """
    Symbol = StringField()
    Exchange = ReferenceField(obj_type="Exchange")
    Denominated = ReferenceField(obj_type="Currency")
    HolidayCalendar = ReferenceField(obj_type="HolidayCalendar")
    Multiplier = FloatField(default=1.0)
    Description = StringField(default="")
    RiskProxy = ReferenceField(obj_type="WithAssetAttributes")
    VolMatrix = StringField()
    VolModel = StringField()

    # -------------------------------------------------------------------------
    def __post_init__(self):
        # --- set defaults for attributes inherited from Exchange
        for attr in {"Denominated", "HolidayCalendar", "Multiplier"}:
            if getattr(self, attr) is None:
                setattr(self, attr, GetVal(self.Exchange, attr))


###############################################################################
class Asset(WithAssetAttributes):
    """
    Base class used to provide a generic interface to all assets.
    """
    # -------------------------------------------------------------------------
    @abc.abstractmethod
    def UniqueId(self, graph):
        raise NotImplementedError()

    # -------------------------------------------------------------------------
    # this should always be implemented as a Settable Property using the
    # RetainedFactory
    @abc.abstractmethod
    def Spot(self, graph):
        raise NotImplementedError()

    # -------------------------------------------------------------------------
    @abc.abstractmethod
    def GetCurve(self, graph, start, end, field):
        raise NotImplementedError()

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def SpotUSD(self, graph):
        cross = "{0:3s}/USD".format(graph(self, "Denominated"))
        return graph(self, "Spot")*graph(cross, "Spot")

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor("Callable")
    def PricesForRisk(self, graph, start, end):
        return prices_for_risk(graph(self, "Name"), start, end, strict=False)
