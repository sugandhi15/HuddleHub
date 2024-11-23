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

from onyx.core import Date, AddObj, GetObj, UpdateObj
from onyx.core import ObjDbQuery, ObjDbTransaction, ObjNotFound
from onyx.core import GraphNodeDescriptor
from onyx.core import CreateInMemory, UfoBase, GetVal, SetVal, PurgeObj
from onyx.core import DateField, ReferenceField, FloatField, StringField
from onyx.core import SelectField, unique_id

from .tradable_api import AddByInference

import collections
import random
import logging

__all__ = [
    "Transaction",
    "TransactionError",
    "TransactionWarning",
    "CommitTransaction",
    "RollbackTransaction",
    "DeleteTransaction",
    "AgeTransaction",
    "TransactionsBy"
]

logger = logging.getLogger(__name__)

# --- templates for common queries

QUERY_INSERT_POSEFF = """
INSERT INTO PosEffects VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s);"""

QUERY_DELETE_POSEFF = "DELETE FROM PosEffects WHERE Transaction=%s;"


# -----------------------------------------------------------------------------
def create_poseffects_table():
    with ObjDbTransaction("PosEffects Table Create"):
        ObjDbQuery("""
CREATE TABLE PosEffects (
  TradeDate   date NOT NULL,
  TimeCreated timestamp with time zone NOT NULL,
  Book        character varying(64) NOT NULL,
  Qty         double precision NOT NULL,
  Unit        character varying(64) NOT NULL,
  UnitType    character varying(64) NOT NULL,
  Transaction character varying(64) NOT NULL,
  Event       character varying(64) NOT NULL,
  Trade       character varying(64) NOT NULL );

CREATE INDEX pos_by_trade_date ON PosEffects (TradeDate);
CREATE INDEX pos_by_time_created ON PosEffects (TimeCreated);
CREATE INDEX pos_by_book ON PosEffects (Book);
CREATE INDEX pos_by_trade ON PosEffects (Trade);

CREATE OR REPLACE FUNCTION notify_trigger() RETURNS trigger AS $$
DECLARE
BEGIN
    IF (TG_OP = 'DELETE') THEN
        PERFORM pg_notify(TG_TABLE_NAME, OLD.Book);
        RETURN OLD;
    ELSIF (TG_OP = 'UPDATE') THEN
        PERFORM pg_notify(TG_TABLE_NAME, OLD.Book);
        PERFORM pg_notify(TG_TABLE_NAME, NEW.Book);
        RETURN NEW;
    ELSIF (TG_OP = 'INSERT') THEN
        PERFORM pg_notify(TG_TABLE_NAME, NEW.Book);
        RETURN NEW;
    END IF;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER PosEffects_Notify
    AFTER INSERT OR UPDATE OR DELETE ON PosEffects
    FOR EACH ROW EXECUTE PROCEDURE notify_trigger();""")


###############################################################################
class TransactionError(Exception):
    pass


###############################################################################
class TransactionWarning(Warning):
    pass


###############################################################################
Position = collections.namedtuple(
    "Position", "TradeDate Book Qty Unit UnitType Name Event Trade")


