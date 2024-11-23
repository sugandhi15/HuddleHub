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

from onyx.core import Date, Curve, Knot, HlocvCurve
from onyx.core import CalcTerm, DateOffset, Interpolate
from onyx.core import ObjDbTransaction, DelObj, ObjNotFound
from onyx.core import TsDbQuery, TsDbGetCurve, TsNotFound
from onyx.core import GetVal, GraphNodeDescriptor, RetainedFactory
from onyx.core import StringField, DictField, ReferenceField
from onyx.core import CurveField, BoolField

from ..system.ufo_asset import Asset

import numpy as np
import math

__all__ = ["EquityAsset"]

# --- map drop-down values to attributes (used by edit screens)
CRV_CHOICES = {
    "Adjusted": "GetCurve",
    "Marks": "GetMarks",
    "Dividends": "GetDividends",
}


###############################################################################
class EquityAsset(Asset):
    """
    class used to represent an equity asset and to provide access to its
    curve of historical prices and price fixes.
    """
    Tickers = DictField()
    Isin = StringField()
    Sedol = StringField()
    Country = ReferenceField(obj_type="Category")
    Region = ReferenceField(obj_type="Category")
    Sector = ReferenceField(obj_type="Category")
    Subsector = ReferenceField(obj_type="Category")
    TimeSeries = StringField()
    Marks = StringField()
    Dividends = StringField()
    SharesOutCrv = CurveField(default=Curve())
    IsProxySecurity = BoolField(default=False)
    ReferenceIndex = ReferenceField(obj_type="EquityIndex")

    name_fmt = "EQ {0:s} {1:s}"

    # -------------------------------------------------------------------------
    def __post_init__(self):
        super().__post_init__()

        exchange_code = GetVal(self.Exchange, "Code")

        self.Name = self.name_fmt.format(self.Symbol, exchange_code)
        self.Country = self.Country or GetVal(self.Exchange, "Country")
        self.Region = self.Region or GetVal(self.Exchange, "Region")

        # --- name of the time-series that store historical prices,
        #     historical closes (marks) and dividends
        fields = self.Symbol, exchange_code
        self.TimeSeries = "EQ-TS {0:s} {1:s}".format(*fields)
        self.Marks = "EQ-MKS {0:s} {1:s}".format(*fields)
        self.Dividends = "EQ-DIV {0:s} {1:s}".format(*fields)

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor("PropSubGraph")
    def Ticker(self, graph, platform="Bloomberg"):
        """
        If ticker for a given platform is missing, it's understood that we
        should default to the one for Bloomberg.
        """
        try:
            return graph(self, "Tickers")[platform]
        except KeyError:
            return graph(self, "Tickers")["Bloomberg"]

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def UniqueId(self, graph):
        sym = graph(self, "Symbol")
        code = graph(graph(self, "Exchange"), "Code")
        return "{0:s} {1:2s}".format(sym, code)

    # -------------------------------------------------------------------------
    @RetainedFactory()
    def Spot(self, graph):
        """
        Return the official close value as of MktDataDate (or the most recent
        close if ForceStrict is False) in the Denominated currency.
        """
        return graph(graph(self, "Marks"), "Price")*graph(self, "Multiplier")

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def Last(self, graph):
        """
        Return the knot with the most recent close value (irrespective of
        MktDataDate) in the Denominated currency.
        """
        marks = graph(self, "Marks")
        date, value = graph(marks, "LastKnot", date=Date.high_date())
        return Knot(date, value*graph(self, "Multiplier"))

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor("PropSubGraph")
    def GetCurve(self, graph, start=None, end=None, field=None, adj=True):
        name = graph(self, "TimeSeries")
        try:
            crv = TsDbGetCurve(name, start, end, "HLOCV", field)
        except TsNotFound:
            return HlocvCurve() if field is None else Curve()

        if adj:
            return graph(graph(self, "Dividends"), "AdjustCurve")(crv)
        else:
            return crv

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor("PropSubGraph")
    def GetMarks(self, graph, start=None, end=None):
        mks = graph(self, "Marks")
        return graph(mks, "PrcFixCurve", start=start, end=end)

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor("PropSubGraph")
    def GetDividends(self, graph, start=None, end=None):
        dvds = graph(self, "Dividends")
        return graph(dvds, "DvdCurve", start=start, end=end)

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def DividendForecast(self, graph):
        """
        Include dividends paid within the last 12 months and pick the most
        recent as forcasted value.
        """
        mdd = graph("Database", "MktDataDate")
        div = graph(self, "GetDividends").crop(DateOffset(mdd, "-12m"))
        val = Interpolate(div, mdd, method="Step")

        rules = ["+1y-0b", "+2y-0b", "+3y-0b"]
        cal = graph(self, "HolidayCalendar")
        dts = [[DateOffset(d, r, cal) for r in rules] for d in div.dates]
        dts = {item for sublist in dts for item in sublist}
        vls = val*np.ones(len(dts))

        return Curve(dts, vls)

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor("Callable")
    def DividendYield(self, graph, start, end):
        """
        DividendYield, calculated by including all dividends that are expected
        to be paid between start and end date and annualizing with continuous
        compounding.
        """
        if start <= end:
            return 0.0

        fcast = graph(self, "DividendForecast").crop_values(start, end)
        tot_dvd = fcast.sum()*graph(self, "Multiplier")
        spot = graph(self, "Spot")

        return math.log(tot_dvd/spot + 1.0) / CalcTerm(start, end)

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor("PropSubGraph")
    def NextExDateActions(self, graph, start=None):
        if start is None:
            start = graph("Database", "PositionsDate")
        return graph(graph(self, "Dividends"), "NextExDateActions", start)

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def SharesOutstanding(self, graph):
        crv = graph(self, "SharesOutCrv")
        if len(crv):
            mdd = graph("Database", "MktDataDate")
            return Interpolate(crv, mdd, method="Step")
        else:
            return None

    # -------------------------------------------------------------------------
    #  Auxiliary attributes/methods used by the edit screen

    @RetainedFactory()
    def Selection(self, graph):
        return "Adjusted"

    @GraphNodeDescriptor()
    def DisplayCurve(self, graph):
        return graph(self, CRV_CHOICES[graph(self, "Selection")])

    # -------------------------------------------------------------------------
    def delete(self):
        # --- delete timeseries
        TsDbQuery("DELETE FROM HlocvCurves WHERE "
                  "Name = %s", parms=(self.TimeSeries,))

        # --- delete price fixes
        with ObjDbTransaction("cleanup", "SERIALIZABLE"):
            for obj_name in (self.Marks, self.Dividends):
                try:
                    DelObj(obj_name)
                except ObjNotFound:
                    # --- this is fine, ignore exception
                    continue


