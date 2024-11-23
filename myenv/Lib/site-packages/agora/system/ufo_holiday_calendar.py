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

from onyx.core import UfoBase, SetField
import onyx.core.datatypes.holiday_cal as onyx_hc

__all__ = ["HolidayCalendar"]


###############################################################################
class HolidayCalendar(UfoBase, onyx_hc.HolidayCalendar):
    """
    Class used to store holidays.
    """
    Holidays = SetField(default=set())

    # -------------------------------------------------------------------------
    @property
    def holidays(self):
        return self.Holidays


# -----------------------------------------------------------------------------
def prepare_for_test():
    from onyx.core import AddIfMissing
    AddIfMissing(HolidayCalendar(Name="USD_CAL"))
    AddIfMissing(HolidayCalendar(Name="EUR_CAL"))
    AddIfMissing(HolidayCalendar(Name="GBP_CAL"))
