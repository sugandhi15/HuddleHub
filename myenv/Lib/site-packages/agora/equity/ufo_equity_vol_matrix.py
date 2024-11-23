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

from onyx.core import Date, CalcTerm
from onyx.core import SelectField, ReferenceField, DictField, Archivable
from onyx.core import GetVal, EvalBlock
from onyx.core import GraphNodeDescriptor, MktIndirectionFactory

from onyx.quantlib.black_scholes import implied_vol

import bisect

__all__ = ["EquityVolMatrix"]


###############################################################################
class EquityVolMatrix(Archivable):
    """
    EquityVolMatrix class.
    """
    Asset = ReferenceField(obj_type="EquityAsset")
    Style = SelectField(options=["EUROPEAN", "AMERICAN"])

    # -------------------------------------------------------------------------
    def __post_init__(self):
        symbol = GetVal(self.Asset, "Symbol")
        exch_code = GetVal(GetVal(self.Asset, "Exchange"), "Code")
        self.Name = ("EQ VOLMAT {0:s} {1:s}").format(symbol, exch_code)

    # -------------------------------------------------------------------------
    @MktIndirectionFactory(DictField)
    def PrcMarks(self, graph):
        """
        Price Marks are structured as follows:
        {
            expiry: [
                {
                    strike: [price_call, price_put],
                    ...
                }
                ...
            ]
        }
        NB: these are NOT used for pricing, but only to calculate implied
            volatilities that are then stored in VolMarks.
        """
        pass

    # -------------------------------------------------------------------------
    @MktIndirectionFactory(DictField)
    def VolMarks(self, graph):
        """
        Marks are structured as follows:
        {
            expiry: [
                {
                    strike: [vol_call, vol_put],
                    ...
                }
                ...
            ]
        }
        """
        pass

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor("Property")
    def ExpirationDates(self, graph):
        return sorted([Date.parse(d) for d in graph(self, "VolMarks")])

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def StrikesByExpDate(self, graph, exp_date):
        exp_date = exp_date.isoformat()
        return sorted([float(k) for k in graph(self, "VolMarks")[exp_date]])

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def VolByExpStrike(self, graph, exp_date, strike):
        exp_date_str = exp_date.isoformat()
        strike_str = str(strike)
        vols = graph(self, "VolMarks")[exp_date_str][strike_str]

        return 0.5*(vols[0] + vols[1])

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def VolByExpStrikeType(self, graph, exp_date, strike, opt_type):
        # --- use only the first letter capitalized
        opt_type = opt_type[0].upper()

        if strike == "ATM":
            strike = graph(self, "AtmStrikeByExpDate", exp_date)

        exp_date_str = exp_date.isoformat()
        strike_str = str(strike)
        vols = graph(self, "VolMarks")[exp_date_str][strike_str]

        if opt_type == "C":
            return vols[0]
        elif opt_type == "P":
            return vols[1]
        else:
            raise NameError("Unrecognized option type, {0:s}".format(opt_type))

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def AtmVol(self, graph, exp_date, opt_type):
        return graph(self, "VolByExpStrikeType", exp_date, "ATM", opt_type)

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def AtmStrikeByExpDate(self, graph, exp_date):
        spot = graph(graph(self, "Asset"), "Spot")
        strikes = graph(self, "StrikesByExpDate", exp_date)

        ih = bisect.bisect_left(strikes, spot)
        il = max(0, ih - 1)
        idx = il if spot - strikes[il] < strikes[ih] - spot else ih

        return strikes[idx]

    # -------------------------------------------------------------------------
    def generate_vol_marks(self, pd, price_marks):
        vol_marks = price_marks
        is_american = (self.Style == "AMERICAN")

        with EvalBlock() as eb:
            eb.change_value("Database", "MktDataDate", pd)
            spot = GetVal(self.Asset, "Spot")

        for exp_date_str, opts_by_strike in price_marks.items():
            exp_date = Date.parse(exp_date_str)

            rd = ...
            rf = GetVal(self.Asset, "DividendYield", pd, exp_date)

            term = CalcTerm(pd, exp_date)

            for strike_str, (p_call, p_put) in opts_by_strike.items():
                strike = float(strike_str)

                iv_c = implied_vol("C", p_call, spot, strike,
                                   term, rd, rf, american=is_american)
                iv_p = implied_vol("P", p_put, spot, strike,
                                   term, rd, rf, american=is_american)

                vol_marks[exp_date_str][strike_str] = [iv_c, iv_p]

        return vol_marks