# -----------------------------------------------------------------------------
def prepare_for_test():
    from onyx.core import AddIfMissing, EvalBlock
    from ..system.ufo_price_fix import PriceFix
    from ..system import ufo_currency
    from ..system import ufo_database
    from ..system import ufo_holiday_calendar
    from ..system import ufo_exchange
    from ..system import ufo_price_fix

    ufo_database.prepare_for_test()
    ufo_holiday_calendar.prepare_for_test()
    ufo_currency.prepare_for_test()
    ufo_exchange.prepare_for_test()
    ufo_price_fix.prepare_for_test()

    ibm_info = {
        "Symbol": "IBM",
        "Exchange": "XNYS Exchange",
        "Tickers": {"Bloomberg": "IBM"},
        "Multiplier": 1.00,
    }

    sec = AddIfMissing(EquityAsset(**ibm_info))
    prc_fix = AddIfMissing(PriceFix(Name=GetVal(sec, "Marks")))

    with EvalBlock() as eb:
        eb.change_value("Database", "ArchivedOverwritable", True)
        prc_fix.set_dated("Price", Date.today(), 100.0)

    ng_info = {
        "Symbol": "NG/",
        "Exchange": "XLON Exchange",
        "Tickers": {
            "Bloomberg": "NG/",
            "Google": "NG",
            "Yahoo": "NG",
            "WSJ": "NG."
        },
        "Multiplier": 0.01,
    }

    sec = AddIfMissing(EquityAsset(**ng_info))
    prc_fix = AddIfMissing(PriceFix(Name=GetVal(sec, "Marks")))

    with EvalBlock() as eb:
        eb.change_value("Database", "ArchivedOverwritable", True)
        prc_fix.set_dated("Price", Date.today(), 900.0)
