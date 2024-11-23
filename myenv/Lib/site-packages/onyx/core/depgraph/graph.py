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

import collections
import copy
import weakref


###############################################################################
class GraphError(Exception):
    pass


###############################################################################
class DependencyGraph(object):
    """
    Class representing the onyx Dependency Graph (a Directed Acyclic Graph).
    Current implementation uses a dictionary that maps tuple of the type
    (ObjectName, AttributeName, args=()) to graph nodes (instances of
    GraphNode class).
    """
    # -------------------------------------------------------------------------
    def __init__(self, db_clt):
        # --- database client instance
        self.db_clt = db_clt
        # --- here we store the nodes
        self.nodes = dict()
        # --- for each node we keep the list of all its children
        self.children = collections.defaultdict(lambda: set())
        # --- for each node we keep the list of all its parents
        self.parents = collections.defaultdict(lambda: set())

    # -------------------------------------------------------------------------
    def add_child(self, node_id, child):
        self.children[node_id].add(child)
        self.parents[child].add(node_id)

    # -------------------------------------------------------------------------
    def clear_children(self, node_id):
        for child in self.children[node_id]:
            # --- this should never raise KeyError
            self.parents[child].remove(node_id)
        self.children[node_id].clear()

    # -------------------------------------------------------------------------
    def get_or_create(self, node_id):
        try:
            return self.nodes[node_id]
        except KeyError:
            self.nodes[node_id] = node = self.create_node(node_id)
            return node

    # -------------------------------------------------------------------------
    def create_node(self, node_id):
        if len(node_id) == 2:
            obj_name, attr = node_id
            args = ()
        else:
            obj_name, attr, args = node_id
    
        obj = self.db_clt.get(obj_name)
    
        if attr == "StoredAttrs":
            # --- StoredAttrs is special insofar that we don't want it to be
            #     settable/changeable
            return GraphNode(attr, weakref.ref(obj))
        elif attr in obj.StoredAttrs:
            # --- all stored attributes are settable by definition
            return SettableNode(attr, weakref.ref(obj))
        else:
            # --- use the node constructor of the node descriptor itself
            node_descriptor = getattr(obj.__class__, attr)
            return node_descriptor.node(attr, weakref.ref(obj), args)

    # -------------------------------------------------------------------------
    def invalidate_node(self, node_id):
        try:
            for parent in self.parents[node_id].copy():
                self.invalidate_node(parent)

            self.nodes[node_id].valid = False
            self.clear_children(node_id)
        except KeyError:
            # --- early return if node doesn't exist
            return

    # -------------------------------------------------------------------------
    def clear(self):
        self.nodes.clear()
        self.children.clear()
        self.parents.clear()

    # -------------------------------------------------------------------------
    def __deepcopy__(self, memo):
        clone = self.__new__(self.__class__)
        clone.db_clt = self.db_clt
        clone.nodes = copy.deepcopy(self.nodes)
        clone.children = self.children.copy()
        clone.parents = self.parents.copy()
        memo[id(self)] = clone
        return clone


###############################################################################
class GraphNode(object):
    """
    Base class representing a node in the Dependency Graph.
    """
    __slots__ = ("attr", "obj_ref", "valid", "value")

    # -------------------------------------------------------------------------
    def __init__(self, attr, obj_ref):
        self.attr = attr
        self.obj_ref = obj_ref
        self.valid = False
        self.value = None

    # -------------------------------------------------------------------------
    def get_id(self):
        return self.obj_ref().Name, self.attr, ()

    # -------------------------------------------------------------------------
    def get_value(self):
        if not self.valid:
            # --- get the attribute's value from the instance itself and return
            #     it to the caller
            self.value = getattr(self.obj_ref(), self.attr)
            self.valid = True

        return copy.deepcopy(self.value)

    # -------------------------------------------------------------------------
    def __deepcopy__(self, memo):
        clone = self.__new__(self.__class__)
        clone.attr = self.attr
        clone.obj_ref = self.obj_ref
        clone.valid = self.valid
        # --- value can be an instance of a mutable class, make a proper copy.
        clone.value = copy.deepcopy(self.value)
        memo[id(self)] = clone
        return clone


###############################################################################
class PropertyNode(GraphNode):
    """
    Derived class used for Property ValueTypes.
    """
    __slots__ = ()


###############################################################################
class SettableNode(GraphNode):
    """
    Derived class used for nodes whose value can be explicitly set (such as
    StoredAttrs and descriptors that implement a setter).
    """
    __slots__ = ()


###############################################################################
class CallableNode(GraphNode):
    __slots__ = ("args",)

    # -------------------------------------------------------------------------
    def __init__(self, attr, obj_ref, args):
        super().__init__(attr, obj_ref)
        self.args = args

    # -------------------------------------------------------------------------
    def get_id(self):
        return self.obj_ref().Name, self.attr, self.args

    # -------------------------------------------------------------------------
    def get_value(self, *args):
        assert args == self.args
        if not self.valid:
            # --- call the object's method with the arguments for this node
            self.value = getattr(self.obj_ref(), self.attr)(*args)
            self.valid = True

        return copy.deepcopy(self.value)

    # -------------------------------------------------------------------------
    def __deepcopy__(self, memo):
        clone = super().__deepcopy__(memo)
        # --- shallow copies here should be fine
        clone.args = self.args[:]
        memo[id(self)] = clone
        return clone


###############################################################################
class PropSubGraphNode(GraphNode):
    __slots__ = ("kwds",)

    # -------------------------------------------------------------------------
    def __init__(self, attr, obj_ref):
        super().__init__(attr, obj_ref)
        self.kwds = {}

    # -------------------------------------------------------------------------
    def get_value(self, **kwds):
        # --- if kwds don't match the stored values, the node is assumed to be
        #     no longer valid
        if kwds != self.kwds:
            self.valid = False
            self.kwds = kwds

        if not self.valid:
            # --- call the object's method with provided arguments
            self.value = getattr(self.obj_ref(), self.attr)(**kwds)
            self.valid = True

        return copy.deepcopy(self.value)

    # -------------------------------------------------------------------------
    def __deepcopy__(self, memo):
        clone = super().__deepcopy__(memo)
        clone.kwds = copy.deepcopy(self.kwds)
        memo[id(self)] = clone
        return clone
