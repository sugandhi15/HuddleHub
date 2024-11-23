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

from onyx.core import Curve, HlocvCurve, RDate, Interpolate
from onyx.core import AddObj, GetObj, DelObj
from onyx.core import ObjExists, ObjNotFound, ObjDbTransaction
from onyx.core import TsDbGetCurve, TsNotFound
from onyx.core import RetainedFactory, GetVal, GraphNodeDescriptor
from onyx.core import (
    FloatField, DictField, SetField, StringField, ReferenceField)

from ..system.ufo_asset import Asset
from .ufo_equity_index_contract import EquityIndexCnt

__all__ = ["EquityIndex", "MissingContract"]


###############################################################################
class MissingContract(Exception):
    pass


###############################################################################
class EquityIndex(Asset):
    """
    class used to represent an equity index and to provide access to futures
    contracts and options that settle on that index.
    """
    Tickers = DictField()
    ContractSize = FloatField()
    Country = ReferenceField(obj_type="Category")
    Region = ReferenceField(obj_type="Category")
    Sector = StringField(default="Equity Index")
    Subsector = StringField(default="Equity Index")
    TimeSeries = StringField()

    # --- settlement date rule for the underlying futures contracts
    SettDateRule = StringField()

    # --- date rule for the expiry of options
    OptExpDateRule = StringField()

    # --- the set of futures contracts expressed in LYY format
    Contracts = SetField(default=set())

    # -------------------------------------------------------------------------
    def __post_init__(self):
        super().__post_init__()

        self.Name = "EQ-IDX {0:s}".format(self.Symbol)
        self.Country = self.Country or GetVal(self.Exchange, "Country")
        self.Region = self.Region or GetVal(self.Exchange, "Region")

        # --- name of the time-series where historical cash prices are stored
        self.TimeSeries = "IDX-TS {0:s}".format(self.Symbol)

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
        return graph(self, "Symbol")

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor("Callable")
    def GetContract(self, graph, del_mth):
        """
        Description:
            Return the EqutyIndexCnt object for a specific delivery month.
        Inputs:
            del_mth - the delivery month in LYY format (as in Z11)
        Returns:
            A string.
        """
        if del_mth in graph(self, "Contracts"):
            symbol = graph(self, "Symbol")
            return EquityIndexCnt.get_name(symbol, del_mth)
        else:
            raise MissingContract("Contract {0:s} not found "
                                  "for {1:s}".format(del_mth, self.Name))

    # -------------------------------------------------------------------------
    @RetainedFactory()
    def Spot(self, graph):
        mdd = graph("Database", "MktDataDate")
        sd = mdd + RDate("-1m")
        crv = graph(self, "GetCurve", start=sd, end=mdd, field="Close")
        return Interpolate(crv, mdd)

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor("PropSubGraph")
    def GetCurve(self, graph, start=None, end=None, field=None):
        name = graph(self, "TimeSeries")
        try:
            return TsDbGetCurve(name, start, end, "HLOCV", field)
        except TsNotFound:
            return HlocvCurve() if field is None else Curve()

    # -------------------------------------------------------------------------
    def add_contract(self, cnt_mth, tickers):
        """
        Description:
            Add a new contract or return the existing one.
        Inputs:
            cnt_mth - the contract month in LYY format
            tickers - a dictionary of tickers
        Returns:
            The contract's name.
        """
        if cnt_mth in self.Contracts:
            return GetVal(self, "GetContract", cnt_mth)
        else:
            info = {
                "EquityIndex": self.Name,
                "DeliveryMonth": cnt_mth,
                "Tickers": tickers,
                "RiskProxy": self.Name,
            }
            cnt_obj = EquityIndexCnt(**info)
            try:
                AddObj(cnt_obj)
            except ObjExists:
                obj = GetObj(cnt_obj.Name)
                if obj != cnt_obj:
                    raise RuntimeError("StoredAttrs of existing contract "
                                       "{0:s} don't match those of parent "
                                       "EquityIndex".format(obj.Name))

            self.Contracts.add(cnt_mth)

        return cnt_obj.Name

    # -------------------------------------------------------------------------
    def delete(self):
        sym = self.Symbol
        with ObjDbTransaction("deleting contracts", "SERIALIZABLE"):
            # --- conversion to tuple is needed because the delete method of a
            #     contract removes such contract from the set of contracts of
            #     the asset.
            for cnt_mth in tuple(self.Contracts):
                cnt_name = EquityIndexCnt.get_name.format(sym, cnt_mth)
                try:
                    DelObj(cnt_name)
                except ObjNotFound:
                    print("contract {0:s} not found ?!?".format(cnt_name))


# -----------------------------------------------------------------------------
def prepare_for_test():
    from onyx.core import AddIfMissing
    from ..system import ufo_currency
    from ..system import ufo_database
    from ..system import ufo_holiday_calendar
    from ..system import ufo_exchange

    ufo_database.prepare_for_test()
    ufo_holiday_calendar.prepare_for_test()
    ufo_currency.prepare_for_test()
    ufo_exchange.prepare_for_test()

    sx5e_info = {
        "Symbol": "SX5E",
        "Exchange": "XEUR Exchange",
        "Tickers": {"Bloomberg": "SX5E"},
        "Multiplier": 1.0,
        "ContractSize": 10.0,
    }

    AddIfMissing(EquityIndex(**sx5e_info))
