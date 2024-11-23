###############################################################################
#
#   Copyright: (c) 2015 Carlo Sbraccia
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

from ..datatypes.curve import Curve
from ..datatypes.gcurve import CurveError
from ..datatypes.hlocv import HlocvCurve
from ..datatypes.rdate import RDate
from .date_fns import DateRange

import numpy as np
import bisect
import collections

__all__ = [
    "CurveShift",
    "CurveIntersect",
    "CurveUnion",
    "CurveSum",
    "Interpolate",
    "ApplyAdjustments",
    "ApplyToCurves",
    "CumSum",
    "Daily",
    "Weekly",
    "Monthly",
    "Quarterly",
    "Yearly",
]


# -----------------------------------------------------------------------------
def CurveShift(crv, rule, calendar=None):
    """
    Description:
        Apply the specified date rule to the each knot in the curve to obtain
        a new shifted curve.
        For a list of valid rules, see the RDate module.
    Inputs:
        crv      - the input curve
        rule     - the date-rule
        calendar - a holiday calendar used to identify business days
    Returns:
        The shifted curve.
    """
    rdt = RDate(rule, calendar)
    return crv.create_raw([d + rdt for d in crv.dates], crv.values)


# -----------------------------------------------------------------------------
def CurveIntersect(curves):
    """
    Description:
        Intersect a list of curves returning a new list of curves with only
        the common knots presents.
    Inputs:
        curves - the list of curves to be intersected
    Returns:
        A list of curves with common knots.
    """
    # --- first find dates common to all curves
    common_dates = set.intersection(*[set(crv.dates) for crv in curves])

    # --- then use these dates to build a list of curves with common knots
    intersected_curves = []
    for crv in curves:
        idxs = np.array([k for k, d in
                         enumerate(crv.dates) if d in common_dates])
        if len(idxs):
            new_crv = crv.create_raw(crv.dates[idxs], crv.values[idxs])
        else:
            new_crv = crv.create_raw([], [])
        intersected_curves.append(new_crv)

    return intersected_curves


# -----------------------------------------------------------------------------
def CurveUnion(crv1, crv2):
    """
    Description:
        Return a curve formed by the union of knots from the two input
        curves. If common knots are present, those from the first curve
        will be used.
    Inputs:
        crv1 - the first  curve (takes precedence)
        crv2 - the second curve
    Returns:
        A new curve with the union of knots.
    """
    if type(crv1) != type(crv2):
        raise CurveError("CurveUnion: curves must be of the same "
                         "type: {0!s} - {1!s}".format(type(crv1), type(crv2)))

    # --- create auxiliary dictionaries
    d1 = dict(zip(crv1.dates, crv1.values))
    d2 = dict(zip(crv2.dates, crv2.values))

    # --- merge the two dictionaries giving priority to d1
    d2.update(d1)

    # --- NB: the curve constructor sorts knots by date automatically
    return crv1.__class__(d2.keys(), d2.values(), crv1.dtype)


# -----------------------------------------------------------------------------
def CurveSum(curves):
    """
    Description:
        Sum a list of curves knot by knot, using interpolation for curves
        missing knots for certain dates.
    Inputs:
        curves - the list of curves to be summed
    Returns:
       A new curve.
    """
    dts = sorted(set.union(*[set(crv.dates) for crv in curves]))
    vls = [sum([Interpolate(crv, d) for crv in curves]) for d in dts]
    return Curve.create_raw(dts, vls)


# -----------------------------------------------------------------------------
def Interpolate(crv, d, method="Step"):
    """
    Description:
        Return the value at curve knot using the required interpolation scheme.
    Inputs:
        crv    - the curve
        d      - the knot date (a Date)
        method - interpolation scheme. Choose among:
                    "Step":   return previous knot
                    "Linear": linear interpolation between knots
    Returns:
        The curve knot's value.
    """
    if not len(crv):
        raise CurveError("Interpolate: input curve has no data")

    try:
        return crv[d]
    except IndexError:
        if method == "Step":
            idx = bisect.bisect_left(crv.dates, d)
            if idx:
                return crv.values[idx-1]
            else:
                return crv.values[0]

        elif method == "Linear":
            idx = bisect.bisect_left(crv.dates, d)
            if idx == 0:
                return crv.values[0]
            elif idx == len(crv.dates):
                return crv.values[-1]
            else:
                d0 = crv.dates[idx-1]
                d1 = crv.dates[idx]
                w = (d - d0) / (d1 - d0)
                return w*crv.values[idx] + (1.0 - w)*crv.values[idx-1]

        else:
            raise NameError("Interpolate: unrecognized "
                            "interpolation method:{0:s}".format(method))


