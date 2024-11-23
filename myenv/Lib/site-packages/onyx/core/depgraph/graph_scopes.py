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

from .graph import DependencyGraph, GraphError, PropertyNode, SettableNode

from .. import database as onyx_db
from .. import depgraph as onyx_dg

import collections
import copy

__all__ = ["EvalBlock", "GraphScope"]


###############################################################################
class EvalBlock(object):
    """
    Description:
        Context manager used to manage lifetime of one or more one-off changes.
        NB: when exiting an EvalBlock, all changed nodes as well as their
        ancestors are invalidated and the topology of the graph is lost.
    Usage:
        Typical use is as follows:

        with EvalBlock() as eb:
            eb.change_value("abc", "xyz", 123)
            ...
    """
    # -------------------------------------------------------------------------
    def __init__(self):
        self.__changed_nodes = {}

    # -------------------------------------------------------------------------
    def __enter__(self):
        # --- return a reference to itself (to be used by change_value)
        return self

    # -------------------------------------------------------------------------
    def __exit__(self, *args, **kwds):
        for node_id, original_node in self.__changed_nodes.items():
            # --- invalidate the node and all its ancestors
            onyx_dg.active_graph.invalidate_node(node_id)

            # --- move pre-change node back into the graph
            onyx_dg.active_graph.nodes[node_id] = original_node

        self.__changed_nodes.clear()

        # --- returns False so that all execptions raised will be propagated
        return False

    # -------------------------------------------------------------------------
    def change_value(self, obj, attr, value):
        """
        Description:
            Change the in-memory value of a graph node within an EvalBlock.
        Inputs:
            obj   - instance (or name) of an object derived from UfoBase
            attr  - name of the target attribute/method
            value - the new value for the attribute
        Returns:
            None.
        """
        name = obj if isinstance(obj, str) else obj.Name
        node_id = (name, attr, ())
        is_new_node = False

        try:
            node = onyx_dg.active_graph.nodes[node_id]
        except KeyError:
            node = onyx_dg.active_graph.create_node(node_id)
            onyx_dg.active_graph.nodes[node_id] = node
            is_new_node = True

        if not isinstance(node, (PropertyNode, SettableNode)):
            node_type = node.__class__.__name__
            raise GraphError(
                "Unsupported node type: {0:s}".format(node_type))

        # --- copy pre-change node and store it in __changed_nodes. This
        #     is only required the first time a node is changed.
        if node_id not in self.__changed_nodes:
            original = copy.deepcopy(node)
            if len(onyx_dg.active_graph.children[node_id]) :
                # --- this is a calculated node, invalidate it
                original.valid = False
            else:
                # --- this is a leaf or invalid node, do nothing
                pass
            self.__changed_nodes[node_id] = original

        # --- invalidation is only needed for pre-existing nodes
        if not is_new_node:
            onyx_dg.active_graph.invalidate_node(node_id)

        # --- set the node value and set its state to valid
        node.value = value
        node.valid = True


###############################################################################
class dict_with_fallback(collections.UserDict):
    # -------------------------------------------------------------------------
    def __init__(self, fallback, *args, **kwds):
        super().__init__(*args, **kwds)
        self.fallback = fallback

    # -------------------------------------------------------------------------
    def __getitem__(self, item):
        # --- return the value if present, otherwise get it from the fallback
        #     dictionary, make a deepcopy and return it
        try:
            return self.data[item]
        except KeyError:
            self.data[item] = value = copy.deepcopy(self.fallback[item])
            return value

    # -------------------------------------------------------------------------
    def __iter__(self):
        return iter({**self.data, **self.fallback})


###############################################################################
class GraphScope(DependencyGraph):
    """
    Description:
        Context manager used to manage the lifetime of in-memory changes to
        the graph. All changes applied within a GraphScope remain invisible
        outside the context manager (including graph topology).
        A GraphScope can be used to create persistent scenarions that are
        then re-used multiple times.
    Usage:
        Typical use is as follows:

        scope = GraphScope()
        scope.change_value("abc", xyz", 123)
        with scope:
            scope.change_value("abc", "xxx", 666)
            ...

        with scope:
            ...
            ...
    """
    # -------------------------------------------------------------------------
    def __init__(self):
        super().__init__(db_clt=onyx_dg.active_graph.db_clt)
        # --- save a reference to the underlying graph
        self.udl_graph = onyx_dg.active_graph
        # --- we override nodes, children and parents with custom dictionaries
        #     which fallback to the underlying graph
        self.nodes = dict_with_fallback(self.udl_graph.nodes)
        self.children = dict_with_fallback(self.udl_graph.children)
        self.parents = dict_with_fallback(self.udl_graph.parents)
        # --- set a flag used to determine if the GraphScope is being used as a
        #     context manager
        self.__active = False
        # --- keep track of changed nodes
        self.changes = set() 

    # -------------------------------------------------------------------------
    def __enter__(self):
        self.__active = True
        # --- make sure the underlying graph hasn't changed since the graph
        #     scope was created
        if id(self.udl_graph) != id(onyx_dg.active_graph):
            raise GraphError("Active instance of the "
                "DependencyGraph has changed since the GraphScope was created")
        # --- replace the active graph with the GraphScope
        onyx_dg.active_graph = self
        # --- recursively invalidate all ancestors of each changed node: to
        #     minimize invalidation first collect parents of all changed nodes
        parents = set()
        for changed in self.changes:
            parents.update(self.parents[changed])
        for parent in parents:
            self.invalidate_node(parent)
        # --- return a reference to itself (to be used for disposable scopes)
        return self

    # -------------------------------------------------------------------------
    def __exit__(self, *args, **kwds):
        onyx_dg.active_graph = self.udl_graph
        self.__active = False
        # --- returns False so that all execptions raised will be propagated
        return False

    # -------------------------------------------------------------------------
    def __deepcopy__(self, memo):
        clone = super().__deepcopy__(memo)
        clone.__active = self.__active
        clone.changes = self.changes.copy()
        clone.udl_graph = self.udl_graph
        memo[id(self)] = clone
        return clone

    # -------------------------------------------------------------------------
    def change_value(self, obj, attr, value):
        """
        Description:
            Change the value of a graph node within a GraphScope so that the
            change and all its implications won't be visible outside the scope.
            NB: only Property and Settable (including stored attributes) nodes
                can be changed.
        Inputs:
            obj   - instance (or name) of an object derived from UfoBase
            attr  - name of the target attribute/method
            value - the new value for the attr
        Returns:
            None.
        """
        if not self.__active:
            # --- switch the active graph to the graph scope. also make sure
            #     that the underlying graph hasn't changed since the graph
            #     scope was created
            if id(self.udl_graph) != id(onyx_dg.active_graph):
                raise GraphError(
                    "Active instance of the DependencyGraph"
                    "has changed since the GraphScope was created")
            # --- replace the active graph with the GraphScope
            onyx_dg.active_graph = self

        try:
            name = obj if isinstance(obj, str) else obj.Name
            node_id = (name, attr, ())
            node = self.get_or_create(node_id)

            if not isinstance(node, (PropertyNode, SettableNode)):
                node_type = node.__class__.__name__
                raise GraphError(
                    "Unsupported node type: {0:s}".format(node_type))

            # --- keep track of changed nodes
            self.changes.add(node_id)

            # --- NB: this will also save a local copy of all affected nodes
            self.invalidate_node(node_id)

            # --- set the node value and set its state to valid
            node.value = value
            node.valid = True

        finally:
            if not self.__active:
                onyx_dg.active_graph = self.udl_graph
