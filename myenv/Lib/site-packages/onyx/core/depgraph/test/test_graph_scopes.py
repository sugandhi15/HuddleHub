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

from onyx.core.database.ufo_base import UfoBase
from onyx.core.database.ufo_fields import FloatField
from onyx.core.depgraph.graph_api import GraphNodeDescriptor
from onyx.core.depgraph.graph_api import GetVal, SetVal, CreateInMemory
from onyx.core.depgraph.graph_api import UseGraph, InvalidateNode, GraphError
from onyx.core.depgraph.graph_scopes import EvalBlock, GraphScope

from onyx.core.utils.unittest import OnyxTestCase

import unittest

VAL = 2.0


###############################################################################
class test_cls(UfoBase):
    Number = FloatField(default=VAL)

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def Property(self, graph):
        return 1.0 + 2.0*graph(self, "Number")


###############################################################################
class TestGraphScopes(OnyxTestCase):
    # -------------------------------------------------------------------------
    def setUp(self):
        super().setUp()
        self.instance = CreateInMemory(test_cls(Name="test"))
        self.name = self.instance.Name

    # -------------------------------------------------------------------------
    def tearDown(self):
        super().tearDown()

    # -------------------------------------------------------------------------
    def node_assertEqual(self, obj, attr, value):
        self.assertEqual(GetVal(self.name, attr), value)
        self.assertEqual(GetVal(self.instance, attr), value)

    # -------------------------------------------------------------------------
    def test_evalblock(self):
        self.node_assertEqual(self.name, "Property", 2*VAL + 1.0)

        # --- create an eval block
        with EvalBlock() as ev_block:
            self.node_assertEqual(self.name, "Number", VAL)
            self.node_assertEqual(self.name, "Property", 2*VAL + 1.0)

            # --- now change Number to 0
            ev_block.change_value(self.name, "Number", 0)
            self.node_assertEqual(self.name, "Property", 1.0)

            # --- test multiple changes within nested eval blocks
            with EvalBlock() as new_ev_block:
                new_ev_block.change_value(self.name, "Number", 333)
                self.node_assertEqual(self.name, "Property", 333*2.0 + 1.0)

                new_ev_block.change_value(self.name, "Number", -333)
                self.node_assertEqual(self.name, "Property", -333*2.0 + 1.0)

            # --- outside nested eval block
            self.node_assertEqual(self.name, "Property", 1.0)

            # --- now change Property itself
            ev_block.change_value(self.name, "Property", 1976)
            self.node_assertEqual(self.name, "Property", 1976)

            with EvalBlock() as new_ev_block:
                new_ev_block.change_value(self.name, "Property", 333)
                self.node_assertEqual(self.name, "Property", 333)

            # --- outside nested eval block
            self.node_assertEqual(self.name, "Property", 1976)

            # --- invalidating a changed node should take it back to the
            #     original state
            InvalidateNode(self.name, "Property")
            self.node_assertEqual(self.name, "Property", 1.0)

        # --- outside all eval blocks
        self.node_assertEqual(self.name, "Number", VAL)
        self.node_assertEqual(self.name, "Property", 2*VAL + 1.0)

    # -------------------------------------------------------------------------
    def test_graphscope_throwaway(self):
        with GraphScope() as scope:
            self.node_assertEqual(self.name, "Number", VAL)
            self.node_assertEqual(self.name, "Property", 2*VAL + 1.0)

            scope.change_value(self.name, "Number", 0.0)

            self.node_assertEqual(self.name, "Number", 0.0)
            self.node_assertEqual(self.name, "Property", 1.0)

            scope.change_value(self.name, "Property", "ABC")

            self.node_assertEqual(self.name, "Number", 0.0)
            self.node_assertEqual(self.name, "Property", "ABC")

        # --- outside graph scope
        self.node_assertEqual(self.name, "Number", VAL)
        self.node_assertEqual(self.name, "Property", 2*VAL + 1.0)

        # --- the graph scope should be usable again
        with scope:
            self.node_assertEqual(self.name, "Number", 0.0)
            self.node_assertEqual(self.name, "Property", "ABC")

            # --- invalidating a changed node should bring it back to the
            #     original state
            InvalidateNode(self.name, "Property")
            self.node_assertEqual(self.name, "Property", 1.0)

        # --- outside graph scope
        self.node_assertEqual(self.name, "Number", VAL)
        self.node_assertEqual(self.name, "Property", 2*VAL + 1.0)

    # -------------------------------------------------------------------------
    def test_graphscope(self):
        self.node_assertEqual(self.name, "Number", VAL)
        self.node_assertEqual(self.name, "Property", 2*VAL + 1.0)

        # --- create a graph scope and set a first change
        scope = GraphScope()
        scope.change_value(self.name, "Number", 0.0)

        # --- the value is changed, but not yet used
        self.node_assertEqual(self.name, "Number", VAL)
        self.node_assertEqual(self.name, "Property", 2*VAL + 1.0)

        # --- use the graph scope to enforce existing changes and to add more
        with scope:
            self.node_assertEqual(self.name, "Number", 0.0)
            self.node_assertEqual(self.name, "Property", 1.0)

            scope.change_value(self.name, "Property", "ABC")

            self.node_assertEqual(self.name, "Number", 0.0)
            self.node_assertEqual(self.name, "Property", "ABC")

        # --- outside graph scope
        self.node_assertEqual(self.name, "Number", VAL)
        self.node_assertEqual(self.name, "Property", 2*VAL + 1.0)

        # --- a graph scope can be reused and all changes are active again
        with scope:
            self.node_assertEqual(self.name, "Number", 0.0)
            self.node_assertEqual(self.name, "Property", "ABC")

            # --- invalidating a changed node should bring it back to the
            #     original state
            InvalidateNode(self.name, "Property")
            self.node_assertEqual(self.name, "Property", 1.0)

        # --- outside graph scope
        self.node_assertEqual(self.name, "Number", VAL)
        self.node_assertEqual(self.name, "Property", 2*VAL + 1.0)

    # -------------------------------------------------------------------------
    def test_nested_graphscopes_1(self):
        self.node_assertEqual(self.name, "Number", VAL)
        self.node_assertEqual(self.name, "Property", 2*VAL + 1.0)

        # --- create a graph scope and set a first change
        outer = GraphScope()
        outer.change_value(self.name, "Number", 0.0)

        with outer:
            # --- create a second graph scope within the outer scope so that
            #     inner will fallback on outer and inherit its changes
            inner = GraphScope()

            self.node_assertEqual(self.name, "Number", 0.0)
            self.node_assertEqual(self.name, "Property", 1.0)

            with inner:
                self.node_assertEqual(self.name, "Number", 0.0)
                self.node_assertEqual(self.name, "Property", 1.0)

                inner.change_value(self.name, "Number", 5)
                self.node_assertEqual(self.name, "Property", 11.0)

                inner.change_value(self.name, "Number", -5)
                self.node_assertEqual(self.name, "Property", -9.0)

            self.node_assertEqual(self.name, "Number", 0.0)
            self.node_assertEqual(self.name, "Property", 1.0)

        self.node_assertEqual(self.name, "Number", VAL)
        self.node_assertEqual(self.name, "Property", 2*VAL + 1.0)

    # -------------------------------------------------------------------------
    def test_multiple_graphs_copes(self):
        self.node_assertEqual(self.name, "Number", VAL)
        self.node_assertEqual(self.name, "Property", 2*VAL + 1.0)

        # --- create a graph scope and set a first change
        first = GraphScope()
        first.change_value(self.name, "Number", 0.0)

        # --- create a second graph scope outside the first scope so that
        #     second will not fallback on first and it won't inherit its
        #     changes.
        #     NB: you won't be abltto nest the scopes this way
        second = GraphScope()
        second.change_value(self.name, "Number", 5.0)

        with first:
            self.node_assertEqual(self.name, "Number", 0.0)
            self.node_assertEqual(self.name, "Property", 1.0)

            with self.assertRaises(GraphError):
                with second:
                    pass

        with second:
            self.node_assertEqual(self.name, "Number", 5.0)
            self.node_assertEqual(self.name, "Property", 11.0)

        self.node_assertEqual(self.name, "Number", VAL)
        self.node_assertEqual(self.name, "Property", 2*VAL + 1.0)


if __name__ == "__main__":
    from onyx.core.utils.unittest import UseEphemeralDbs
    with UseEphemeralDbs():
        unittest.main(failfast=True)