###############################################################################
class Transaction(UfoBase):
    """
    Transactions represent trading events:
    - Transactions are the only means to change positions. Positions effects
      associated to each transaction are two sided and must always sume to
      zero.
    - Each transaction refers to one and only one trade.
    - Each transaction has marker to define the its type and a pointer to the
      previous transaction in the chain.
    - Each transaction has marker to indentify the event that gave rise to its
      creation.
    """
    TransactionDate = DateField()
    SecurityTraded = ReferenceField(obj_type="TradableObj")
    Quantity = FloatField(default=0.0)
    Party = ReferenceField(obj_type="Book")
    Counterparty = ReferenceField(obj_type="Book")
    Trade = ReferenceField(obj_type="Trade")
    PrevTransaction = ReferenceField(obj_type="Transaction")
    Event = StringField()
    Marker = SelectField(options=[
        "HEAD", "AMENDED", "AGED", "BACKOUT", "ROLLEDBACK", "DELETED"])

    # -------------------------------------------------------------------------
    def __post_init__(self):
        self.Name = self.Name or Transaction.random_name()

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def Denominated(self, graph):
        return graph(graph(self, "SecurityTraded"), "Denominated")

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def Trader(self, graph):
        return graph(graph(self, "Trade"), "Trader")

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def TransactionInfo(self, graph):
        """
        Return a dictionary {attribute: value}, including only the stored
        attributes that can be altered by a transaction amendment.
        """
        attrs = self._json_fields.copy()
        attrs = sorted(attrs.difference({"Trade", "Event", "Marker"}))
        return dict(zip(attrs, [graph(self, attr) for attr in attrs]))

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def Leaves(self, graph):
        qty = graph(self, "Quantity")
        sec = graph(self, "SecurityTraded")
        return qty*graph(sec, "Leaves")

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
        ccy = graph(self, "Denominated")
        spot_fx = graph("{0:3s}/USD".format(ccy), "Spot")
        return graph(self, "MktValUSD") / spot_fx

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def PositionEffects(self, graph):
        sec = graph(self, "SecurityTraded")
        qty = graph(self, "Quantity")
        date = graph(self, "TransactionDate")
        name = graph(self, "Name")
        event = graph(self, "Event")
        trade = graph(self, "Trade")
        cpty1 = graph(self, "Party")
        cpty2 = graph(self, "Counterparty")

        pos_effects = [
            Position(date, cpty1, qty,
                     sec, graph(sec, "ObjType"), name, event, trade),
            Position(date, cpty2, -qty,
                     sec, graph(sec, "ObjType"), name, event, trade)
        ]

        return pos_effects

    # -------------------------------------------------------------------------
    def delete(self):
        if GetVal("Database", "TradesDeletable"):
            query = """DELETE FROM PosEffects WHERE Transaction=%s;
                       NOTIFY PosEffects, %s; NOTIFY PosEffects, %s;"""
            ObjDbQuery(query, parms=(self.Name, self.Party, self.Counterparty))
        else:
            raise TransactionError(
                "Trying to delete a transaction without permission")

    # -------------------------------------------------------------------------
    @classmethod
    def random_name(cls):
        return "TmpTrs-{0:>07d}".format(random.randrange(0, 10000000, 1))

    # -------------------------------------------------------------------------
    @classmethod
    def format_name(cls, date, trd_id):
        return "TRS {0:s} {1:s}".format(date.strftime("%Y%m%d"), trd_id)


# -------------------------------------------------------------------------
def CommitTransaction(transaction, stored_name=None):
    """
    Description:
        Insert/amend a transaction, taking care of all position effects.
    Inputs:
        transaction - the instance of Transaction to commit
        stored_name - the name of the corresponding stored transaction, used
                      for amendments
    Returns:
        The Transaction instance.
    """
    stored_name = stored_name or transaction.Name

    # --- clone security traded: AddByInference is needed to generate the
    #     proper ImpliedName.
    sec = AddByInference(GetObj(transaction.SecurityTraded).clone())

    # --- get transaction info before reloading the transaction
    info = GetVal(transaction, "TransactionInfo")
    info["SecurityTraded"] = sec.Name

    # --- need to overwrite transaction name AFTER looking up TransactionInfo,
    #     otherwise we end up  using TransactionInfo of the stored transaction
    transaction.Name = stored_name

    try:
        # --- reload security: this is needed to avoid basing decisions on
        #     attribute values that might have been set in memory
        transaction = GetObj(transaction.Name, refresh=True)

    except ObjNotFound:
        # --- transaction not found, it must be added to the backend along with
        #     its position effects
        transaction.SecurityTraded = sec.Name
        transaction.Marker = "HEAD"
        return insert_transaction(transaction)

    else:
        return amend_transaction(transaction, info)


# -----------------------------------------------------------------------------
def insert_transaction(transaction):
    """
    This function should never be called directly. Use TransactionCommit
    instead.
    """
    if transaction.Marker != "HEAD":
        raise TransactionError(
            "Only head transaction can be created. Marker for {0:s} "
            "is {1:s}.".format(transaction.Name, transaction.Marker))

    # --- create a new transaction to make sure that Version, ChangedBy, and
    #     timestamps are fresh
    name = transaction.format_name(Date.today(), unique_id(8))
    transaction = transaction.clone(Name=name)
    time_created = transaction.TimeCreated

    logger.info("creating transaction {0:s}".format(name))

    with ObjDbTransaction("Insert", "SERIALIZABLE"):
        AddObj(transaction)

        for pos in GetVal(transaction, "PositionEffects"):
            ObjDbQuery(QUERY_INSERT_POSEFF, parms=(
                pos.TradeDate, time_created, pos.Book, pos.Qty, pos.Unit,
                pos.UnitType, pos.Name, pos.Event, pos.Trade))

    return transaction


