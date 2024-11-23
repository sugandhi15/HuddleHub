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

from ...datatypes.date import Date
from ...datatypes.curve import Curve
from ..ufo_base import UfoBase
from ..ufo_fields import DateField, SetField, CurveField

__all__ = []

DATES = [Date(2012, 8, 6), Date(2014, 11, 28)]


class ufocls(UfoBase):
    Birthday = DateField(default=Date(1977, 6, 8))
    OtherDates = SetField(default=set(DATES))
    SimpleCurve = CurveField(default=Curve(dates=DATES, values=[1, 2]))
