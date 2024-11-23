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

from onyx.core import Date, UfoBase, RetainedFactory

__all__ = ["Database"]


###############################################################################
class Database(UfoBase):
    # -------------------------------------------------------------------------
    @RetainedFactory()
    def PricingDate(self, graph):
        return Date.today()

    # -------------------------------------------------------------------------
    @RetainedFactory()
    def MktDataDate(self, graph):
        # --- defaults to PricingDate
        return graph(self, "PricingDate")

    # -------------------------------------------------------------------------
    @RetainedFactory()
    def PositionsDate(self, graph):
        """
        Used to retrive children by book.
        """
        # --- defaults to PricingDate
        return graph(self, "PricingDate")

    # -------------------------------------------------------------------------
    @RetainedFactory()
    def ProcDate(self, graph):
        return Date.today()

    # -------------------------------------------------------------------------
    @RetainedFactory()
    def ReportDate(self, graph):
        return Date.today()

    # -------------------------------------------------------------------------
    @RetainedFactory()
    def ForceStrict(self, graph):
        """
        Change to enforce retrival of a specific dated object or knot.
        """
        return False

    # -------------------------------------------------------------------------
    @RetainedFactory()
    def ArchivedOverwritable(self, graph):
        """
        Change to allow overwriting archived objects.
        """
        return False

    # -------------------------------------------------------------------------
    @RetainedFactory()
    def TradesDeletable(self, graph):
        """
        Change to allow deleting trades.
        """
        return False


# -----------------------------------------------------------------------------
def prepare_for_test():
    from onyx.core import AddIfMissing
    AddIfMissing(Database(Name="Database"))
