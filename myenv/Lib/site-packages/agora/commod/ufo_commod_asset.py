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

from onyx.core import Date, Date2LYY, DateOffset
from onyx.core import Curve, HlocvCurve
from onyx.core import AddObj, GetObj, DelObj, ObjNotFound, ObjExists
from onyx.core import ObjDbTransaction
from onyx.core import TsDbGetCurve, TsNotFound
from onyx.core import GetVal, GraphNodeDescriptor
from onyx.core import StringField, SelectField, IntField, FloatField
from onyx.core import SetField, DictField

from ..system.price_curves_api import prices_for_risk
from ..system.ufo_asset import WithAssetAttributes
from .ufo_commod_contract import CommodCnt

from dateutil import relativedelta

import logging

__all__ = ["CommodAsset"]

VALID_UNITS = ["BBL", "MT", "MWh", "Therm", "MMBTU", "Day"]

logger = logging.getLogger(__name__)


###############################################################################
class CommodAsset(WithAssetAttributes):
    """
    This class used to represent commodity assets and to get access to the
    underlying contracts.
    Despite its name, this is not an Asset as it doesn't expose the full Asset
    interface: this because the underlying of a commod tradable is a specific
    commod contract (which is the actual Asset).
    """
    Market = StringField()
    Tickers = DictField()
    Units = SelectField(options=VALID_UNITS)
    TimeSeries = StringField()

    # --- SettDateRule is used to determine the futures settlement date of a
    #     futures contract from its LYY code as follows:
    #         FutSettDate = DateOffset(LYY2Date(DeliveryMonth), SettDateRule)
    SettDateRule = StringField(default="+e")

    # --- OptExpDateRule is used to determine the options expiration date
    #     starting from the settlement date of the futures contract.
    OptExpDateRule = StringField(default="+e")

    CntType = SelectField(options=["CLOSE", "HLOCV"])
    NrbyOffset = IntField()

    ContractSize = FloatField(default=1.0)
    Contracts = SetField(default=set())

    # --- used for attributions
    Country = StringField(default="Commodity")
    Region = StringField(default="Commodity")
    Sector = StringField(default="Commodity")
    Subsector = StringField(default="Commodity")

    # -------------------------------------------------------------------------
    def __post_init__(self):
        super().__post_init__()

        self.Name = "COMMOD {0:s} {1:s}".format(self.Market, self.Symbol)

        # --- calculate the neraby offset based on the settlement date rule and
        #     an arbitrary reference date
        ref = DateOffset(Date.today(), "+0J")
        di = DateOffset(ref, self.SettDateRule, self.HolidayCalendar)
        df = DateOffset(ref, "+e", self.HolidayCalendar)
        rd = relativedelta.relativedelta(df, di)

        self.NrbyOffset = rd.months + 12*rd.years
        if self.NrbyOffset < 0:
            raise RuntimeError("Negative NrbyOffset?!? Check SettDateRule.")

        # --- name of the time-series where historical cash prices are stored
        self.TimeSeries = "CMD-TS {0:s} {1:s}".format(self.Market, self.Symbol)

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor("PropSubGraph")
    def Ticker(self, graph, platform=None):
        if platform is None:
            platform = graph("Settings", "Platform")
        return graph(self, "Tickers")[platform]

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor("Callable")
    def GetContract(self, graph, del_mth):
        """
        Description:
            Return the CommodCnt object for a specific delivery month.
        Inputs:
            del_mth - the delivery month in LYY format (as in Z11)
        Returns:
            A string.
        """
        if del_mth in graph(self, "Contracts"):
            market = graph(self, "Market")
            symbol = graph(self, "Symbol")
            return CommodCnt.get_name(market, symbol, del_mth)
        else:
            raise NameError("Contract {0:s} not found in the set of "
                            "Contracts of {1:s}".format(del_mth, self.Name))

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
                return TsDbGetCurve(name, start, end)
            except TsNotFound:
                return Curve()

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor("Callable")
    def PricesForRisk(self, graph, start, end):
        return prices_for_risk(graph(self, "Name"), start, end, strict=False)

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor("Callable")
    def ActiveByDate(self, graph, date):
        """
        Return the active contract (first nearby) as of a given date.
        """
        cal = graph(self, "HolidayCalendar")
        sdr = graph(self, "SettDateRule")

        rule = "+{0:d}m+0J".format(graph(self, "NrbyOffset"))
        cnt_dt = DateOffset(date, rule)

        if date > DateOffset(cnt_dt, sdr, cal):
            cnt_dt = DateOffset(cnt_dt, "+1m")

        return Date2LYY(cnt_dt)

    # -------------------------------------------------------------------------
    def add_contract(self, del_mth, tickers):
        """
        Description:
            Add a new contract or return the existing one.
        Inputs:
            cnt_mth - the contract month in LYY format
            tickers - a dictionary of tickers
        Returns:
            The contract's name.
        """
        if del_mth in self.Contracts:
            return GetVal(self, "GetContract", del_mth)
        else:
            info = {
                "CommodAsset": self.Name,
                "DeliveryMonth": del_mth,
                "Tickers": tickers,
                "RiskProxy": self.Name,
            }
            cnt_obj = CommodCnt(**info)
            try:
                AddObj(cnt_obj)
            except ObjExists:
                obj = GetObj(cnt_obj.Name)
                if obj != cnt_obj:
                    raise RuntimeError("StoredAttrs of existing contract "
                                       "{0:s} don't match those of parent "
                                       "CommodAsset".format(obj.Name))

            self.Contracts.add(del_mth)

        return cnt_obj.Name

    # -------------------------------------------------------------------------
    def delete(self):
        mkt = self.Market
        sym = self.Symbol
        with ObjDbTransaction("deleting contracts", "SERIALIZABLE"):
            # --- conversion to tuple is needed because the delete method of a
            #     contract removes such contract from the set of contracts of
            #     the asset.
            for cnt in tuple(self.Contracts):
                cnt_name = CommodCnt.get_name(mkt, sym, cnt)
                try:
                    DelObj(cnt_name)
                except ObjNotFound:
                    logger.waring("contract "
                                  "{0:s} not found ?!?".format(cnt_name))


# -----------------------------------------------------------------------------
def prepare_for_test():
    from onyx.core import AddIfMissing
    from ..system import ufo_database
    from ..system import ufo_settings
    from ..system import ufo_holiday_calendar
    from ..system import ufo_currency
    from ..system import ufo_exchange

    ufo_database.prepare_for_test()
    ufo_settings.prepare_for_test()
    ufo_holiday_calendar.prepare_for_test()
    ufo_currency.prepare_for_test()
    ufo_exchange.prepare_for_test()

    eua_info = {
        "Symbol": "EUA",
        "Market": "CO2",
        "Exchange": "IFEN Exchange",
        "Units": "MT",
        "CntType": "CLOSE",
        "SettDateRule": "+e-M+4d-4b-M+4d-4b-M",
        "OptExpDateRule": "-3b",
        "Tickers": {"Bloomberg": "MO1"},
        "Multiplier": 1.0,
        "ContractSize": 1000.0,
    }

    AddIfMissing(CommodAsset(**eua_info))
