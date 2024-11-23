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

from onyx.core.database.ufo_base import UfoBase
from onyx.core.database.ufo_fields import IntField, DictField
from onyx.core.depgraph.graph_api import GraphNodeDescriptor
from onyx.core.depgraph.graph_api import CreateInMemory, GetVal
from onyx.core.depgraph.graph_scopes import EvalBlock

from onyx.core.utils.unittest import OnyxTestCase

import unittest

CF_GROWTH = 0.02
G = 0.25   # gearing: D / (D+E)
Kd = 0.06  # cost of debt
Ke = 0.08  # cost of equity
KWDS = {
    "PastCashFlows": {2014: 101.3, 2015: 100.0},
}


###############################################################################
class DCFModel(UfoBase):
    CurrentYear = IntField(default=2016)
    FinalYear = IntField(default=2050)
    PastCashFlows = DictField()
    PastGrowth = DictField()

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor("Callable")
    def CashFlow(self, graph, year):
        if year < graph(self, "CurrentYear"):
            return graph(self, "PastCashFlows")[year]
        else:
            multiplier = 1.0 + graph(self, "CashFlowGrowth", year)
            return graph(self, "CashFlow", year - 1)*multiplier

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor("Callable")
    def CashFlowGrowth(self, graph, year):
        if year < graph(self, "CurrentYear"):
            cf = graph(self, "PastCashFlows")
            return cf[year] / cf[year-1] - 1.0
        else:
            return CF_GROWTH

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor("Callable")
    def WACC(self, graph, year):
        return G*Kd + (1.0 - G)*Ke

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor("Callable")
    def DiscountFactor(self, graph, year):
        return 1.0 / (1.0 + graph(self, "WACC", year))

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor("Callable")
    def DCF(self, graph, year):
        if year > graph(self, "FinalYear"):
            return 0.0
        elif year == graph(self, "FinalYear"):
            return graph(self, "CashFlow", year)
        else:
            cf = graph(self, "CashFlow", year)
            df = graph(self, "DiscountFactor", year)
            return cf + df*graph(self, "DCF", year + 1)


###############################################################################
class TestDCFModel(OnyxTestCase):
    # -------------------------------------------------------------------------
    def setUp(self):
        super().setUp()
        self.instance = CreateInMemory(DCFModel(Name="model", **KWDS))
        self.name = self.instance.Name

    # -------------------------------------------------------------------------
    def tearDown(self):
        super().tearDown()

    # -------------------------------------------------------------------------
    def test_cashflow(self):
        self.assertEqual(GetVal(self.name, "CashFlow", 2016), 102.0)
        self.assertEqual(GetVal(self.name, "CashFlow", 2017), 104.04)

    # -------------------------------------------------------------------------
    def test_cashflow_growth(self):
        cf_2015 = GetVal(self.name, "CashFlowGrowth", 2015)
        self.assertAlmostEqual(cf_2015, -0.0128, 4)
        cf_2016 = GetVal(self.name, "CashFlowGrowth", 2016)
        self.assertEqual(cf_2016, CF_GROWTH)

    # -------------------------------------------------------------------------
    def test_wacc(self):
        self.assertEqual(GetVal(self.name, "WACC", 2017), G*Kd + (1.0 - G)*Ke)

    # -------------------------------------------------------------------------
    def test_discount_factor(self):
        self.assertEqual(
            GetVal(self.name, "DiscountFactor", 2017),
            1.0 / (1.0 + G*Kd + (1.0 - G)*Ke))

    # -------------------------------------------------------------------------
    def test_dcf(self):
        def dcf(cf, final_year):
            # --- auxiliary function to calculate result analytically:
            #     dcf = cf * \sum k=0, N (1+g)^k/(1+wacc)^k
            #         = cf * (1 - q^N+1)/(1 - q)
            #     where q = (1+g)/(1+wacc)
            q = (1.0 + CF_GROWTH) / (1.0 + G*Kd + (1.0 - G)*Ke)
            n = final_year - 2016
            return cf*(1.0 - q**(n+1)) / (1.0 - q)

        cf = GetVal(self.name, "CashFlow", 2016)
        fy = GetVal(self.name, "FinalYear")

        self.assertAlmostEqual(GetVal(self.name, "DCF", 2016), dcf(cf, fy), 10)

        # --- test it on shorter cashflows
        with EvalBlock() as eb:
            for fy in (2020, 2030, 2040):
                eb.change_value(self.name, "FinalYear", fy)
                self.assertAlmostEqual(
                    GetVal(self.name, "DCF", 2016), dcf(cf, fy), 10)


if __name__ == "__main__":
    from onyx.core.utils.unittest import UseEphemeralDbs
    with UseEphemeralDbs():
        unittest.main(failfast=True)
