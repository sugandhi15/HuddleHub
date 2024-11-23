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

from calendar import SATURDAY, SUNDAY

__all__ = ["HolidayCalendar"]


###############################################################################
class HolidayCalendar(object):
    """
    Store holidays and provide testing methods.
    """
    # -------------------------------------------------------------------------
    def __init__(self, holidays=None):
        if holidays is None:
            self.holidays = set()
        else:
            self.holidays = set(holidays)

    # -------------------------------------------------------------------------
    def add(self, holidays):
        for holiday in holidays:
            self.holidays.add(holiday)

    # -------------------------------------------------------------------------
    def is_holiday(self, d):
        if d in self.holidays:
            return True
        elif d.weekday() in (SATURDAY, SUNDAY):
            # --- saturday and sundays are always recurring holidays
            return True
        return False

    # -------------------------------------------------------------------------
    def __deepcopy__(self, memo):
        clone = self.__class__.__new__(self.__class__)
        clone.holidays = self.holidays.copy()
        memo[id(self)] = clone
        return clone