# -----------------------------------------------------------------------------
def ApplyAdjustments(crv, adj_crv):
    """
    Description:
        Apply a curve of multiplicative adjustments to an other curve. At the
        moment only backward looking adjustments are implemented.
    Inputs:
        crv     - the input curve
        adj_crv - the curve of adjustments
    Returns:
        A new curve of same type as crv.
    """
    if not len(crv):
        raise CurveError("ApplyAdjustments: input curve has no data")

    vls = crv.values
    dts = crv.dates

    if isinstance(crv, Curve):
        i = 0
        for d, v in adj_crv:
            j = bisect.bisect_left(dts, d)
            vls[i:j] *= v
            i = j

    elif isinstance(crv, HlocvCurve):
        i = 0
        for d, v in adj_crv:
            j = bisect.bisect_left(dts, d)
            vls[i:j,:4] *= v  # analysis:ignore
            i = j

    else:
        raise TypeError("Invalid curve type: {0!s}".format(type(crv)))

    return crv.create_raw(dts, vls)


# -----------------------------------------------------------------------------
def CumSum(crv):
    """
    Description:
        Compute the cumulative sum of the curve values.
    Inputs:
        crv - the input curve
    Returns:
        A new curve with the cumulative sum.
    """
    if not isinstance(crv, Curve):
        raise CurveError("Cumulative sum is only available "
                         "for Curve objects, not for {0!s}".format(type(crv)))

    return crv.create_raw(crv.dates, np.cumsum(crv.values))


# -----------------------------------------------------------------------------
def ApplyToCurves(curves, func=min):
    """
    Description:
        Create a new curve appling a given function to the common knots of a
        list of curves.
    Inputs:
        curves - a list of curves
        func   - the function applied to the common knots (such as min, max,
                 mean, median, etc)
    Returns:
        A new curve where every common knot has value given by func(values)
        where values are for the same date.
    """
    curves = CurveIntersect(curves)

    crv = curves.pop()
    vls = [[v] for v in crv.values]

    for crv in curves:
        for k, v in enumerate(crv.values):
            vls[k].append(v)

    return crv.create_raw(crv.dates, [func(v) for v in vls])


# -----------------------------------------------------------------------------
def Daily(crv, method="InterpolateStep", calendar=None):
    """
    Description:
        Return a daily (business days) curve obtained by up-sampling via
        interpolation/extrapolation.
    Inputs:
        crv      - the input curve
        method   - interpolation method
        calendar - a holiday calendar used to identify business days
    Returns:
        A new curve with daily knots.
    """
    dates = list(DateRange(crv.front.date, crv.back.date, "+1b", calendar))
    values = [Interpolate(crv, d, method) for d in dates]

    return crv.create_raw(dates, values)


# -----------------------------------------------------------------------------
def Weekly(crv):
    """
    Description:
        Return a weekly averaged curve. Weekly values are set on Mondays.
    Inputs:
        crv - the input curve
    Returns:
        A new curve with weekly knots.
    """
    rd = RDate("+7d")
    d0 = crv.front.date + RDate("-1M")
    d1 = d0 + rd
    avg = collections.defaultdict(list)
    for d, v in crv:
        while True:
            if d < d1:
                avg[d0].append(v)
                break
            else:
                d0 = d1
                d1 = d0 + rd

    return Curve(avg.keys(), [np.mean(v) for v in avg.values()])


# -----------------------------------------------------------------------------
def Monthly(crv):
    """
    Description:
        Return a monthly averaged curve. Monthly values are set on the first
        day of the month.
    Inputs:
        crv - the input curve
    Returns:
        A new curve with monthly knots.
    """
    rd = RDate("+1m")
    d0 = crv.front.date + RDate("+0J")
    d1 = d0 + rd
    avg = collections.defaultdict(list)
    for d, v in crv:
        while True:
            if d < d1:
                avg[d0].append(v)
                break
            else:
                d0 = d1
                d1 = d0 + rd

    return Curve(avg.keys(), [np.mean(v) for v in avg.values()])


# -----------------------------------------------------------------------------
def Quarterly(crv):
    """
    Description:
        Return a quarterly averaged curve. Quarterly average values are set on
        the first day of the quarter.
    Inputs:
        crv - the input curve
    Returns:
        A new curve with quarterly knots.
    """
    rd = RDate("+Q+1d")
    d0 = crv.front.date + RDate("+q")
    d1 = d0 + rd
    avg = collections.defaultdict(list)
    for d, v in crv:
        while True:
            if d < d1:
                avg[d0].append(v)
                break
            else:
                d0 = d1
                d1 = d0 + rd

    return Curve(avg.keys(), [np.mean(v) for v in avg.values()])


# -----------------------------------------------------------------------------
def Yearly(crv):
    """
    Description:
        Return a yearly averaged curve. Year average values are set on the
        first day of the year.
    Inputs:
        crv - the input curve
    Returns:
        A new curve with yearly knots.
    """
    rd = RDate("+E+1d")
    d0 = crv.front.date + RDate("+A")
    d1 = d0 + rd
    avg = collections.defaultdict(list)
    for d, v in crv:
        while True:
            if d < d1:
                avg[d0].append(v)
                break
            else:
                d0 = d1
                d1 = d0 + rd

    return Curve(avg.keys(), [np.mean(v) for v in avg.values()])
