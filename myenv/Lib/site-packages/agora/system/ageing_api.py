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

from onyx.core import GetObj, GetVal, ObjDbTransaction
from .transaction_api import TransactionsBy, AgeTransaction

import logging

__all__ = ["age_portfolio"]

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
def age_portfolio(port):
    """
    Description:
        Age postions for a given portfolio as of Database->PositionsDate.
    Inputs:
        port - the portfolio whose positions we want to age
    """
    books = GetVal(port, "Books")
    kids = set.union(*[set(GetVal(book, "Children").keys()) for book in books])
    pos_date = GetVal("Database", "PositionsDate")

    maybe_more_to_do = False

    for kid in kids:
        try:
            ntd = GetVal(kid, "NextTransactionDate")
        except AttributeError:
            continue

        if ntd == pos_date:
            # --- lookup affected transactions
            transactions = set()
            for book in books:
                trs_by_book = TransactionsBy(security=kid, book=book)
                transactions.update(set(trs_by_book))

            if len(transactions):
                event = GetVal(kid, "ExpectedTransaction")
                secs = GetVal(kid, "ExpectedSecurities", event)
                logger.debug(kid, event, secs)
                logger.debug(sorted(transactions))

                tag = "Aging of {0:s}".format(kid)
                with ObjDbTransaction(tag, level="SERIALIZABLE"):
                    for transaction in sorted(transactions):
                        AgeTransaction(GetObj(transaction), pos_date)

                maybe_more_to_do = True

    return maybe_more_to_do
