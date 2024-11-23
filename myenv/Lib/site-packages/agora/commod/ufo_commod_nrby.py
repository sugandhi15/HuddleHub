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

from onyx.core import Curve, CurveUnion, Date2LYY, DateOffset, DateRange
from onyx.core import GraphNodeDescriptor, GetVal
from onyx.core import IntField, DateField, SelectField, ReferenceField

from ..system.tradable_api import NamedByInference, HashStoredAttrs

import collections

__all__ = ["CommodNrby"]

AVERAGING_TYPES = ["DAILYCALDAYS", "DAILYBIZDAYS", "LAST"]


###############################################################################
class CommodNrby(NamedByInference):
    """
    CommodNrby class, used to provide nearby information to COMMOD tradable
    objects.
    """
    Asset = ReferenceField(obj_type="CommodAsset")
    StartDate = DateField()
    EndDate = DateField()
    AvgType = SelectField(options=AVERAGING_TYPES)
    RollType = IntField(default=0)

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def StartDateRule(self, graph):
        avg_type = graph(self, "AvgType")
        if avg_type == "DAILYCALDAYS":
            return None
        elif avg_type == "DAILYBIZDAYS":
            return "+0b"
        elif avg_type == "LAST":
            asset = graph(self, "Asset")
            return "+0J{0:s}".format(graph(asset, "SettDateRule"))

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def EndDateRule(self, graph):
        avg_type = graph(self, "AvgType")
        if avg_type == "DAILYCALDAYS":
            return None
        elif avg_type == "DAILYBIZDAYS":
            return "-0b"
        elif avg_type == "LAST":
            asset = graph(self, "Asset")
            return "+0J{0:s}".format(graph(asset, "SettDateRule"))

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def IncrementRule(self, graph):
        avg_type = graph(self, "AvgType")
        if avg_type == "DAILYCALDAYS":
            return "+1d"
        elif avg_type == "DAILYBIZDAYS":
            return "+1b"
        elif avg_type == "LAST":
            asset = graph(self, "Asset")
            offset = graph(asset, "NrbyOffset")
            return "+{0:d}m+0J{1:s}".format(1 + offset,
                                            graph(asset, "SettDateRule"))

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def NrbyStartDate(self, graph):
        return DateOffset(graph(self, "StartDate"),
                          graph(self, "StartDateRule"),
                          graph(graph(self, "Asset"), "HolidayCalendar"))

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def NrbyEndDate(self, graph):
        return DateOffset(graph(self, "EndDate"),
                          graph(self, "EndDateRule"),
                          graph(graph(self, "Asset"), "HolidayCalendar"))

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def NearbyDateRule(self, graph):
        """
        Date rule used to determine the relevant nearby contract given a date.
        """
        return "+{0:d}m+0J".format(graph(self, "RollType") +
                                   graph(graph(self, "Asset"), "NrbyOffset"))

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def DataCurve(self, graph):
        """
        The data curve is created by merging two different pieces:
         1) the setteled part of the curve
         2) the open part of the curve
        """
        pd = graph("Database", "PricingDate")
        sd = graph(self, "NrbyStartDate")
        ed = graph(self, "NrbyEndDate")

        asset = graph(self, "Asset")
        cal = graph(asset, "HolidayCalendar")

        sett_rule = graph(asset, "SettDateRule")
        inc_rule = graph(self, "IncrementRule")
        nrby_rule = graph(self, "NearbyDateRule")

        crv = Curve()

        if sd <= pd:
            # --- this is the part of curve that has settled
            cnts = collections.defaultdict(list)
            for d in DateRange(sd, min(pd, ed), inc_rule, cal):
                # --- find the nth (as defined by RollType) nearby contract as
                #     of a given date
                cnt = DateOffset(d, nrby_rule, cal)
                if d > DateOffset(cnt, sett_rule, cal):
                    cnt = DateOffset(cnt, "+1m", cal)

                cnt = graph(asset, "GetContract", Date2LYY(cnt))
                cnts[cnt].append(d)

            # --- build-up the curve
            for cnt, dts in cnts.items():
                cnt_crv = graph(cnt, "GetCurve",
                                start=dts[0], end=dts[-1], field="Close")
                crv = CurveUnion(crv, cnt_crv)

            # --- move forward start date
            if len(crv):
                sd = DateOffset(crv.back.date, inc_rule, cal)
            else:
                sd = pd

        # --- this is the open part of the curve
        for d in DateRange(sd, ed, inc_rule, cal):
            # --- find the nth (as defined by RollType) nearby contract as of
            #     a given date
            cnt = DateOffset(d, nrby_rule, cal)
            if d > DateOffset(cnt, sett_rule, cal):
                cnt = DateOffset(cnt, "+1m", cal)

            crv[d] = graph(graph(asset, "GetContract", Date2LYY(cnt)), "Spot")

        return crv

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def AverageValue(self, graph):
        crv = graph(self, "DataCurve")
        if len(crv):
            return crv.values.mean()
        else:
            return 0.0

    # -------------------------------------------------------------------------
    @property
    def ImpliedName(self):
        mkt = GetVal(self.Asset, "Market")
        sym = GetVal(self.Asset, "Symbol")
        mush = HashStoredAttrs(self, 8)
        return "CmdNRBY {0:s} {1:s} {2:8s} {{0:2d}}".format(mkt, sym, mush)
