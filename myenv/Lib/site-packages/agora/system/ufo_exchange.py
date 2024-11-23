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

from onyx.core import UfoBase, GraphNodeDescriptor, GetVal
from onyx.core import FloatField, ReferenceField, StringField, DictField

__all__ = ["Exchange"]


###############################################################################
class Exchange(UfoBase):
    """
    Class used to represent an exchange or trading venue.
    """
    IsoCode = StringField()
    Denominated = ReferenceField(obj_type="Currency")
    Multiplier = FloatField(default=1.0)
    HolidayCalendar = ReferenceField(obj_type="HolidayCalendar")
    Country = ReferenceField(obj_type="Category")
    Region = ReferenceField(obj_type="Category")
    FullName = StringField(default="")
    Codes = DictField()
    TimeZone = StringField()
    MarketSession = StringField()

    # -------------------------------------------------------------------------
    def __post_init__(self):
        if self.IsoCode is None:
            raise ValueError("IsoCode not set")
        self.Name = self.Name or "{0:s} Exchange".format(self.IsoCode)
        if self.HolidayCalendar is None:
            self.HolidayCalendar = GetVal(self.Denominated, "HolidayCalendar")

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor("PropSubGraph")
    def Code(self, graph, platform="Bloomberg"):
        return graph(self, "Codes")[platform]


# -----------------------------------------------------------------------------
def prepare_for_test():
    from onyx.core import AddIfMissing
    from . import ufo_currency
    from . import ufo_database
    from . import ufo_holiday_calendar
    from . import ufo_category

    ufo_database.prepare_for_test()
    ufo_holiday_calendar.prepare_for_test()
    ufo_currency.prepare_for_test()
    ufo_category.prepare_for_test()

    exchanges = [
        {
            "IsoCode": "XNYS",
            "Denominated": "USD",
            "Country": "USA",
            "Region": "Nth. America",
            "FullName": "New York Stock Exchange",
            "Codes": {
                "Bloomberg": "US",
                "Google": "NYSE",
                "Yahoo": "",
                "WSJ": "US",
            },
        },
        {
            "IsoCode": "XLON",
            "Denominated": "GBP",
            "Country": "United Kingdom",
            "Region": "Nth. Europe",
            "FullName": "London Stock Exchange",
            "Codes": {
                "Bloomberg": "LN",
                "Google": "LON",
                "Yahoo": "L",
                "WSJ": "UK",
            },
        },
        {
            "IsoCode": "XEUR",
            "Denominated": "EUR",
            "Country": "Germany",
            "Region": "Cnt. Europe",
            "FullName": "Eurex",
            "Codes": {"Bloomberg": "EUX"},
        },
        {
            "IsoCode": "IFEN",
            "Denominated": "EUR",
            "Country": "United Kingdom",
            "Region": "Nth. Europe",
            "FullName": "ICE Futures Europe",
            "Codes": {"Bloomberg": "ICE"},
        }
    ]

    for info in exchanges:
        AddIfMissing(Exchange(**info))
