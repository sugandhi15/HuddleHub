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

import datetime
import dateutil.parser

__all__ = ["Date", "DateError"]

# --- constants used for conversion from/to numerical value
HOURS_PER_DAY = 24.0
MINUTES_PER_DAY = 60.0*HOURS_PER_DAY
SECONDS_PER_DAY = 60.0*MINUTES_PER_DAY
MUSECONDS_PER_DAY = 1e6*SECONDS_PER_DAY

# --- letter to month conversion
L2M = {
    "F":  1,
    "G":  2,
    "H":  3,
    "J":  4,
    "K":  5,
    "M":  6,
    "N":  7,
    "Q":  8,
    "U":  9,
    "V": 10,
    "X": 11,
    "Z": 12,
}

# --- constant used to distinguish date from datetime
DT0 = datetime.time(0, 0)


###############################################################################
class DateError(Exception):
    """
    Base class for all Date exceptions.
    """
    pass


###############################################################################
class Date(datetime.datetime):
    """
    Sublass of the datetime.datetime class implementing a few more methods.
    """
    # -------------------------------------------------------------------------
    def __str__(self):
        if self.time() == DT0:
            # --- d is a date
            return self.strftime("%d-%b-%Y")
        else:
            # --- d is a date-time
            return self.strftime("%d-%b-%Y %H:%M:%S")

    # -------------------------------------------------------------------------
    def __hash__(self):
        # --- FIXME: for some reason in python3.4 we need to redefine...
        return super().__hash__()

    # -------------------------------------------------------------------------
    #  methods for date comparisons. superclass methods are extended so that
    #  comparisons with datetime.date instances are possible

    def __eq__(self, other):
        if other.__class__ == datetime.date:
            return self.date().__eq__(other)
        else:
            return super().__eq__(other)

    def __ne__(self, other):
        if other.__class__ == datetime.date:
            return self.date().__ne__(other)
        else:
            return super().__ne__(other)

    def __lt__(self, other):
        if other.__class__ == datetime.date:
            return self.date().__lt__(other)
        else:
            return super().__lt__(other)

    def __le__(self, other):
        if other.__class__ == datetime.date:
            return self.date().__le__(other)
        else:
            return super().__le__(other)

    def __gt__(self, other):
        if other.__class__ == datetime.date:
            return self.date().__gt__(other)
        else:
            return super().__gt__(other)

    def __ge__(self, other):
        if other.__class__ == datetime.date:
            return self.date().__ge__(other)
        else:
            return super().__ge__(other)

    # -------------------------------------------------------------------------
    @property
    def ordinal(self):
        """
        Return datetime in float ordinal (currently ignores time zones).
        """
        base = float(self.toordinal())
        if self.time() != DT0:
            base += (self.hour / HOURS_PER_DAY +
                     self.minute / MINUTES_PER_DAY +
                     self.second / SECONDS_PER_DAY +
                     self.microsecond / MUSECONDS_PER_DAY)
        return base

    # -------------------------------------------------------------------------
    def is_weekday(self, weekday):
        """
        Test for a particular day in the week.
        """
        return self.weekday() is weekday

    # -------------------------------------------------------------------------
    def eod(self):
        """
        Return a new Date corresponding to the end of day for the same day.
        """
        return self.__class__(self.year, self.month, self.day, 23, 59, 59)

    # -------------------------------------------------------------------------
    #  lower and upper limits to valid dates

    @classmethod
    def low_date(cls):
        return cls(1970, 1, 1)

    @classmethod
    def high_date(cls):
        return cls(2069, 12, 31)

    # -------------------------------------------------------------------------
    #  Date constructors

    @classmethod
    def today(cls):
        return cls.fromordinal(datetime.date.today().toordinal())

    @classmethod
    def parse(cls, d, day_first=False):
        """
           Valid Dates can be created as follows:
            - from LYY string
            - from DDMMMYY string or any other format accepted by
                   dateutil.parser.parse()
            - from date/datetime object
        """
        if isinstance(d, str):
            if len(d) == 3 and d[0] in L2M:
                # --- this is a LYY string
                yy = int(d[1:])
                mm = L2M[d[0]]
                # --- years from 70 to 99 are expected to be in 1900
                yy = 2000 + yy if yy < 70 else 1900 + yy
                # --- construct date from month and year
                return cls(yy, mm, 1)
            elif len(d) == 7:
                # --- this is a date in the DDMMMYY format
                d = datetime.datetime.strptime(d, "%d%b%y")
                return cls(d.year, d.month, d.day)
            else:
                # --- use dateutil parser
                try:
                    d = dateutil.parser.parse(d, dayfirst=day_first)
                    if d.hour or d.minute or d.second or d.microsecond:
                        return cls(d.year, d.month, d.day,
                                   d.hour, d.minute, d.second, d.microsecond)
                    else:
                        return cls(d.year, d.month, d.day)
                except ValueError:
                    raise ValueError("Unrecognized "
                                     "string format: {0:s}".format(d))

        elif isinstance(d, datetime.datetime):
            # --- N.B.: datetime is a subclass of date, hence test for datetime
            #           first
            return cls(d.year, d.month, d.day,
                       d.hour, d.minute, d.second, d.microsecond)

        elif isinstance(d, datetime.date):
            return cls(d.year, d.month, d.day)

        elif isinstance(d, (int, float)):
            # --- NB: conversion is done up to the second: microseconds will be
            #         ignored
            int_d = int(d)
            dt = datetime.datetime.fromordinal(int_d)

            remainder = float(d) - int_d
            hour, remainder = divmod(24*remainder, 1)
            minute, remainder = divmod(60*remainder, 1)
            second, remainder = divmod(60*remainder, 1)

            return cls(dt.year, dt.month, dt.day,
                       int(hour), int(minute), int(second))

        else:
            raise ValueError("Unrecognized format: "
                             "{0!s}, {1!s}".format(d, type(d)))
