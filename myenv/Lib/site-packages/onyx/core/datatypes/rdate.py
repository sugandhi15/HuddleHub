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

from .date import Date
from .holiday_cal import HolidayCalendar

from dateutil.relativedelta import relativedelta, MO, WE, FR

import datetime
import re

__all__ = ["RDate"]

QUARTER_FIRST_MTH = [1, 1, 1, 4, 4, 4, 7, 7, 7, 10, 10, 10]

SPLITTER = re.compile("([\+,\-]\d*\w+)")
OPERANDS = {"+", "-"}


###############################################################################
class RDate(object):
    """
    A date shift object that can be added to Dates to generate shifted dates.
    """
    __slots__ = ("date_rule", "calendar")

    # -------------------------------------------------------------------------
    def __init__(self, date_rule, calendar=None):
        """
        Inputs:
            date_rule - a string specifying relative shift (see below for valid
                        date rules).
            calendar  - a holiday calendar used to identify business days
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
        """
        # --- use parent class setattr because RDate is implemented as an
        #     immutable class
        super().__setattr__("date_rule", date_rule)
        super().__setattr__("calendar", calendar or HolidayCalendar())

    # -------------------------------------------------------------------------
    def __setattr__(self, attr, value):
        raise AttributeError("attribute '{0:s}' of RDate is not settable "
                             "as RDate is an immutable class".format(attr))

    # -------------------------------------------------------------------------
    def apply_rule(self, d):
        # --- rule processing. If no operator is defined assume it's "+"
        if self.date_rule[0] in OPERANDS:
            atomic = SPLITTER.split(self.date_rule)[1::2]
        else:
            atomic = SPLITTER.split("+" + self.date_rule)[1::2]

        # --- iteratively apply each atomic rule
        for rule in atomic:
            op = rule[0:-1]
            r = rule[-1]
            if op in OPERANDS:
                op += "1"
            # --- look for the proper rule to apply
            if r == "d":
                d += relativedelta(days=int(op))
            elif r == "b":
                nb = int(op[1:])
                op1 = int(op[0] + "1")
                if nb == 0 and self.calendar.is_holiday(d):
                    # --- go to the next (or previous) business day only if
                    #     d is not already a business day
                    nb = 1
                for i in range(nb):
                    d += relativedelta(days=op1)
                    while self.calendar.is_holiday(d):
                        d += relativedelta(days=op1)
            elif r == "w":
                d += relativedelta(weeks=int(op))
            elif r == "m":
                d += relativedelta(months=int(op))
            elif r == "y":
                d += relativedelta(years=int(op))
            elif r == "c":
                d += relativedelta(day=int(op))
            elif r == "e":
                d += relativedelta(day=31)
            elif r == "J":
                d += relativedelta(day=1)
            elif r == "M":
                d += relativedelta(weekday=MO(int(op)))
            elif r == "W":
                d += relativedelta(weekday=WE(int(op)))
            elif r == "F":
                d += relativedelta(weekday=FR(int(op)))
            elif r == "q":
                d = d.replace(day=1, month=QUARTER_FIRST_MTH[d.month-1])
            elif r == "Q":
                d = d.replace(day=1, month=QUARTER_FIRST_MTH[d.month-1]+2)
                d += relativedelta(day=31)
            elif r == "A":
                d = d.replace(day=1, month=1)
            elif r == "E":
                d = d.replace(day=31, month=12)
            else:
                raise NameError("Atomic rule {0:s} is unknown. "
                                "Full rule is {1:s}".format(r, rule))

        # --- conversion to Date is needed here because applying a
        #     relativedelta to a Date returns a datetime object
        return Date.parse(d)

    # -------------------------------------------------------------------------
    #  relative date algebra
    def __radd__(self, date):
        # --- check against the supercalss datetime.datetime
        if not isinstance(date, (datetime.date, datetime.datetime)):
            raise ValueError("RDate can only be applied to a Date. "
                             "{0!s} was passed instead".format(date.__class__))
        return self.apply_rule(date)