# -----------------------------------------------------------------------------
def amend_transaction(head, info):
    """
    This function should never be called directly. Use TransactionCommit
    instead.
    """
    if head.Marker != "HEAD":
        raise TransactionError(
            "Only head transaction can be amended. Marker "
            "for {0:s} is {1:s}.".format(head.Name, head.Marker))

    # --- need to amend?
    same = True
    for attr, value in info.items():
        same = (value == getattr(head, attr))
        if not same:
            break
    if same:
        raise TransactionWarning(
            "found nothing to amend for transaction {0:s}".format(head.Name))

    if head.TimeCreated >= Date.today():
        # --- same day amendment: execute in-place update
        for attr, value in info.items():
            SetVal(head, attr, value)

        logger.info(
            "same day amedment for transaction {0:s}".format(head.Name))

        time_created = head.TimeCreated
        with ObjDbTransaction("Amend", "SERIALIZABLE"):
            UpdateObj(head)

            # --- delete existing position effects for head transaction
            ObjDbQuery(QUERY_DELETE_POSEFF, (head.Name, ))

            # --- insert new position effects
            for pos in GetVal(head, "PositionEffects"):
                ObjDbQuery(QUERY_INSERT_POSEFF, parms=(
                    pos.TradeDate, time_created, pos.Book, pos.Qty, pos.Unit,
                    pos.UnitType, pos.Name, pos.Event, pos.Trade))

        transaction = head

    else:
        # --- previous day amendment: book a backout and then a new transaction
        logger.info(
            "previous day amedment for transaction {0:s}".format(head.Name))

        with ObjDbTransaction("Amend", "SERIALIZABLE"):
            head.Marker = "AMENDED"
            UpdateObj(head)

            backout = head.clone()
            backout.Name = head.format_name(Date.today(), unique_id(8))
            backout.Marker = "BACKOUT"
            backout.PrevTransaction = head.Name
            AddObj(backout)

            new = head.clone()
            new.Name = head.format_name(Date.today(), unique_id(8))
            new.Marker = "HEAD"
            new.PrevTransaction = backout.Name

            CreateInMemory(new)
            for attr, value in info.items():
                SetVal(new, attr, value)

            AddObj(new)

            # --- update position effects table:
            # ---  1) first the back-out transaction: quantities are flipped to
            #         offset original transaction
            for pos in GetVal(backout, "PositionEffects"):
                ObjDbQuery(QUERY_INSERT_POSEFF, parms=(
                    pos.TradeDate, backout.TimeCreated, pos.Book, -pos.Qty,
                    pos.Unit, pos.UnitType, pos.Name, pos.Event, pos.Trade))

            # ---  2) then the new transaction with the amendments
            for pos in GetVal(new, "PositionEffects"):
                ObjDbQuery(QUERY_INSERT_POSEFF, parms=(
                    pos.TradeDate, new.TimeCreated, pos.Book, pos.Qty,
                    pos.Unit, pos.UnitType, pos.Name, pos.Event, pos.Trade))

        transaction = new

    return transaction


