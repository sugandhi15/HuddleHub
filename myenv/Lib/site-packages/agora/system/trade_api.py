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

from onyx.core import Date, Structure, DateOffset
from onyx.core import AddObj, GetObj, UpdateObj, DelObj, PurgeObj, ObjNotFound
from onyx.core import CreateInMemory, ObjDbTransaction, ObjDbQuery
from onyx.core import GraphNodeDescriptor, GetVal, SetVal, UfoBase
from onyx.core import ReferenceField
from onyx.core import FloatField, DateField, SelectField, BoolField
from onyx.core import unique_id

from .tradable_api import AddByInference
from .transaction_api import Transaction, TransactionsBy, TransactionWarning
from .transaction_api import CommitTransaction, DeleteTransaction
from .ufo_forward_cash import ForwardCash
from .risk_decorators import WithRiskMethods

import random
import logging

__all__ = [
    "Trade",
    "TradeError",
    "TradeWarning",
    "CommitTrade",
    "DeleteTrade",
    "ChildrenByBook",
    "TradesBy",
]

logger = logging.getLogger(__name__)

# --- templates for common queries

TRANSACTIONS_STORED = """
SELECT Event, Transaction
FROM (
    SELECT Event, Transaction
    FROM PosEffects
    WHERE Trade=%s AND Book=%s
) tab1 INNER JOIN LATERAL (
    SELECT FROM Objects
    WHERE Name=Transaction AND Data->>'Marker'='HEAD'
    LIMIT 1
) tab2 ON true;
"""

CHILDREN_BY_BOOK = """
SELECT Unit, SUM(Qty) AS tot_qty
FROM PosEffects WHERE Book=%s AND {0:s}<=%s
GROUP BY Unit;"""


###############################################################################
class TradeError(Exception):
    pass


###############################################################################
class TradeWarning(Warning):
    pass


