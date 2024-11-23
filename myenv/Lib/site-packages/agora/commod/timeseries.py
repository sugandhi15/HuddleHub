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

from onyx.core import Date, Date2LYY, LYY2Date
from onyx.core import CountBizDays, DateOffset, DateRange
from onyx.core import Curve, CurveIntersect
from onyx.core import TsNotFound
from onyx.core import GetVal

import numpy as np
import collections


# -----------------------------------------------------------------------------
def get_strip(commod, start, end, avg_type="LAST"):
    """
    Description:
        Return the historical timeseries for the required strip. The strip
        is defined as the average of all contracts with delivery date
        within start and end dates.
    Inputs:
        commod   - the name of a CommodAsset
        start    - the start date defining the strip
        end      - the   end date defining the strip
        avg_type - the averaging type. Valid choices are:
                    - DAILYCALDAYS
                    - DAILYBIZDAYS
                    - LAST
    Example:
        GetStrip(Date(2012, 1, 1), Date(2012, 12, 31), "DAILYBIZDAYS")
        returns the historical curve for the Cal12 swap for a commodity
        that prices out every business day.
    """
    cal = GetVal(commod, "HolidayCalendar")
    sdr = GetVal(commod, "SettDateRule")
    nbo = GetVal(commod, "NrbyOffset")

    avg_type = avg_type.upper()
    if avg_type == "DAILYCALDAYS":
        sd_rule = "+0d"
        ed_rule = "-0d"
        inc_rule = "+1d"
    elif avg_type == "DAILYBIZDAYS":
        sd_rule = "+0b"
        ed_rule = "-0b"
        inc_rule = "+1b"
    elif avg_type == "LAST":
        sd_rule = "+0J{0:s}".format(sdr)
        ed_rule = "+0J{0:s}".format(sdr)
        inc_rule = "+{0:d}m+0J{1:s}".format(1+nbo, sdr)
    else:
        raise NameError("Unrecognized "
                        "averaging type {0:s}".format(avg_type))

    sd = DateOffset(start, sd_rule, cal)
    ed = DateOffset(end, ed_rule, cal)
    cnts = [GetVal(commod, "ActiveByDate", d)
            for d in DateRange(sd, ed, inc_rule, cal)]

    # --- accumulate historical prices and quantities for all relevant
    #     contracts
    crvs, qtys = [], []
    for cnt, qty in collections.Counter(cnts).items():
        cnt = GetVal(commod, "GetContract", cnt)
        crvs.append(GetVal(cnt, "GetCurve", field="close"))
        qtys.append(float(qty))

    crvs = CurveIntersect(crvs)
    qtot = qtys[0]
    svls = qtys[0]*crvs[0].values  # sum of values (element by element)
    for k in range(1, len(crvs)):
        qtot += qtys[k]
        svls += qtys[k]*crvs[k].values

    return Curve(crvs[0].dates, svls/qtot)


# -----------------------------------------------------------------------------
def fwd_curve(commod):
    """
    Description:
        Return the forward curve as of a given date.
    Inputs:
        commod - the name of a CommodAsset
    Returns:
        A curve.
    """
    mdd = GetVal("Database", "MktDataDate")
    cal = GetVal(commod, "HolidayCalendar")
    if mdd <= DateOffset(mdd, GetVal(commod, "SettDateRule"), cal):
        offset = GetVal(commod, "NrbyOffset")
    else:
        offset = 1 + GetVal(commod, "NrbyOffset")

    sd = DateOffset(mdd, "+{0:d}m+0J".format(offset), cal)

    fwd_crv = Curve()
    for del_mth in GetVal(commod, "Contracts"):
        # --- contract's month start date
        cnt_sd = LYY2Date(del_mth)
        # --- only include contracts in the range
        if sd <= cnt_sd:
            cnt = GetVal(commod, "GetContract", del_mth)
            try:
                fwd_crv[cnt_sd] = GetVal(cnt, "Spot")
            except TsNotFound:
                # --- no time series for this contract: skip
                continue

    return fwd_crv


