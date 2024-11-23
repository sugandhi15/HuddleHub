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

from onyx.core import GraphNodeDescriptor, Archivable
from onyx.core import FloatField
from onyx.core import MktIndirectionFactory, EnforceArchivableEntitlements

__all__ = ["PriceFix"]


###############################################################################
@EnforceArchivableEntitlements("Database", "ArchivedOverwritable")
class PriceFix(Archivable):
    """
    Class used to represent price fixes (marks or settlement values).
    """
    # -------------------------------------------------------------------------
    @MktIndirectionFactory(FloatField)
    def Price(self, graph):
        pass

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor("PropSubGraph")
    def LastKnot(self, graph, date=None):
        date = date or graph("Database", "MktDataDate")
        return self.get_dated("Price", date, strict=False)

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor("PropSubGraph")
    def PrcFixCurve(self, graph, start=None, end=None):
        return self.get_history("Price", start, end)


# -----------------------------------------------------------------------------
def prepare_for_test():
    from . import ufo_database
    ufo_database.prepare_for_test()
