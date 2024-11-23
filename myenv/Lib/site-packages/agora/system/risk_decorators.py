###############################################################################
#
#   Copyright: (c) 2015-2020 Carlo Sbraccia
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

from onyx.core import Structure, RDate
from onyx.core import Curve, Knot, CurveIntersect, Interpolate
from onyx.core import GetObj, GraphNodeDescriptor, ChildrenSet, GraphScope

from .price_curves_api import get_curve_usd

import numpy as np
import math

__all__ = ["WithRiskMethods"]


# -----------------------------------------------------------------------------
def WithRiskMethods(cls):
    """
    Description:
        Class decorator. It can be applied to any class implementing MktVal
        and MktValUSD methods.
        It adds the following methods to the decorated class:
            Deltas
            FxExposures
            GrossExposure
            NetExposure
            BetaAdjNetExposure
            BetaBySecurity
            ForwardVol
            VaR
            AdjVar
            cVaR
            MaxLoss
        These are further auxiliary methods used by the ones described above:
            Weights
            HistoricalReturns
    """
    # -------------------------------------------------------------------------
    def Deltas(self, graph):
        deltas = Structure()
        # --- the set of children is calculated outside the graph scope so that
        #     the topology of the graph remains visible outside the scope
        children = ChildrenSet((self, "MktValUSD"), "Spot", "Asset", graph)
        with GraphScope() as scope:
            for kid in children:
                cross = "{0:3s}/USD".format(graph(kid, "Denominated"))
                spot = graph(kid, "Spot")
                fx = graph(cross, "Spot")
                shift = 0.01*spot
                scope.change_value(kid, "Spot", spot+shift)
                up = graph(self, "MktValUSD")
                scope.change_value(kid, "Spot", spot-shift)
                dw = graph(self, "MktValUSD")
                scope.change_value(kid, "Spot", spot)
                deltas += Structure({kid: (up-dw) / (2.0*shift*fx)})
        deltas.drop_zeros()
        return deltas

    # -------------------------------------------------------------------------
    def FxExposures(self, graph):
        exposures = Structure()
        # --- the set of children is calculated outside the graph scope so that
        #     the topology of the graph remains visible outside the scope
        children = ChildrenSet(
            (self, "MktValUSD"), "Spot", "CurrencyCross", graph)
        with GraphScope() as scope:
            for kid in children:
                spot = graph(kid, "Spot")
                shift = 0.01*spot
                scope.change_value(kid, "Spot", spot+shift)
                up = graph(self, "MktValUSD")
                scope.change_value(kid, "Spot", spot-shift)
                dw = graph(self, "MktValUSD")
                scope.change_value(kid, "Spot", spot)
                exposures += Structure({kid: (up-dw) / (2.0*shift)})
        exposures.drop_zeros()
        return exposures

    # -------------------------------------------------------------------------
    def GrossExposure(self, graph):
        gross = 0.0
        for sec, qty in graph(self, "Deltas").items():
            spot_usd = graph(sec, "SpotUSD")
            gross += math.fabs(qty)*spot_usd
        cross = "{0:3s}/USD".format(graph(self, "Denominated"))
        fx = graph(cross, "Spot")
        return gross / fx

    # -------------------------------------------------------------------------
    def NetExposure(self, graph):
        net = 0.0
        for sec, qty in graph(self, "Deltas").items():
            spot_usd = graph(sec, "SpotUSD")
            net += qty*spot_usd
        cross = "{0:3s}/USD".format(graph(self, "Denominated"))
        fx = graph(cross, "Spot")
        return net / fx

    # -------------------------------------------------------------------------
    def Weights(self, graph):
        weights = Structure()
        cross = "{0:3s}/USD".format(graph(self, "Denominated"))
        gross = graph(self, "GrossExposure") * graph(cross, "Spot")
        for sec, qty in graph(self, "Deltas").items():
            spot_usd = graph(sec, "SpotUSD")
            weights[sec] = qty*spot_usd / gross
        return weights

    # -------------------------------------------------------------------------
    def BetaAdjNetExposure(self, graph):
        beta_by_sec = graph(self, "BetaBySecurity")
        beta = 0.0
        for sec, qty in graph(self, "Deltas").items():
            beta += beta_by_sec[sec]*qty*graph(sec, "SpotUSD")
        cross = "{0:3s}/USD".format(graph(self, "Denominated"))
        fx = graph(cross, "Spot")
        return beta / fx

    # -------------------------------------------------------------------------
    def BetaBySecurity(self, graph):
        # --- to improve performance:
        #     1) we fetch curves using Risk.StartDate and Risk.EndDate and then
        #        we crop them to Risk.BetaStartDate and Risk.BetaEndDate,
        #     2) we dynamically add BetaLookupTable attribute to each security
        #        and cache in there beta by (index, start date, end date).
        start = graph("Risk", "StartDate")
        end = graph("Risk", "EndDate")
        beta_start = graph("Risk", "BetaStartDate")
        beta_end = graph("Risk", "BetaEndDate")
        betas = Structure()
        index = graph("Risk", "RefIndex")
        idx_prcs_full = get_curve_usd(index, beta_start, beta_end)
        for sec in graph(self, "Deltas"):
            key = (index, beta_start, beta_end)
            sec = GetObj(sec)
            try:
                beta = sec.BetaLookupTable[key]
            except (AttributeError, KeyError) as err:
                sec_prcs = graph(sec, "PricesForRisk",
                                 start, end).crop(beta_start, beta_end)
                sec_prcs, idx_prcs = CurveIntersect([sec_prcs, idx_prcs_full])
                # --- do not attempt to calculate beta with less than 15
                #     datapoints
                if len(sec_prcs) < 15:
                    npts = len(sec_prcs)
                    raise RuntimeError(
                        "cannot calculate beta with "
                        "less than 15 data points: {0:d}".format(npts))
                s_rets = np.diff(np.log(sec_prcs.values))
                s_rets -= s_rets.mean()
                i_rets = np.diff(np.log(idx_prcs.values))
                i_rets -= i_rets.mean()
                beta = np.dot(i_rets, s_rets) / np.dot(i_rets, i_rets)
                if isinstance(err, AttributeError):
                    # --- lookup table doesn't exist yet for this security
                    sec.BetaLookupTable = {key: beta}
                else:
                    sec.BetaLookupTable[key] = beta
            betas[sec.Name] = beta
        return betas

    # -------------------------------------------------------------------------
    def HistoricalReturns(self, graph, rule):
        start = graph("Risk", "StartDate")
        end = graph("Risk", "EndDate")

        cross = "{0:3s}/USD".format(graph(self, "Denominated"))
        dates = date_range_backwards(end, start, rule)
        agg_returns = None

        for sec, weight in graph(self, "Weights").items():
            prcs = graph(sec, "PricesForRisk", start, end)
            fx = graph(cross, "GetCurve").crop(start, end)
            prcs, fx = CurveIntersect([prcs, fx])
            prcs = prcs / fx
            prcs = np.array([Interpolate(prcs, d) for d in dates])
            rets = Curve(dates[1:], np.diff(np.log(prcs)))

            if agg_returns is None:
                agg_returns = rets*weight
            else:
                agg_returns += rets*weight

        if agg_returns is None:
            return Curve()
        else:
            return agg_returns

    # -------------------------------------------------------------------------
    def ForwardVol(self, graph):
        start = graph("Risk", "VaRStartDate")
        end = graph("Risk", "VaREndDate")
        rets = graph(self, "HistoricalReturns", "-1b").crop(start, end).values
        if len(rets):
            rets -= rets.mean()
            return graph(self, "GrossExposure")*rets.std()
        else:
            return 0.0

    # -------------------------------------------------------------------------
    def VaR(self, graph, rule="-1b", pctl=95.0):
        start = graph("Risk", "VaRStartDate")
        end = graph("Risk", "VaREndDate")
        rets = graph(self, "HistoricalReturns", rule).crop(start, end).values
        if len(rets):
            rets -= rets.mean()
            gross = graph(self, "GrossExposure")
            return -gross*np.percentile(rets, 100.0 - pctl)
        else:
            return 0.0

    # -------------------------------------------------------------------------
    def AdjVaR(self, graph, rule="-1b", pctl=95.0, nbos_adj=60):
        start = graph("Risk", "VaRStartDate")
        end = graph("Risk", "VaREndDate")
        rets = graph(self, "HistoricalReturns", rule).crop(start, end).values
        if len(rets):
            rets -= rets.mean()
            adj = rets[-nbos_adj:].std() / rets.std()
            return adj*graph(self, "VaR", rule=rule, pctl=pctl)
        else:
            return 0.0

    # -------------------------------------------------------------------------
    def cVaR(self, graph, rule="-1b", pctl=95.0):
        start = graph("Risk", "VaRStartDate")
        end = graph("Risk", "VaREndDate")
        rets = graph(self, "HistoricalReturns", rule).crop(start, end).values
        if len(rets):
            rets -= rets.mean()
            gross = graph(self, "GrossExposure")
            cvar_pct = rets[rets <= np.percentile(rets, 100.0 - pctl)].mean()
            return -gross*cvar_pct
        else:
            return 0.0

    # -------------------------------------------------------------------------
    def MaxLoss(self, graph, rule="-1b"):
        # --- the date of max loss is meant to be the beginning of the
        #     ndays interval
        rets_crv = graph(self, "HistoricalReturns", rule)
        rets = rets_crv.values
        if len(rets):
            rets -= rets.mean()
            gross = graph(self, "GrossExposure")
            max_loss_idx = rets.argmax()
            max_loss_val = gross*rets[max_loss_idx]
            max_loss_date = rets_crv.dates[max_loss_idx]
        else:
            max_loss_val = 0.0
            max_loss_date = None

        return Knot(max_loss_date, max_loss_val)

    # --- here we whack graph node descriptors (method wrappers) into the
    #     decorated class
    cls.Deltas = GraphNodeDescriptor()(Deltas)
    cls.FxExposures = GraphNodeDescriptor()(FxExposures)
    cls.GrossExposure = GraphNodeDescriptor()(GrossExposure)
    cls.NetExposure = GraphNodeDescriptor()(NetExposure)
    cls.Weights = GraphNodeDescriptor()(Weights)

    cls.BetaBySecurity = GraphNodeDescriptor()(BetaBySecurity)
    cls.BetaAdjNetExposure = GraphNodeDescriptor()(BetaAdjNetExposure)

    cls.HistoricalReturns = GraphNodeDescriptor("Callable")(HistoricalReturns)

    cls.ForwardVol = GraphNodeDescriptor()(ForwardVol)
    cls.VaR = GraphNodeDescriptor("PropSubGraph")(VaR)
    cls.AdjVaR = GraphNodeDescriptor("PropSubGraph")(AdjVaR)
    cls.cVaR = GraphNodeDescriptor("PropSubGraph")(cVaR)
    cls.MaxLoss = GraphNodeDescriptor("PropSubGraph")(MaxLoss)

    return cls


# -----------------------------------------------------------------------------
def date_range_backwards_iter(end, start, rule):
    # --- auxiliary function to get a date iteretor that walks backward from an
    #     end date based on a given date rule
    shift = RDate(rule)
    d = end
    while d >= start:
        yield d
        d = d + shift


# -----------------------------------------------------------------------------
def date_range_backwards(end, start, rule):
    # --- auxiliary function to get a list of dates sorted in ascending order
    #     that walks backwards from the end date according to the provided date
    #     rule
    return list(reversed(list(date_range_backwards_iter(end, start, rule))))