# -----------------------------------------------------------------------------
def nearby(commod, idx=0, start=None, end=None, smooth=False):
    """
    Description:
        Returns the historical time series for a given nearby month.
    Inputs:
        commod - the name of a CommodAsset
        idx    - the nearby index (0 is prompt month)
        start  - the start date of the curve
        end    - the   end date of the curve
        smooth - if True, use a weighted combination of two consecutive
                 months
    """
    if idx < 0:
        raise ValueError("Nearby index cannot "
                         "be negative: idx = {0:d}".format(idx))

    # --- if available, use default values for sd and ed
    start = start or Date.low_date()
    end = end or GetVal("Database", "MktDataDate")
    cal = GetVal(commod, "HolidayCalendar")

    # --- date rules that define the portion of the curve to be used for
    #     each contract
    rule_sd = "-1m{0:s}+1d".format(GetVal(commod, "SettDateRule"))
    rule_ed = GetVal(commod, "SettDateRule")

    # --- for all contracts in the range, select the ones that have a
    #     non-empty time series within the required date range
    cnts_iter = (Date2LYY(d) for d in DateRange(start, end, "0J+1m", cal))
    cnts_within_range = [cnt for cnt in cnts_iter
                         if cnt in GetVal(commod, "Contracts")]

    # --- get start dates for the first and last contracts in the range
    first_cnt_sd = LYY2Date(cnts_within_range[0])
    last_cnt_sd = LYY2Date(cnts_within_range[-1])
    last_cnt_sd = DateOffset(last_cnt_sd,
                             "{0:d}m+0J".format(GetVal(commod, "NrbyOffset")))

    dts, vls = [], []
    if smooth:
        # --- use a weighted combination of two consecutive months. weights
        #     are scaled linearly.
        rule0 = "{0:d}m+0J".format(idx)
        rule1 = "{0:d}m+0J".format(1+idx)
        for d in DateRange(first_cnt_sd, last_cnt_sd, "+1m", cal):
            mth0 = DateOffset(d, rule0, cal)
            mth1 = DateOffset(d, rule1, cal)
            csd = DateOffset(d, rule_sd, cal)
            ced = DateOffset(d, rule_ed, cal)
            try:
                cnt0 = GetVal(commod, "GetContract", Date2LYY(mth0))
                cnt1 = GetVal(commod, "GetContract", Date2LYY(mth1))
                crv0 = GetVal(cnt0, "GetCurve", csd, ced, field="close")
                crv1 = GetVal(cnt1, "GetCurve", csd, ced, field="close")
            except TsNotFound:
                continue

            m = CountBizDays(csd, ced, cal)
            n = len(crv0)

            if n != m or n != len(crv1):
                continue

            w = (np.cumsum(np.ones(n)) - 1) / (n - 1)
            mix = (1.0 - w)*crv0.values + w*crv1.values

            dts += crv0.dates
            vls += mix.tolist()
    else:
        rule = "{0:d}m+0J".format(idx)
        for d in DateRange(first_cnt_sd, last_cnt_sd, "+1m", cal):
            mth = DateOffset(d, rule, cal)
            csd = DateOffset(d, rule_sd, cal)
            ced = DateOffset(d, rule_ed, cal)
            try:
                cnt = GetVal(commod, "GetContract", Date2LYY(mth))
                crv = GetVal(cnt, "GetCurve", csd, ced, field="close")
                dts += crv.dates
                vls += crv.values.tolist()
            except TsNotFound:
                continue

    return Curve(dts, vls).crop(start, end)


# -----------------------------------------------------------------------------
def rolling_strip(
    commod, strip="Quarter", idx=1, start=None, end=None, avg_type="LAST"):
    """
    Description:
        Return the historical time series for a given rolling strip.
    Inputs:
        commod   - the name of a CommodAsset
        strip    - choose among "Quarter", "Calendar"
        idx      - the nearby index (0 is prompt strip)
        start    - the start date of the curve
        end      - the end date of the curve
        avg_type - the averaging type (see get_strip).
    Returns:
        A Curve.
    """
    if idx < 0:
        raise ValueError("Nearby index cannot "
                         "be negative: idx = {0:d}".format(idx))

    # --- if available, use default values for sd and ed
    start = start or Date.low_date()
    end = end or GetVal("Database", "MktDataDate")
    cal = GetVal(commod, "HolidayCalendar")

    # --- date rules that define the portion of the curve to be used for
    #     each contract
    rule_sd = "-1m{0:s}+1d".format(GetVal(commod, "SettDateRule"))
    rule_ed = GetVal(commod, "SettDateRule")

    if strip == "Quarter":
        rule_i = "+{0:d}m+q".format(3*idx)
        rule_f = "+{0:d}m+Q".format(3*idx)
    elif strip == "Calendar":
        rule_i = "+{0:d}y+A".format(idx)
        rule_f = "+{0:d}y+E".format(idx)
    else:
        raise RuntimeError("Unrecognized strip type {0:s}".format(strip))

    # --- for all contracts in the range, select the ones that have a
    #     non-empty time series within the required date range
    cnts_iter = (Date2LYY(d) for d in DateRange(start, end, "0J+1m", cal))
    cnts_within_range = [cnt for cnt in cnts_iter
                         if cnt in GetVal(commod, "Contracts")]

    # --- get start dates for the first and last contracts in the range
    first_cnt_sd = LYY2Date(cnts_within_range[0])
    last_cnt_sd = LYY2Date(cnts_within_range[-1])
    last_cnt_sd = DateOffset(last_cnt_sd,
                             "{0:d}m+0J".format(GetVal(commod, "NrbyOffset")))

    dts, vls = [], []
    for d in DateRange(first_cnt_sd, last_cnt_sd, "+1m", cal):
        di = DateOffset(d, rule_i, cal)
        df = DateOffset(d, rule_f, cal)
        crv = GetVal(commod, "GetStrip", di, df, avg_type)
        crv = crv.corp(DateOffset(d, rule_sd, cal),
                       DateOffset(d, rule_ed, cal))
        dts += crv.dates
        vls += crv.values.tolist()

    return Curve(dts, vls).crop(start, end)