###############################################################################
@WithRiskMethods
class Trade(UfoBase):
    """
    Class used to represent trade objects in the system and their effects
    on positions.
    """
    SecurityTraded = ReferenceField(obj_type="TradableObj")
    TradeDate = DateField()
    TradeType = SelectField(default="Buy", options=["Buy", "Sell"])
    Quantity = FloatField(default=0.0, positive=True)
    UnitPrice = FloatField(default=0.0, positive=True)
    PaymentUnit = ReferenceField(obj_type="Currency")
    SettlementDate = DateField()
    Party = ReferenceField(obj_type="Book")
    Counterparty = ReferenceField(obj_type="Book")
    Trader = ReferenceField(obj_type="Trader")
    Broker = ReferenceField(obj_type="Broker")
    BrokerageFee = FloatField(default=0.0, positive=True)
    OtherCosts = FloatField(default=0.0, positive=True)
    Deleted = BoolField(default=False)

    # -------------------------------------------------------------------------
    def __post_init__(self):
        # --- set object's name if not set already
        self.Name = self.Name or Trade.random_name()

        # --- set default values
        self.PaymentUnit = self.PaymentUnit or "USD"

        if self.SettlementDate is None:
            cal = GetVal(self.PaymentUnit, "HolidayCalendar")
            self.SettlementDate = DateOffset(self.TradeDate, "+2b", cal)

        self.Broker = self.Broker or "BROKER-SUSPENSE"

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def Denominated(self, graph):
        """
        A trade is denominated in the PaymentUnit currency.
        """
        return graph(self, "PaymentUnit")

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def TradeInfo(self, graph):
        """
        Return a dictionary {attribute: value}, including all the stored
        attributes.
        """
        attrs = sorted(self._json_fields)
        return dict(zip(attrs, [graph(self, attr) for attr in attrs]))

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def TransactionsCalc(self, graph):
        sec = graph(self, "SecurityTraded")
        trd_date = graph(self, "TradeDate")
        trd_type = graph(self, "TradeType")
        trd_qty = graph(self, "Quantity")
        qty = trd_qty*(1.0 if trd_type == "Buy" else -1.0)
        ccy = graph(self, "PaymentUnit")
        prc = graph(self, "UnitPrice")
        sett_dt = graph(self, "SettlementDate")
        cash = ForwardCash(Currency=ccy, PaymentDate=sett_dt)
        cash = AddByInference(cash, in_memory=True)

        return {
            "BuySell": CreateInMemory(Transaction(
                TransactionDate=trd_date,
                SecurityTraded=sec,
                Quantity=qty,
                Party=graph(self, "Party"),
                Counterparty=graph(self, "Counterparty"),
                Event="BuySell",
                Trade=self.Name
            )),
            "Payment": CreateInMemory(Transaction(
                TransactionDate=trd_date,
                SecurityTraded=cash.Name,
                Quantity=-qty*prc,
                Party=graph(self, "Party"),
                Counterparty=graph(self, "Counterparty"),
                Event="Payment",
                Trade=self.Name
            )),
            "Costs": CreateInMemory(Transaction(
                TransactionDate=trd_date,
                SecurityTraded=cash.Name,
                Quantity=-graph(self, "OtherCosts"),
                Party=graph(self, "Party"),
                Counterparty="TAXNCOSTS",
                Event="Costs",
                Trade=self.Name
            )),
            "Fees": CreateInMemory(Transaction(
                TransactionDate=trd_date,
                SecurityTraded=cash.Name,
                Quantity=-graph(self, "BrokerageFee"),
                Party=graph(self, "Party"),
                Counterparty=graph(self, "Broker"),
                Event="Fees",
                Trade=self.Name
            ))
        }

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def Leaves(self, graph):
        leaves = Structure()
        for transaction in graph(self, "TransactionsCalc").values():
            leaves += graph(transaction, "Leaves")
        return leaves

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def MktValUSD(self, graph):
        mtm = 0.0
        for leaf, qty in graph(self, "Leaves").items():
            mtm += qty*graph(leaf, "MktValUSD")
        return mtm

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def MktVal(self, graph):
        raise NotImplementedError()

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def PositionEffects(self, graph):
        pos_effects = []
        for transaction in self.transactions_stored().values():
            pos_effects += graph(transaction, "PositionEffects")
        return pos_effects

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def PositionEffectsCalc(self, graph):
        pos_effects = []
        for transaction in graph(self, "TransactionsCalc").values():
            pos_effects += graph(transaction, "PositionEffects")
        return pos_effects

    # -------------------------------------------------------------------------
    def delete(self):
        if GetVal("Database", "TradesDeletable"):
            transactions = TransactionsBy(trade=self.Name, head_only=False)
            with ObjDbTransaction("Delete Children", "SERIALIZABLE"):
                for transaction in transactions:
                    DelObj(transaction)
        else:
            raise TradeError("Trying to delete a trade without permission")

    # -------------------------------------------------------------------------
    # NB: this needs to be a standard method to make sure that there is never
    #     any caching on trade.Name and trade.Party (for clarity sake we
    #     refrain from making this a property).
    def transactions_stored(self):
        rows = ObjDbQuery(
            TRANSACTIONS_STORED, (self.Name, self.Party), attr="fetchall")

        stored = {}
        for row in rows:
            try:
                stored[row.event].append(row.transaction)
            except AttributeError:
                stored[row.event] = [stored[row.event], row.transaction]
            except KeyError:
                stored[row.event] = row.transaction

        return stored

    # -------------------------------------------------------------------------
    @classmethod
    def random_name(cls):
        return "TmpTrd-{0:>07d}".format(random.randrange(0, 10000000, 1))

    # -------------------------------------------------------------------------
    @classmethod
    def format_name(cls, date, trd_id):
        return "TRD {0:s} {1:s}".format(date.strftime("%Y%m%d"), trd_id)


# -----------------------------------------------------------------------------
def PreTradeCompliance(trade):
    """
    Description:
        This function is ment to raise an exception for any violation
        of pre-trade compliance checks.
    Inpots:
        trade - the trade to be checked
    Returns:
        None.
    """
    # --- price validation
    GetVal(trade, "MktValUSD")

    # --- basic risk validation
    GetVal(trade, "Deltas")


