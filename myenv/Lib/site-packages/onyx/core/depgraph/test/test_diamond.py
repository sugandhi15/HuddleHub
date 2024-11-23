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

from onyx.core.database.objdb import ObjNotFound
from onyx.core.database.ufo_base import UfoBase
from onyx.core.database.ufo_fields import StringField

from onyx.core.depgraph.graph import GraphError
from onyx.core.depgraph.graph_api import GraphNodeDescriptor, CreateInMemory
from onyx.core.depgraph.graph_api import GetVal, SetVal
from onyx.core.depgraph.graph_api import InvalidateNode, ChildrenSet
from onyx.core.depgraph.graph_scopes import EvalBlock, GraphScope

from onyx.core.utils.unittest import OnyxTestCase

import unittest


###############################################################################
class Diamond(UfoBase):
    D = StringField(default="D")

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def A(self, graph):
        return graph(self, "B") + graph(self, "C")

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def B(self, graph):
        return graph(self, "D") + "B"

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def C(self, graph):
        return graph(self, "D") + "C"


###############################################################################
class TestDiamond(OnyxTestCase):
    # -------------------------------------------------------------------------
    def setUp(self):
        super().setUp()
        self.instance = CreateInMemory(Diamond(Name="diamond"))
        self.name = self.instance.Name

    # -------------------------------------------------------------------------
    def tearDown(self):
        super().tearDown()

    # -------------------------------------------------------------------------
    def test_values(self):
        self.assertEqual(GetVal(self.name, "A"), "DBDC")
        self.assertEqual(GetVal(self.name, "B"), "DB")
        self.assertEqual(GetVal(self.name, "C"), "DC")
        self.assertEqual(GetVal(self.name, "D"), "D")

    # -------------------------------------------------------------------------
    def test_setting_values(self):
        SetVal(self.name, "D", "X")

        self.assertEqual(GetVal(self.name, "A"), "XBXC")
        self.assertEqual(GetVal(self.name, "B"), "XB")
        self.assertEqual(GetVal(self.name, "C"), "XC")
        self.assertEqual(GetVal(self.name, "D"), "X")

        # --- despite invalidation the set node retains the new value as it has
        #     been set on the instance of the underlying object
        InvalidateNode(self.name, "D")
 
        self.assertEqual(GetVal(self.name, "A"), "XBXC")
        self.assertEqual(GetVal(self.name, "B"), "XB")
        self.assertEqual(GetVal(self.name, "C"), "XC")
        self.assertEqual(GetVal(self.name, "D"), "X")

    # -------------------------------------------------------------------------
    def test_children_set(self):
        self.assertEqual(ChildrenSet((self.name, "A"), "D"), {"diamond"})

    # -------------------------------------------------------------------------
    def test_errors(self):
        # --- asking for an object that doesn't exist
        self.assertRaises(ObjNotFound, GetVal, "yyy", "xxx")
        # --- asking for an attribute that doesn't exist
        self.assertRaises(AttributeError, GetVal, self.name, "xxx")
        # --- setting a non-settable node
        self.assertRaises(GraphError, SetVal, self.name, "B", "666")

    # -------------------------------------------------------------------------
    def test_eval_block(self):
        self.test_values()

        with EvalBlock() as eb:
            eb.change_value(self.name, "D", "XXX")
            self.assertEqual(GetVal(self.name, "B"), "XXXB")
            self.assertEqual(GetVal(self.name, "C"), "XXXC")
            self.assertEqual(GetVal(self.name, "A"), "XXXBXXXC")

            InvalidateNode(self.name, "D")

            self.test_values()

            eb.change_value(self.name, "C", "XXX")
            self.assertEqual(GetVal(self.name, "A"), "DBXXX")

        self.test_values()

    # -------------------------------------------------------------------------
    def test_graph_scope(self):
        self.test_values()

        scope = GraphScope()
        scope.change_value(self.name, "D", "XXX")

        self.test_values()

        with scope:
            self.assertEqual(GetVal(self.name, "B"), "XXXB")
            self.assertEqual(GetVal(self.name, "C"), "XXXC")
            self.assertEqual(GetVal(self.name, "A"), "XXXBXXXC")

            InvalidateNode(self.name, "D")

            self.test_values()

            scope.change_value(self.name, "C", "XXX")
            self.assertEqual(GetVal(self.name, "A"), "DBXXX")

        self.test_values()

        with scope:
            self.assertEqual(GetVal(self.name, "A"), "DBXXX")


if __name__ == "__main__":
    from onyx.core.utils.unittest import UseEphemeralDbs
    with UseEphemeralDbs():
        unittest.main(failfast=True)
