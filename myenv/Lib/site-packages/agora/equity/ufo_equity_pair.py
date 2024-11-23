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

from onyx.core import Curve, RDate, CurveIntersect
from onyx.core import UfoBase, GetVal, GraphNodeDescriptor
from onyx.core import ReferenceField, StringField, FloatField

from ..econometrics.regression import RobustRegression
from ..econometrics.arma_functions import AR1

import numpy as np

__all__ = ["EquityPair"]


# -----------------------------------------------------------------------------
def get_spread_parms(crv1, crv2):
    x = np.log(crv2.values)
    y = np.log(crv1.values)

    m, c, snr, spr = RobustRegression(x, y)

    root, std_err, cv, _ = AR1(spr, const=True)

    return {"m": m, "c": c, "snr": snr,
            "root": root, "std_err": std_err, "cv": cv}


###############################################################################
class FitError(Exception):
    pass


###############################################################################
class EquityPair(UfoBase):
    """
    class used to represent a pair of two equities.
    """
    Symbol1 = ReferenceField(obj_type="EquityAsset")
    Symbol2 = ReferenceField(obj_type="EquityAsset")

    # --- parameters used to define a spread
    RegRange = StringField("-24m")
    Alpha = FloatField()
    Beta = FloatField()

    name_fmt = "EQP {0:s} {1:s} - {2:s} {3:s}"

    # -------------------------------------------------------------------------
    def __post_init__(self):
        sym1 = GetVal(self.Symbol1, "Symbol")
        sym2 = GetVal(self.Symbol2, "Symbol")
        exchg_code1 = GetVal(GetVal(self.Symbol1, "Exchange"), "Code")
        exchg_code2 = GetVal(GetVal(self.Symbol2, "Exchange"), "Code")

        self.Name = self.name_fmt.format(sym1, exchg_code1, sym2, exchg_code2)

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor("PropSubGraph")
    def Curves(self, graph, start=None, end=None):
        sym1 = graph(self, "Symbol1")
        sym2 = graph(self, "Symbol2")
        ccy1 = graph(sym1, "Denominated")
        ccy2 = graph(sym2, "Denominated")

        sym1_crv = graph(sym1, "GetCurve", start=start, end=end, field="Close")
        sym2_crv = graph(sym2, "GetCurve", start=start, end=end, field="Close")

        if ccy1 != ccy2:
            # --- convert both to US$
            cross1 = "{0:3s}/USD".format(ccy1)
            cross2 = "{0:3s}/USD".format(ccy2)
            cross1_crv = graph(cross1, "GetCurve", start=start, end=end)
            cross2_crv = graph(cross2, "GetCurve", start=start, end=end)

            crvs = CurveIntersect([sym1_crv, sym2_crv, cross1_crv, cross2_crv])
            sym1_crv, sym2_crv, cross1_crv, cross2_crv = crvs

            sym1_crv *= cross1_crv
            sym2_crv *= cross2_crv

            return sym1_crv, sym2_crv

        else:
            return CurveIntersect([sym1_crv, sym2_crv])

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor("Callable")
    def Ratio(self, graph, start, end, use_log=False):
        """
        Description:
            Ratio is defined as:
                Ratio = Symbol1 / Symbol2
            or, if use_log is True:
                Ratio = log(Symbol1 / Symbol2)
        """
        num_crv, den_crv = graph(self, "Curves")
        num_crv = num_crv.crop(start=start, end=end)
        den_crv = den_crv.crop(start=start, end=end)

        if use_log:
            return Curve(
                num_crv.dates, np.log(num_crv.values / den_crv.values))
        else:
            return Curve(num_crv.dates, num_crv.values / den_crv.values)

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor("Callable")
    def Spread(self, graph, start, end):
        """
        Description:
            Spread is defined as:
                Spread = log(Symbol1) - Beta*log(Symbol2) - Alpha
            NB: Alpha and Beta are the stored parameters.
        Inputs:
            start - spread start date
            end   - spread end date
        """
        sym1_crv, sym2_crv = graph(self, "Curves")
        sym1_crv = sym1_crv.crop(start=start, end=end)
        sym2_crv = sym2_crv.crop(start=start, end=end)

        c = graph(self, "Alpha")
        m = graph(self, "Beta")

        spread = np.log(sym1_crv.values) - m*np.log(sym2_crv.values) - c

        return Curve(sym1_crv.dates, spread)

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor("Callable")
    def Ar1Parms(self, graph, start, end):
        """
        Returns:
            A tuple: (root, std_err, cv, ar1_res)
        """
        return AR1(graph(self, "Spread", start, end), const=True)

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor("Callable")
    def Ar1Root(self, graph, start, end):
        parms = graph(self, "Ar1Parms", start, end)
        return parms[0]

    # -------------------------------------------------------------------------
    def fit_spread_parms(self, min_range=None, max_range=None, cv_thr=1.0):
        """
        Description:
            Determine the longest regression range for which we can reject the
            unit root hypothesis for the spread determined via robust
            regression.
        Inputs:
            min_range - minimum value of regression range, in number of months
            max_range - maximum value of regression range, in number of months
            cv_thr    - critical value threshold:
                            the range is accepted if cv > cv_thr
        """
        min_range = min_range or 6
        max_range = max_range or 36

        sym1_crv, sym2_crv = GetVal(self, "Curves")
        range_ed = GetVal("Database", "PricingDate")

        for mths in range(max_range, min_range - 1, -3):
            rule = "-{0:d}m".format(mths)
            range_sd = range_ed + RDate(rule)

            crv1 = sym1_crv.crop(range_sd, range_ed)
            crv2 = sym2_crv.crop(range_sd, range_ed)
            parms = get_spread_parms(crv1, crv2)

            # --- spread is accepted if cv > 1.0
            if parms["cv"] > cv_thr:
                parms["rule"] = rule
                return parms

        raise FitError(
            "{0:s} is never cointegrated for any range in "
            "the last {1:d} months".format(self.Name, max_range))

    # -------------------------------------------------------------------------
    def analyze_spread_parms(self, min_range=None, max_range=None):

        min_range = min_range or 6
        max_range = max_range or 48

        sym1_crv, sym2_crv = GetVal(self, "Curves")
        range_ed = GetVal("Database", "PricingDate")

        head_fmt = "{0:>6s}  {1:>6s}  {2:>6s}  {3:>6s}  {4:>6s}"
        body_fmt = "{rule:>6s}  {m:6.3f}  {c:6.3f}  {root:6.4f}  {cv:6.3f}"
        dashes = "-"*6

        print(head_fmt.format("rule", "m", "c", "root", "cv"))
        print(head_fmt.format(dashes, dashes, dashes, dashes, dashes))

        for mths in range(max_range, min_range - 1, -3):
            rule = "-{0:d}m".format(mths)
            range_sd = range_ed + RDate(rule)

            crv1 = sym1_crv.crop(range_sd, range_ed)
            crv2 = sym2_crv.crop(range_sd, range_ed)
            parms = get_spread_parms(crv1, crv2)
            parms["rule"] = rule

            print(body_fmt.format(**parms))

    # -------------------------------------------------------------------------
    def set_spread_parms(self, reg_range=None):
        if reg_range is None:
            parms = self.fit_spread_parms()
        else:
            rule = "-{0:d}m".format(reg_range)
            sym1_crv, sym2_crv = GetVal(self, "Curves")
            range_ed = GetVal("Database", "PricingDate")
            range_sd = range_ed + RDate(rule)
            crv1 = sym1_crv.crop(range_sd, range_ed)
            crv2 = sym2_crv.crop(range_sd, range_ed)
            parms = get_spread_parms(crv1, crv2)

        self.Alpha = parms["c"]
        self.Beta = parms["m"]
        self.RegRange = rule


# -----------------------------------------------------------------------------
def prepare_for_test():
    from onyx.core import AddIfMissing
    from .ufo_equity_asset import EquityAsset
    from ..system import ufo_currency
    from ..system import ufo_database
    from ..system import ufo_holiday_calendar
    from ..system import ufo_exchange

    ufo_database.prepare_for_test()
    ufo_holiday_calendar.prepare_for_test()
    ufo_currency.prepare_for_test()
    ufo_exchange.prepare_for_test()

    sse_info = {
        "Symbol": "SSE",
        "Exchange": "XLON Exchange",
        "Tickers": {
            "Bloomberg": "SSE",
        },
        "Multiplier": 0.01,
    }

    cna_info = {
        "Symbol": "CNA",
        "Exchange": "XLON Exchange",
        "Tickers": {
            "Bloomberg": "CNA",
        },
        "Multiplier": 0.01,
    }

    AddIfMissing(EquityAsset(**sse_info))
    AddIfMissing(EquityAsset(**cna_info))
    AddIfMissing(EquityPair(Symbol1="EQ SSE LN", Symbol2="EQ CNA LN"))