# -----------------------------------------------------------------------------
def RollbackTransaction(head):
    """
    Description:
        Rolls back a transaction and all its position effects.
    Inputs:
        head - the transaction to roll-back
    Returns:
        None.
    """
    # --- reload security: this is needed to avoid basing decisions on
    #     attribute values that might have been set in memory
    head = GetObj(head.Name, refresh=True)

    if head.Marker != "HEAD":
        raise TransactionError(
            "Only head transaction can be rolled back. "
            "Marker for {0:s} is {1:s}.".format(head.Name, head.Marker))

    if head.TimeCreated >= Date.today():
        # --- same day roll-back: there are two sub-cases
        if head.PrevTransaction is None:
            # --- case 1: delete transaction (all postion effectes are taken
            #             care of automatically)
            with ObjDbTransaction("Rollback", "SERIALIZABLE"):
                PurgeObj(head.Name)

        else:
            # --- case 2: delete last two transactions and re-mark the amended
            #             one as "HEAD"
            backout = GetObj(head.PrevTransaction, refresh=True)
            amended = GetObj(backout.PrevTransaction, refresh=True)

            # --- check that markers conform to expectation
            if head.Marker != "HEAD":
                raise TransactionError(
                    "Wrong Marker for transaction {0:s}: {1:s} "
                    "instead of HEAD".format(head.Name, head.Marker))
            if backout.Marker != "BACKOUT":
                raise TransactionError(
                    "Wrong Marker for transaction {0:s}: {1:s} "
                    "instead of BACKOUT".format(backout.Name, backout.Marker))
            if amended.Marker != "AMENDED":
                raise TransactionError(
                    "Wrong Marker for transaction {0:s}: {1:s} "
                    "instead of AMENDED".format(amended.Name, amended.Marker))
            amended.Marker = "HEAD"

            with ObjDbTransaction("Rollback", "SERIALIZABLE"):
                PurgeObj(head.Name)
                PurgeObj(backout.Name)
                UpdateObj(amended)

    else:
        # --- previous day roll-back: book backout transactions for both the
        #     current head and backout transactions
        with ObjDbTransaction("Rollback", "SERIALIZABLE"):
            # --- we start with a backout of the head transaction
            head.Marker = "ROLLEDBACK"
            UpdateObj(head)

            head_backout = head.clone()
            head_backout.Name = head.format_name(Date.today(), unique_id(8))
            head_backout.Marker = "BACKOUT"
            head_backout.PrevTransaction = head.Name
            AddObj(head_backout)

            # --- now update position effects: quantities are flipped to
            #     offset original transactions
            for pos in GetVal(head_backout, "PositionEffects"):
                ObjDbQuery(QUERY_INSERT_POSEFF, parms=(
                    pos.TradeDate, head_backout.TimeCreated, pos.Book,
                    -pos.Qty, pos.Unit, pos.UnitType, pos.Name, pos.Event,
                    pos.Trade))

            # --- if head was the result of an amendment, look up the backout
            #     transaction and make it the new head.
            #     NB: a backout transaction has the same sign as the amended
            #         transaction (although when the positions effects are
            #         saved the sign is flipped), therefore no need to flip it
            #         here.
            if head.PrevTransaction is not None:
                backout = GetObj(head.PrevTransaction, refresh=True)
                reverse = backout.clone()
                reverse.Name = backout.format_name(Date.today(), unique_id(8))
                reverse.Marker = "HEAD"
                reverse.PrevTransaction = head_backout.Name
                AddObj(reverse)

                for pos in GetVal(reverse, "PositionEffects"):
                    ObjDbQuery(QUERY_INSERT_POSEFF, parms=(
                        pos.TradeDate, reverse.TimeCreated, pos.Book,
                        pos.Qty, pos.Unit, pos.UnitType, pos.Name, pos.Event,
                        pos.Trade))


# -----------------------------------------------------------------------------
def DeleteTransaction(transaction_name):
    """
    Description:
        Delete a transaction and all its position effects.
    Inputs:
        transaction_name - the name of the transaction to delete
    Returns:
        None.
    """
    # --- reload security: this is needed to avoid basing decisions on
    #     attribute values that might have been set in memory
    transaction = GetObj(transaction_name, refresh=True)

    if transaction.Marker != "HEAD":
        raise TransactionError(
            "Only head transaction can be deleted. Marker for "
            "{0:s} is {1:s}.".format(transaction.Name, transaction.Marker))

    if transaction.TimeCreated >= Date.today():
        # --- same day delete: recursively delete transaction-chain
        with ObjDbTransaction("Delete", "SERIALIZABLE"):
            prev = transaction.PrevTransaction
            PurgeObj(transaction)
            while prev is not None:
                transaction = GetObj(prev, refresh=True)
                prev = transaction.PrevTransaction
                PurgeObj(transaction)

    else:
        # --- previous day delete: book backout transaction
        with ObjDbTransaction("Delete", "SERIALIZABLE"):
            transaction.Marker = "DELETED"
            UpdateObj(transaction)

            backout = transaction.clone()
            backout.Name = transaction.format_name(Date.today(), unique_id(8))
            backout.Marker = "BACKOUT"
            backout.PrevTransaction = transaction.Name
            AddObj(backout)

            # --- this is a dummy head-transaction that is created to preserve
            #     the rule stating that every change to a transaction should be
            #     represented by zero (for same day) or two (for previous day)
            #     new transactions
            #     NB: the quantity is manually set to zero!
            dummy = transaction.clone()
            dummy.Name = transaction.format_name(Date.today(), unique_id(8))
            dummy.Quantity = 0.0  # important!!!
            dummy.Marker = "HEAD"
            dummy.PrevTransaction = backout.Name

            AddObj(dummy)

            # --- now update position effects: quantities are flipped to
            #     offset original transactions
            for pos in GetVal(backout, "PositionEffects"):
                ObjDbQuery(QUERY_INSERT_POSEFF, parms=(
                    pos.TradeDate, backout.TimeCreated, pos.Book, -pos.Qty,
                    pos.Unit, pos.UnitType, pos.Name, pos.Event, pos.Trade))

            # --- save positions effects for the dummy head-transaction: we
            #     need this (even if Qty is zero) to be able to lookup the
            #     head transaction for a given trade (required by the method
            #     TransactionsStored of a Trade instance)
            for pos in GetVal(dummy, "PositionEffects"):
                ObjDbQuery(QUERY_INSERT_POSEFF, parms=(
                    pos.TradeDate, dummy.TimeCreated, pos.Book, pos.Qty,
                    pos.Unit, pos.UnitType, pos.Name, pos.Event, pos.Trade))