# -------------------------------------------------------------------------
def CommitTrade(trade, name=None):
    """
    Description:
        Create/amend a trade by creting/amending the associated transactions.
    Inputs:
        trade - the instance of Trade to commit
        name  - an optional trade name
    Returns:
        A Trade instance.
    """
    # --- clone security traded: AddByInference is needed to generate the
    #     proper ImpliedName.
    sec = AddByInference(GetObj(trade.SecurityTraded).clone())

    # --- get trade info before reloading the trade
    info = GetVal(trade, "TradeInfo")
    info["SecurityTraded"] = sec.Name

    try:
        # --- reload security: this is needed to avoid basing decisions on
        #     attribute values that might have been set in memory
        trade = GetObj(trade.Name, refresh=True)

    except ObjNotFound:
        # --- trade not found, proceed as new trade
        trade.SecurityTraded = sec.Name

        # --- create trade and overwrite a few stored attributes
        name = name or trade.format_name(Date.today(), unique_id(8))
        trade = CreateInMemory(trade.clone(Name=name))

        PreTradeCompliance(trade)

        logger.info("creating new trade {0:s}".format(trade.Name))

        calculated = GetVal(trade, "TransactionsCalc")
        with ObjDbTransaction("Trade Insert", level="SERIALIZABLE"):
            for transaction in calculated.values():
                CommitTransaction(transaction)
            AddObj(trade)

    else:
        # --- need to amend?
        same = True
        for attr, value in info.items():
            same = (value == getattr(trade, attr))
            if not same:
                break
        if same:
            raise TradeWarning("{0:s}, TradeCommit found nothing to "
                               "amend on existing trade.".format(trade.Name))

        logger.info("amending trade {0:s}".format(trade.Name))

        # --- we fetch stored transactions before overwriting the stored
        #     attributes of the trade (this is essential since amending the
        #     Party attribute would prevent fetching the correct stored
        #     transactions).
        stored = trade.transactions_stored()  # this queries the backend

        if not len(stored):
            raise TradeError("{0:s}, error loading "
                             "transactions stored.".format(trade.Name))

        # --- overwrite trade stored attributes with new ones
        for attr, value in info.items():
            SetVal(trade, attr, value)

        PreTradeCompliance(trade)

        calculated = GetVal(trade, "TransactionsCalc")
        with ObjDbTransaction("Trade Amend", level="SERIALIZABLE"):
            UpdateObj(trade.Name)
            for event, transaction in calculated.items():
                # --- overwrite the name of the calculated transaction with
                #     that of the stored one
                try:
                    stored_name = stored[event]
                except KeyError:
                    raise TradeError("{0:s}, trying to amend a trade with "
                                     "an aged transaction.".format(trade.Name))
                try:
                    CommitTransaction(transaction, stored_name)
                except TransactionWarning as warning:
                    # --- ignore warnings
                    logger.info(warning)

    return trade


# -------------------------------------------------------------------------
def DeleteTrade(trade_name):
    """
    Description:
        Delete a trade, by deleting all associated transactions and marking it
        as deleted.
    Inputs:
        trade_name - the name of the trade to delete
    Returns:
        None.
    """
    # --- reload security: this is needed to avoid basing decisions on
    #     attribute values that might have been set in memory
    trade = GetObj(trade_name, refresh=True)

    with ObjDbTransaction("Trade Delete", level="SERIALIZABLE"):
        if trade.TimeCreated >= Date.today():
            # --- same day delete: get rid of the trade and of all associated
            #     transactions
            PurgeObj(trade)
        else:
            trade.Deleted = True
            UpdateObj(trade)
            for transaction in trade.transactions_stored().values():
                if isinstance(transaction, list):
                    for sub_transaction in transaction:
                        DeleteTransaction(sub_transaction)
                else:
                    DeleteTransaction(transaction)


