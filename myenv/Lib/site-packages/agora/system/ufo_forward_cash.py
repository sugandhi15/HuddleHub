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

from onyx.core import GraphNodeDescriptor, ReferenceField, DateField

from .tradable_api import AgingTradableObj, AddByInference
from .ufo_cash_balance import CashBalance


###############################################################################
class ForwardCash(AgingTradableObj):
    """
    Tradable class that represents cash to be exchanged at a future date.
    """
    Currency = ReferenceField(obj_type="Currency")
    PaymentDate = DateField()

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def MktVal(self, graph):
        pd = graph("Database", "PricingDate")
        ed = graph(self, "PaymentDate")

        if pd < ed:
            ccy = graph(self, "Currency")
            return graph(ccy, "DiscountFactor", ed, pd)
        else:
            return 1.0

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def MktValUSD(self, graph):
        cross = "{0:3s}/USD".format(graph(self, "Currency"))
        return graph(self, "MktVal")*graph(cross, "Spot")

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def ExpirationDate(self, graph):
        return graph(self, "PaymentDate")

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def NextTransactionDate(self, graph):
        return graph(self, "PaymentDate")

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def TradeTypes(self, graph):
        mapping = super().TradeTypes
        mapping.update({
            "Pay/Receive": "PayReceiveSecurities",
        })
        return mapping

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def ExpectedTransaction(self, graph):
        return "Pay/Receive"

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def PayReceiveSecurities(self, graph):
        cash = CashBalance(Currency=graph(self, "Currency"))
        return [
            {"Security": AddByInference(cash, in_memory=True),
             "Quantity": 1.0},
        ]

    # -------------------------------------------------------------------------
    @property
    def ImpliedName(self):
        pay_date = self.PaymentDate.strftime("%d%m%y")
        return "FWD {0:3s} {1:6s}".format(self.Currency, pay_date)


# -----------------------------------------------------------------------------
def prepare_for_test():
    from onyx.core import Date, RDate
    from .tradable_api import AddByInference
    from . import ufo_database
    from . import ufo_holiday_calendar
    from . import ufo_currency
    from . import ufo_currency_cross

    ufo_database.prepare_for_test()
    ufo_holiday_calendar.prepare_for_test()
    ufo_currency.prepare_for_test()
    ufo_currency_cross.prepare_for_test()

    paydt = Date.today() + RDate("+1y")

    securities = []
    for ccy in ["USD", "EUR", "GBP"]:
        securities.append(
            AddByInference(ForwardCash(Currency=ccy, PaymentDate=paydt)))

    return [sec.Name for sec in securities]
