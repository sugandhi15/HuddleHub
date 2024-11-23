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

from onyx.core import Date, LYY2Date, Curve, HlocvCurve, Knot, DateOffset
from onyx.core import DelObj, UpdateObj, ObjNotFound
from onyx.core import TsDbGetCurve, TsDbQuery, TsNotFound
from onyx.core import GetVal, SetVal, GraphNodeDescriptor
from onyx.core import StringField, DictField, ReferenceField
from onyx.core import InheritAsProperty, RetainedFactory

from ..system.ufo_asset import Asset

__all__ = ["CommodCnt"]

# --- replace all base class stored attributes with pointers to CommodAsset,
#     with the exception of RiskProxy
REPLACE = Asset._json_fields.difference({"RiskProxy"})
# --- add a few CommodAsset-specific stored attributes
REPLACE = REPLACE.union({
    "Market", "CntType", "ContractSize", "SettDateRule", "OptExpDateRule",
    "Country", "Region", "Sector", "Subsector"
})


###############################################################################
@InheritAsProperty(REPLACE, "CommodAsset")
class CommodCnt(Asset):
    """
    This class used to access commod contract information and the relative
    timeseries.
    """
    # --- this is the parent object that babysits all contracts on the same
    #     commodity
    CommodAsset = ReferenceField(obj_type="CommodAsset")
    Tickers = DictField()

    # --- DeliveryMonth is the LYY code for the contract
    DeliveryMonth = StringField()

    Marks = StringField()
    TimeSeries = StringField()

    # -------------------------------------------------------------------------
    def __post_init__(self):
        mkt = GetVal(self.CommodAsset, "Market")
        sym = GetVal(self.CommodAsset, "Symbol")
        args = mkt, sym, self.DeliveryMonth

        self.Name = self.get_name(*args)
        self.Marks = "CNT-MKS {0:s} {1:s} {2:3s}".format(*args)
        self.TimeSeries = "CNT-TS {0:s} {1:s} {2:3s}".format(*args)

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor("PropSubGraph")
    def Ticker(self, graph, platform=None):
        if platform is None:
            platform = graph("Settings", "Platform")
        return graph(self, "Tickers")[platform]

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def UniqueId(self, graph):
        mkt = graph(self, "Market")
        sym = graph(self, "Symbol")
        mth = graph(self, "DeliveryMonth")
        return "{0:s} {1:s} {2:3s}".format(mkt, sym, mth)

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def FutSettDate(self, graph):
        rule = graph(self, "SettDateRule")
        cal = graph(self, "HolidayCalendar")
        mth = graph(self, "DeliveryMonth")
        return DateOffset(LYY2Date(mth), rule, cal)

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def VolEndDate(self, graph):
        return graph(self, "FutSettDate")

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def OptExpDate(self, graph):
        rule = graph(self, "OptExpDateRule")
        cal = graph(self, "HolidayCalendar")
        return DateOffset(graph(self, "FutSettDate"), rule, cal)

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
    def GetCurve(self, graph, start=None, end=None, field=None):
        name = graph(self, "TimeSeries")
        if graph(self, "CntType") == "HLOCV":
            try:
                return TsDbGetCurve(name, start, end, "HLOCV", field)
            except TsNotFound:
                return HlocvCurve() if field is None else Curve()
        else:
            try:
                return TsDbGetCurve(name, start, end, "CRV", field)
            except TsNotFound:
                return Curve()

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor("PropSubGraph")
    def GetMarks(self, graph, start=None, end=None):
        return graph(graph(self, "Marks"), "PrcFixCurve", start, end)

    # -------------------------------------------------------------------------
    def delete(self):
        # --- delete time-series from TsDb
        if self.CntType == "HLOCV":
            query = "DELETE FROM HlocvCurves WHERE Name=%s"
        else:
            query = "DELETE FROM Curves WHERE Name=%s"

        # --- delete timeseries
        TsDbQuery(query, parms=(self.TimeSeries,))

        # --- delete price fixes
        try:
            DelObj(self.Marks)
        except ObjNotFound:
            pass

        # --- remove from set of contracts for the CommodAsset object
        cnts = GetVal(self.CommodAsset, "Contracts")
        cnts.discard(self.DeliveryMonth)

        SetVal(self.CommodAsset, "Contracts", cnts)
        UpdateObj(self.CommodAsset)

    # -------------------------------------------------------------------------
    @classmethod
    def get_name(cls, market, symbol, del_mth):
        """
        Generate contract's name from Market, Symbol, and DeliveryMonth
        """
        return "CNT {0:s} {1:s} {2:3s}".format(market, symbol, del_mth)


# -----------------------------------------------------------------------------
def prepare_for_test():
    from onyx.core import Date, RDate, Date2LYY
    from onyx.core import GetObj, AddIfMissing, EvalBlock
    from . import ufo_commod_asset
    from ..system import ufo_price_fix

    ufo_commod_asset.prepare_for_test()
    ufo_price_fix.prepare_for_test()

    mth = Date2LYY(Date.today() + RDate("+E"))
    bbg_ticker = "MO{0:s}{1:s}".format(mth[0], mth[-1])

    commod = GetObj("COMMOD CO2 EUA")
    cnt = commod.add_contract(mth,  {"Bloomberg": bbg_ticker})
    prc = 7.0

    prc_fix = AddIfMissing(ufo_price_fix.PriceFix(Name=GetVal(cnt, "Marks")))
    with EvalBlock() as eb:
        eb.change_value("Database", "ArchivedOverwritable", True)
        prc_fix.set_dated("Price", Date.today(), prc)

    return [(cnt, prc)]