# -----------------------------------------------------------------------------
def ChildrenByBook(book, pos_date, by_time_created=False):
    """
    Description:
        Return all children of a given book as of a given date.
    Inputs:
        book            - the book
        pos_date        - the positions date
        by_time_created - if True, amendments are reflected on the date they
                          were booked, not on the date of the original trade.
    Returns:
        A Structure.
    """
    if by_time_created:
        query = CHILDREN_BY_BOOK.format("TimeCreated")
    else:
        query = CHILDREN_BY_BOOK.format("TradeDate")

    rows = ObjDbQuery(query, parms=(book, pos_date.eod()), attr="fetchall")
    children = Structure()
    for row in rows:
        # --- exclude children with zero quantity
        if row.tot_qty != 0.0:
            children[row.unit] = row.tot_qty

    return children


# -----------------------------------------------------------------------------
def TradesBy(book=None, trader=None,
             security=None, sectype=None, date_range=None):
    """
    Description:
        Return all trades matching the given criteria.
    Inputs:
        book       - a given book
        trader     - a given trader
        security   - a given security
        sectype    - a given security type
        date_range - a tuple of start and end date
    Returns:
        A list of trade names.
    """
    extquery = []
    criteria = []

    if book is not None:
        extquery.append("Book=%s")
        criteria.append(book)

    if security is not None:
        extquery.append("Unit=%s")
        criteria.append(security)

    if sectype is not None:
        extquery.append("UnitType=%s")
        criteria.append(sectype)

    if date_range is not None:
        extquery.append("TradeDate BETWEEN %s AND %s")
        criteria.append(date_range[0])
        criteria.append(date_range[1])

    if len(criteria):
        query = ("SELECT DISTINCT(Trade) "
                 "FROM PosEffects WHERE {0:s};").format(" AND ".join(extquery))
        rows = ObjDbQuery(query, parms=criteria, attr="fetchall")

    else:
        query = "SELECT DISTINCT(Trade) FROM PosEffects;"
        rows = ObjDbQuery(query, attr="fetchall")

    # --- postprocessing filters
    if trader is not None:
        # --- Trader is not part of PosEffects table: run filter as a
        #     post-process
        def post_proc(trade_name):
            trade = GetObj(trade_name)
            return trade.Trader == trader and not trade.Deleted
    else:
        def post_proc(trade_name):
            trade = GetObj(trade_name)
            return not trade.Deleted

    return [row.trade for row in rows if post_proc(row.trade)]


# -----------------------------------------------------------------------------
def prepare_for_test():
    from onyx.core import Date, AddIfMissing

    from . import ufo_book
    from . import ufo_trader
    from . import ufo_broker
    from . import ufo_forward_cash
    from ..equity import ufo_equity_cash
    from ..equity import ufo_equity_cfd

    books = ufo_book.prepare_for_test()
    traders = ufo_trader.prepare_for_test()
    brokers = ufo_broker.prepare_for_test()
    eqcash = ufo_equity_cash.prepare_for_test()
    eqcfds = ufo_equity_cfd.prepare_for_test()

    ufo_forward_cash.prepare_for_test()

    trades = [
        # --- this is a cash trade
        {
            "SecurityTraded": eqcash[0],
            "TradeDate": Date.today(),
            "TradeType": "Sell",
            "Quantity": 1000.0,
            "Party": books[0],
            "Counterparty": books[2],
            "Trader": traders[0],
            "Broker": brokers[0],
            "UnitPrice": 9.1*1.5/1.15,
            "PaymentUnit": "EUR",
        },
        # --- this is a CFD trade
        {
            "SecurityTraded": eqcfds[0],
            "TradeDate": Date.today(),
            "TradeType": "Sell",
            "Quantity": 1000.0,
            "Party": books[0],
            "Counterparty": books[2],
            "Trader": traders[0],
            "Broker": brokers[0],
        }
    ]
    trades = [AddIfMissing(Trade(**trade_info), True) for trade_info in trades]

    return [trade.Name for trade in trades]