# -----------------------------------------------------------------------------
def AgeTransaction(head, date):
    """
    Description:
        Age a transaction and all its position effects.
    Inputs:
        head - the transaction to roll-back
        date - the date of the ageing event
    Returns:
        None.
    """
    # --- reload security: this is needed to avoid basing decisions on
    #     attribute values that might have been set in memory
    head = GetObj(head.Name, refresh=True)

    if head.Marker != "HEAD":
        raise TransactionError(
            "Only head transaction can be aged. Marker "
            "for {0:s} is {1:s}.".format(head.Name, head.Marker))

    sec = GetVal(head, "SecurityTraded")
    event = GetVal(sec, "ExpectedTransaction")
    securities = GetVal(sec, "ExpectedSecurities", event)

    with ObjDbTransaction("Ageing Event", "SERIALIZABLE"):
        head.Marker = "AGED"
        UpdateObj(head)

        backout = head.clone()
        backout.Name = head.format_name(Date.today(), unique_id(8))
        backout.Marker = "BACKOUT"
        backout.TransactionDate = date
        backout.PrevTransaction = head.Name
        AddObj(backout)

        for pos in GetVal(backout, "PositionEffects"):
            ObjDbQuery(QUERY_INSERT_POSEFF, parms=(
                pos.TradeDate, backout.TimeCreated, pos.Book, -pos.Qty,
                pos.Unit, pos.UnitType, pos.Name, pos.Event, pos.Trade))

        # --- insert new transactions
        prev_trans = backout.Name

        for sec_info in securities:
            # --- add security
            sec = AddByInference(sec_info["Security"])
            # --- append new transaction
            insert_transaction(Transaction(
                TransactionDate=date,
                SecurityTraded=sec.Name,
                Quantity=head.Quantity*sec_info["Quantity"],
                Party=GetVal(head, "Party"),
                Counterparty=GetVal(head, "Counterparty"),
                Trade=head.Trade,
                PrevTransaction=prev_trans,
                Event=event,
                Marker="HEAD",
            ))

            # --- only the first of the new transactions points to the previous
            #     trnsaction in the chain (which one exactly of the new
            #     transactionsdoesn't matter as they would have to be all
            #     rolled back together)
            prev_trans = None


# -----------------------------------------------------------------------------
def TransactionsBy(book=None, trade=None,
                   security=None, date_range=None, head_only=True):
    """
    Description:
        Return all transactions matching the given criteria.
    Inputs:
        book       - a given book
        trade      - a given trade
        security   - a given security
        date_range - a tuple of start and end date
        head_only  - if True, only returns the Head trade
    Returns:
        A list of trade names.
    """
    extquery = []
    criteria = []

    if book is not None:
        extquery.append("Book=%s")
        criteria.append(book)

    if trade is not None:
        extquery.append("Trade=%s")
        criteria.append(trade)

    if security is not None:
        extquery.append("Unit=%s")
        criteria.append(security)

    if date_range is not None:
        extquery.append("TradeDate BETWEEN %s AND %s")
        criteria.append(date_range[0])
        criteria.append(date_range[1])

    if len(criteria):
        query = """
        SELECT DISTINCT(Transaction)
        FROM PosEffects WHERE {0:s};""".format(" AND ".join(extquery))
        rows = ObjDbQuery(query, parms=criteria, attr="fetchall")

    else:
        query = "SELECT DISTINCT(Transaction) FROM PosEffects;"
        rows = ObjDbQuery(query, attr="fetchall")

    if head_only:
        return [row.transaction for row in rows
                if GetVal(row.transaction, "Marker") == "HEAD"]
    else:
        return [row.transaction for row in rows]


# -----------------------------------------------------------------------------
def prepare_for_test():
    import psycopg2
    try:
        create_poseffects_table()
    except psycopg2.ProgrammingError as err:
        if psycopg2.errorcodes.lookup(err.pgcode) == "DUPLICATE_TABLE":
            pass
        else:
            raise
