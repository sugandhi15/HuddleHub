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

from onyx.core import Interpolate, CalcTerm
from onyx.core import Archivable, GraphNodeDescriptor
from onyx.core import ReferenceField, CurveField
from onyx.core import MktIndirectionFactory, EnforceArchivableEntitlements

import math

__all__ = ["Currency"]


###############################################################################
@EnforceArchivableEntitlements("Database", "ArchivedOverwritable")
class Currency(Archivable):
    """
    Class used to represent a currency and its discount curve.
    """
    HolidayCalendar = ReferenceField(obj_type="HolidayCalendar")

    # -------------------------------------------------------------------------
    @MktIndirectionFactory(CurveField)
    def ZeroCurve(self, graph):
        pass

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor("Callable")
    def DiscountFactor(self, graph, from_date, to_date):
        zero_crv = graph(self, "ZeroCurve")
        ref_date = graph("Database", "MktDataDate")
        rate_from = Interpolate(zero_crv, from_date, method="Linear")
        term_from = CalcTerm(ref_date, from_date)
        rate_to = Interpolate(zero_crv, to_date, method="Linear")
        term_to = CalcTerm(ref_date, to_date)
        return math.exp(-term_from*rate_from)*math.exp(term_to*rate_to)


# -----------------------------------------------------------------------------
def prepare_for_test():
    from onyx.core import Curve, Date, AddIfMissing, EvalBlock
    from . import ufo_database
    from . import ufo_holiday_calendar

    ufo_database.prepare_for_test()
    ufo_holiday_calendar.prepare_for_test()

    ccys = []
    ccys.append(AddIfMissing(Currency(Name="USD", HolidayCalendar="USD_CAL")))
    ccys.append(AddIfMissing(Currency(Name="EUR", HolidayCalendar="EUR_CAL")))
    ccys.append(AddIfMissing(Currency(Name="GBP", HolidayCalendar="GBP_CAL")))

    zero_curve = Curve([Date.low_date()], [0.0])

    with EvalBlock() as eb:
        eb.change_value("Database", "ArchivedOverwritable", True)
        for ccy in ccys:
            ccy.set_dated("ZeroCurve", Date.today(), zero_curve)
