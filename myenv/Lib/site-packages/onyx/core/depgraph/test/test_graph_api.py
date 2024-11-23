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
from onyx.core.database.ufo_fields import IntField, FieldError
from onyx.core.database.objdb import ObjNotFound
from onyx.core.database.objdb_api import GetObj
from onyx.core.depgraph.graph import GraphError
from onyx.core.depgraph.graph_api import GraphNodeDescriptor
from onyx.core.depgraph.graph_api import GetVal, SetVal
from onyx.core.depgraph.graph_api import CreateInMemory, InvalidateNode
from onyx.core.depgraph.ufo_functions import RetainedFactory

from onyx.core.utils.unittest import OnyxTestCase

import time
import unittest

ATTR1 = 333
ATTR2 = 666


###############################################################################
class timer(object):
    # -------------------------------------------------------------------------
    def __enter__(self):
        self.start = time.time()
        return self

    # -------------------------------------------------------------------------
    def __exit__(self, *args):
        self.elapsed = time.time() - self.start


###############################################################################
class test_cls(UfoBase):
    attr1 = IntField(default=ATTR1)
    attr2 = IntField(default=ATTR2)

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def A(self, graph):
        return 1.0 + graph(self, "B") + graph(self, "C", 1, 2)

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def B(self, graph):
        # --- this is a slow method
        time.sleep(2.0)
        return graph(self, "attr1")

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor("Callable")
    def C(self, graph, x, y):
        # --- this is a slow calculated method
        time.sleep(2.0)
        return x + y + graph(self, "attr2")

    # -------------------------------------------------------------------------
    @RetainedFactory()
    def D(self, graph):
        return graph(self, "attr2") / graph(self, "attr1")

    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def parent(self, graph):
        return graph(self, "D")*2.0


###############################################################################
class TestGraph(OnyxTestCase):
    # -------------------------------------------------------------------------
    def setUp(self):
        super().setUp()
        self.instance = CreateInMemory(test_cls(Name="test"))
        self.name = self.instance.Name

    # -------------------------------------------------------------------------
    def tearDown(self):
        super().tearDown()

    # -------------------------------------------------------------------------
    def test_GetVal(self):
        # --- retrive stored attributes by instance name
        self.assertEqual(GetVal(self.name, "attr1"), ATTR1)
        self.assertEqual(GetVal(self.name, "attr2"), ATTR2)

        # --- retrive stored attributes by instance
        self.assertEqual(GetVal(self.instance, "attr1"), ATTR1)
        self.assertEqual(GetVal(self.instance, "attr2"), ATTR2)

        # --- retrive other value types
        self.assertEqual(GetVal(self.name, "A"), 1003.0)
        self.assertEqual(GetVal(self.name, "C", 0, 0), ATTR2)
        self.assertEqual(GetVal(self.name, "C", 1, 0), ATTR2 + 1)
        self.assertEqual(GetVal(self.name, "C", 0, 2), ATTR2 + 2)
        self.assertEqual(GetVal(self.name, "D"), 2.0)

    # -------------------------------------------------------------------------
    def test_SetVal(self):
        self.assertEqual(GetVal(self.name, "attr1"), ATTR1)
        SetVal(self.name, "attr1", 999)
        self.assertEqual(GetVal(self.name, "attr1"), 999)
        self.assertEqual(GetObj(self.name).attr1, 999)
        # --- set a retained GraphNodeDescriptor. we first call the parent node so that D
        #     has parents and children.
        self.assertEqual(GetVal(self.name, "D"), ATTR2 / 999)
        self.assertEqual(GetVal(self.name, "parent"), (ATTR2 / 999) * 2.0)
        SetVal(self.name, "D", "a string")
        self.assertEqual(GetVal(self.name, "D"), "a string")

    # -------------------------------------------------------------------------
    def test_caching(self):
        # --- compute A the first time
        with timer() as t:
            val = GetVal(self.name, "A")
        self.assertEqual(val, 1003.0)
        self.assertAlmostEqual(t.elapsed, 4.0, 1)

        # --- compute A a second time: result is cached
        with timer() as t:
            val = GetVal(self.name, "A")
        self.assertEqual(val, 1003.0)
        self.assertAlmostEqual(t.elapsed, 0.0, 1)

        # --- invalidate B and recalculate A: should only have to recalculate
        #     one of the two children
        InvalidateNode(self.name, "B")
        with timer() as t:
            val = GetVal(self.name, "A")
        self.assertEqual(val, 1003.0)
        self.assertAlmostEqual(t.elapsed, 2.0, 1)

        # --- try once more: should be cached again
        with timer() as t:
            val = GetVal(self.name, "A")
        self.assertEqual(val, 1003.0)
        self.assertAlmostEqual(t.elapsed, 0.0, 1)

    # -------------------------------------------------------------------------
    def test_exceptions(self):
        # --- object doesn't exist
        self.assertRaises(ObjNotFound, GetVal, "xxx", "xxx")
        # --- object exists, but not the GraphNodeDescriptor
        self.assertRaises(AttributeError, GetVal, self.name, "xxx")
        # --- VT is settable but wrong type
        self.assertRaises(FieldError, SetVal, self.name, "attr1", None)
        # --- VT not settable
        self.assertRaises(GraphError, SetVal, self.name, "A", None)
        self.assertRaises(GraphError, SetVal, self.name, "B", None)
        self.assertRaises(GraphError, SetVal, self.name, "C", None)
        # --- callable node invalidated incorrectly
        self.assertRaises(GraphError, InvalidateNode, self.name, "C")


if __name__ == "__main__":
    from onyx.core.utils.unittest import UseEphemeralDbs
    with UseEphemeralDbs():
        unittest.main(failfast=True)
