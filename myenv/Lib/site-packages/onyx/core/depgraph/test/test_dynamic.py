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
from onyx.core.database.ufo_fields import FloatField, BoolField

from onyx.core.depgraph.graph_api import GraphNodeDescriptor, CreateInMemory
from onyx.core.depgraph.graph_api import GetVal, GetNode, GetNodeChildren, InvalidateNode
from onyx.core.depgraph.graph_scopes import EvalBlock, GraphScope

from onyx.core.utils.unittest import OnyxTestCase

import unittest

LEAF_1 = 12.3
LEAF_2 = 66.6
FLAG = True
X = 3.14


###############################################################################
class Dynamic(UfoBase):
    leaf1 = FloatField(default=LEAF_1)
    leaf2 = FloatField(default=LEAF_2)
    flag = BoolField(default=FLAG)

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def property(self, graph):
        if graph(self, "flag"):
            return graph(self, "leaf1")
        else:
            return graph(self, "leaf2")

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor("Callable")
    def callable(self, graph, x):
        if graph(self, "flag"):
            return graph(self, "leaf1") + x
        else:
            return graph(self, "leaf2") + x

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor("PropSubGraph")
    def prop_sub_graph(self, graph, x=X):
        if graph(self, "flag"):
            return graph(self, "leaf1") + x
        else:
            return graph(self, "leaf2") + x


