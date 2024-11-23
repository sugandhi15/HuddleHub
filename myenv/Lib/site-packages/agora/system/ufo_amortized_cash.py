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

from onyx.core import Structure, DateRange
from onyx.core import GraphNodeDescriptor
from onyx.core import ReferenceField, DateField, StringField

from .tradable_api import AgingTradableObj, AddByInference, HashStoredAttrs
from .ufo_forward_cash import ForwardCash


###############################################################################
class AmortizedCash(AgingTradableObj):
    """
    Tradable class that represents the depreciation/amortization of an asset or
    liability.
    For instance, to book an amortized fee one will have to book a buy trade on
    AmortizedCash with UnitPrice=1.0 and Quantity=FeeAmount. The cash-flow
    takes place on the trade's settlement date but the fee hits the P&L on the
    basis of the amortization schedule.
    """
    Currency = ReferenceField(obj_type="Currency")
    StartDate = DateField()
    EndDate = DateField()
    DateRule = StringField(default="+1b")

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def Dates(self, graph):
        start = graph(self, "StartDate")
        end = graph(self, "EndDate")
        rule = graph(self, "DateRule")
        return list(DateRange(start, end, rule))

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def AmortizedAmount(self, graph):
        return 1.0 / float(len(graph(self, "Dates")))

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def Leaves(self, graph):
        pos_date = graph("Database", "PositionsDate")
        ccy = graph(self, "Currency")
        dts = graph(self, "Dates")
        amt = graph(self, "AmortizedAmount")
        qty = 1.0 - amt*sum([1.0 for d in dts if d <= pos_date])
        fwd_cash = ForwardCash(Currency=ccy, PaymentDate=pos_date)
        fwd_cash = AddByInference(fwd_cash, in_memory=True)
        return Structure({fwd_cash.Name: qty})

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def MktValUSD(self, graph):
        mtm = 0.0
        for sec, qty in graph(self, "Leaves").items():
            mtm += qty*graph(sec, "MktValUSD")
        return mtm

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def MktVal(self, graph):
        cross = "{0:3s}/USD".format(graph(self, "Currency"))
        return graph(self, "MktValUSD") / graph(cross, "Spot")

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def ExpirationDate(self, graph):
        return graph(self, "EndDate")

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def NextTransactionDate(self, graph):
        return graph(self, "EndDate")

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def TradeTypes(self, graph):
        mapping = super().TradeTypes
        mapping.update({
            "Expiry": "ExpirySecurities",
        })
        return mapping

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def ExpectedTransaction(self, graph):
        return "Expiry"

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def ExpirySecurities(self, graph):
        return []

    # -------------------------------------------------------------------------
    @property
    def ImpliedName(self):
        start = self.StartDate.strftime("%d%m%y")
        end = self.EndDate.strftime("%d%m%y")
        mush = HashStoredAttrs(self, 4)
        return ("AMT {0:3s} {1:6s} {2:6s} {3:4s} "
                "{{0:2d}}").format(self.Currency, start, end, mush)
