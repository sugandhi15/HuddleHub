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

from ..datatypes.date import Date, DateError, L2M
from ..datatypes.rdate import RDate
from ..datatypes.holiday_cal import HolidayCalendar
from ..database.objdb_api import GetObj

__all__ = [
    "LYY2Date",
    "Date2LYY",
    "Date2QQYY",
    "CalcTerm",
    "DateOffset",
    "DateRange",
    "CountBizDays",
]

# --- auxiliary local variables (not exported)
M2L = dict(zip(L2M.values(), L2M.keys()))
QUARTER_BY_MTH = [1, 1, 1, 2, 2, 2, 3, 3, 3, 4, 4, 4]


# -----------------------------------------------------------------------------
def LYY2Date(lyy):
    """
    Description:
        Convert a Nymex LYY string (used for futures contracts as in F09) to
        a Date. The LYY string is assumed to correspond to the first day in the
        corresponding month.
    Inputs:
        lyy - a string defining a valid Nymex future contract.
    Returns:
        A Date.
    """
    try:
        m = L2M[lyy[0]]
        y = int(lyy[1:])
        y = 2000 + y if y < 70 else 1900 + y
        return Date(y, m, 1)
    except KeyError:
        raise DateError("Unrecognized LYY string: {0:s}".format(lyy))


# -----------------------------------------------------------------------------
def Date2LYY(date):
    """
    Description:
        Convert a Date to a Nymex LYY string (used for futures contracts
        as in F09). Conversion is done ignoring the actual day in the month.
    Inputs:
        date - a Date for which the LYY Nymex future contract is returned.
    Returns:
        A string with the LYY code.
    """
    if date < Date.low_date() or date > Date.high_date():
        raise DateError("Date outside valid range: {0:s}".format(date))

    m = date.month
    y = date.year
    yy = y - 2000 if y > 1999 else y - 1900

    return "{0:1s}{1:02d}".format(M2L[m], yy)


# -----------------------------------------------------------------------------
def Date2QQYY(date):
    """
    Description:
        Convert a Date to a string for the corresponding quarter (as in Q311).
        Conversion is done ignoring the actual day in the quarter.
    Inputs:
        date - a Date for which the corresponding quarter is returned.
    Returns:
        A string with the QQYY code.
    """
    if date < Date.low_date() or date > Date.high_date():
        raise DateError("Date outside valid range: {0:s}".format(date))

    m = date.month - 1
    y = date.year
    yy = y - 2000 if y > 1999 else y - 1900

    return "Q{0:1d}{1:02d}".format(QUARTER_BY_MTH[m], yy)


# -----------------------------------------------------------------------------
def CalcTerm(start, end, base=365):
    """
    Description:
        Return the number of years between start and end date assuming that
        each year has a number of days as specified by base. Term is negative
        if start > end.
    Inputs:
        start - the initial date of the term
        end   - the final   date of the term
        base  - number of days in a calendar year
    Returns:
        A float.
    """
    return (end - start).days / float(base)


# -----------------------------------------------------------------------------
def DateOffset(date, rule, calendar=None):
    """
    Description:
        Applies the specified rule (a string, as defined below) to the
        specified date to obtain a new shifted date.
    Inputs:
        date     - date on which the date-rule is to be applied
        rule     - a tag specifying shift relative to input date
        calendar - a holiday calendar name used to identify business days
    Rule definitions:
        d = add calendar day
        b = add business day
        w = add calendar week
        m = add calendar month
        y = add calendar year
        c = go to the required day in the month
        e = go to end of month (ignores num)
        J = go to first calendar day of month (ignores num)
        M = go to closest Monday as specified by num
        W = go to closest Wednesday as specified by num
        F = go to closest Friday as specified by num
        q = go to beginning of the quarter (ignores num)
        Q = go to end of the quarter (ignores num)
        A = go to beginning of the year (ignores num)
        E = go to end of the year (ignores num)
    Returns:
        A Date.
    Examples:
        EndOfMonth = DateOffset(Date.today(), "+e")
        FirstBizDayOf2000 = DateOffset(Date(2000, 1, 1), "+b")
    """
    if calendar is None or isinstance(calendar, HolidayCalendar):
        pass
    elif isinstance(calendar, str):
        calendar = GetObj(calendar)
    else:
        raise ValueError("calendar must be either a string or "
                         "an instance of HolidayCalendar (a {0:s} "
                         "was passed instead).".format(type(calendar)))

    return date + RDate(rule, calendar)


# -----------------------------------------------------------------------------
def DateRange(start, end, rule, calendar=None):
    """
    Description:
        Iterator that yields a series of dates between start date and
        end date according to an increment rule (start date is included).
    Inputs:
        start    - the first date in the range, included
        end      - the last  date in the range, included or not, depending on
                   the rule
        rule     - a date rule (see RDate)
        calendar - a holiday calendar used to identify business days
    Yields:
        A range of Dates.
    """
    if calendar is None or isinstance(calendar, HolidayCalendar):
        pass
    elif isinstance(calendar, str):
        calendar = GetObj(calendar)
    else:
        raise ValueError("calendar must be either a string or "
                         "an instance of HolidayCalendar (a {0:s} "
                         "was passed instead).".format(type(calendar)))

    d = start
    rd = RDate(rule, calendar)
    while d <= end:
        yield d
        d = d + rd


# -----------------------------------------------------------------------------
def CountBizDays(start, end, calendar=None):
    """
    Description:
        Return the number of business days between start and end date according
        to the holiday calendar.
        NB: if start date == end date this function will return 1.
    Inputs:
        start    - the initial date of the range
        end      - the last  date in the range
        calendar - a holiday calendar used to identify business days
    Returns:
        An integer.
    """
    if calendar is None or isinstance(calendar, HolidayCalendar):
        pass
    elif isinstance(calendar, str):
        calendar = GetObj(calendar)
    else:
        raise ValueError("calendar must be either a string or "
                         "an instance of HolidayCalendar (a {0:s} "
                         "was passed instead).".format(type(calendar)))

    # --- first push start date forward to the nearest business day
    start = start + RDate("+0b", calendar)

    # --- then sum all business days in the range
    return sum((1 for d in DateRange(start, end, "+1b", calendar)))