###############################################################################
class TestDynamic(OnyxTestCase):
    # -------------------------------------------------------------------------
    def setUp(self):
        super().setUp()
        self.instance = CreateInMemory(Dynamic(Name="dynamic"))
        self.name = self.instance.Name

    # -------------------------------------------------------------------------
    def tearDown(self):
        super().tearDown()

    # -------------------------------------------------------------------------
    def test_leaves(self):
        self.assertEqual(GetVal(self.name, "leaf1"), LEAF_1)
        self.assertEqual(GetVal(self.name, "leaf2"), LEAF_2)
        self.assertEqual(GetVal(self.name, "flag"), FLAG)

    # -------------------------------------------------------------------------
    def test_property(self):
        self.assertEqual(GetVal(self.name, "property"), LEAF_1)

        with EvalBlock() as eb:
            eb.change_value(self.name, "flag", False)
            self.assertEqual(GetVal(self.name, "property"), LEAF_2)

        self.assertEqual(GetVal(self.name, "property"), LEAF_1)

        with EvalBlock() as eb:
            self.assertEqual(GetVal(self.name, "property"), LEAF_1)
            eb.change_value(self.name, "leaf1", 2.71828)
            self.assertFalse(GetNode(self.name, "property").valid)
            self.assertEqual(GetVal(self.name, "property"), 2.71828)

        self.assertEqual(GetVal(self.name, "property"), LEAF_1)

        with EvalBlock() as eb:
            self.assertEqual(GetVal(self.name, "property"), LEAF_1)
            eb.change_value(self.name, "flag", False)
            self.assertEqual(GetVal(self.name, "property"), LEAF_2)
            eb.change_value(self.name, "leaf1", 2.71828)
            self.assertTrue(GetNode(self.name, "property").valid)

        self.assertEqual(GetVal(self.name, "property"), LEAF_1)

        with EvalBlock() as eb:
            eb.change_value(self.name, "flag", False)
            self.assertEqual(GetVal(self.name, "property"), LEAF_2)

        self.assertEqual(GetVal(self.name, "property"), LEAF_1)

        with GraphScope() as scope:
            self.assertEqual(GetVal(self.name, "property"), LEAF_1)
            scope.change_value(self.name, "leaf1", 2.71828)
            self.assertFalse(GetNode(self.name, "property").valid)
            self.assertEqual(GetVal(self.name, "property"), 2.71828)

        self.assertEqual(GetVal(self.name, "property"), LEAF_1)

        with GraphScope() as scope:
            self.assertEqual(GetVal(self.name, "property"), LEAF_1)
            scope.change_value(self.name, "flag", False)
            self.assertEqual(GetVal(self.name, "property"), LEAF_2)
            scope.change_value(self.name, "leaf1", 2.71828)
            self.assertTrue(GetNode(self.name, "property").valid)

        self.assertEqual(GetVal(self.name, "property"), LEAF_1)

    # -------------------------------------------------------------------------
    def test_callable(self):
        self.assertEqual(GetVal(self.name, "callable", 1.0), LEAF_1 + 1.0)

        with EvalBlock() as eb:
            eb.change_value(self.name, "flag", False)
            self.assertEqual(
                GetVal(self.name, "callable", 1.0), LEAF_2 + 1.0)

        self.assertEqual(GetVal(self.name, "callable", 1.0), LEAF_1 + 1.0)

        with EvalBlock() as eb:
            self.assertEqual(
                GetVal(self.name, "callable", 1.0), LEAF_1 + 1.0)
            eb.change_value(self.name, "leaf1", 2.71828)
            self.assertFalse(GetNode(self.name, "callable", (1.0,)).valid)
            self.assertEqual(GetVal(self.name, "callable", 1.0), 3.71828)

        self.assertEqual(GetVal(self.name, "callable", 1.0), LEAF_1 + 1.0)

        with EvalBlock() as eb:
            self.assertEqual(
                GetVal(self.name, "callable", 1.0), LEAF_1 + 1.0)
            eb.change_value(self.name, "flag", False)
            self.assertEqual(
                GetVal(self.name, "callable", 1.0), LEAF_2 + 1.0)
            eb.change_value(self.name, "leaf1", 2.71828)
            self.assertTrue(GetNode(self.name, "callable", (1.0,)).valid)

        self.assertEqual(GetVal(self.name, "callable", 1.0), LEAF_1 + 1.0)

        with EvalBlock() as eb:
            eb.change_value(self.name, "flag", False)
            self.assertEqual(
                GetVal(self.name, "callable", 1.0), LEAF_2 + 1.0)

        self.assertEqual(GetVal(self.name, "callable", 1.0), LEAF_1 + 1.0)

        with GraphScope() as scope:
            self.assertEqual(
                GetVal(self.name, "callable", 1.0), LEAF_1 + 1.0)
            scope.change_value(self.name, "leaf1", 2.71828)
            self.assertFalse(GetNode(self.name, "callable", (1.0,)).valid)
            self.assertEqual(GetVal(self.name, "callable", 1.0), 3.71828)

        self.assertEqual(GetVal(self.name, "callable", 1.0), LEAF_1 + 1.0)

        with GraphScope() as scope:
            self.assertEqual(
                GetVal(self.name, "callable", 1.0), LEAF_1 + 1.0)
            scope.change_value(self.name, "flag", False)
            self.assertEqual(
                GetVal(self.name, "callable", 1.0), LEAF_2 + 1.0)
            scope.change_value(self.name, "leaf1", 2.71828)
            self.assertTrue(GetNode(self.name, "callable", (1.0,)).valid)

        self.assertEqual(GetVal(self.name, "callable", 1.0), LEAF_1 + 1.0)

    # -------------------------------------------------------------------------
    def test_property_sub_graph_vt(self):
        self.assertEqual(GetVal(self.name, "prop_sub_graph"), LEAF_1 + X)
        self.assertEqual(
            GetVal(self.name, "prop_sub_graph", x=1.0), LEAF_1 + 1.0)

        with EvalBlock() as eb:
            self.assertEqual(
                GetVal(self.name, "prop_sub_graph"), LEAF_1 + X)
            eb.change_value(self.name, "leaf1", 2.71828)
            self.assertFalse(GetNode(self.name, "prop_sub_graph").valid)
            self.assertEqual(
                GetVal(self.name, "prop_sub_graph"), 2.71828 + X)

        with EvalBlock() as eb:
            eb.change_value(self.name, "flag", False)
            self.assertEqual(
                GetVal(self.name, "prop_sub_graph"), LEAF_2 + X)
            eb.change_value(self.name, "leaf1", 2.71828)
            self.assertTrue(GetNode(self.name, "prop_sub_graph").valid)
            self.assertEqual(
                GetVal(self.name, "prop_sub_graph"), LEAF_2 + X)

        self.assertEqual(GetVal(self.name, "prop_sub_graph"), LEAF_1 + X)

        with GraphScope() as scope:
            self.assertEqual(
                GetVal(self.name, "prop_sub_graph"), LEAF_1 + X)
            scope.change_value(self.name, "leaf1", 2.71828)
            self.assertFalse(GetNode(self.name, "prop_sub_graph").valid)
            self.assertEqual(
                GetVal(self.name, "prop_sub_graph"), 2.71828 + X)

        with GraphScope() as scope:
            scope.change_value(self.name, "flag", False)
            self.assertEqual(
                GetVal(self.name, "prop_sub_graph"), LEAF_2 + X)
            scope.change_value(self.name, "leaf1", 2.71828)
            self.assertTrue(GetNode(self.name, "prop_sub_graph").valid)
            self.assertEqual(
                GetVal(self.name, "prop_sub_graph"), LEAF_2 + X)

        self.assertEqual(GetVal(self.name, "prop_sub_graph"), LEAF_1 + X)


if __name__ == "__main__":
    from onyx.core.utils.unittest import UseEphemeralDbs
    with UseEphemeralDbs():
        unittest.main(failfast=True)
