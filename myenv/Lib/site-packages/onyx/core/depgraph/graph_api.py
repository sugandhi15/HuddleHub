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

from ..database.ufo_base import get_base_classes
from ..database.objdb import ObjNotFound
from ..database.objdb_api import DelObj
from .graph import DependencyGraph, GraphError, SettableNode, CallableNode
from .graph_node_descriptors import BaseNodeDesc, PropertyNodeDesc
from .graph_node_descriptors import SettableNodeDesc, CallableNodeDesc
from .graph_node_descriptors import PropSubGraphNodeDesc

from .. import database as onyx_db
from .. import depgraph as onyx_dg

__all__ = [
    "GraphError",
    "UseGraph",
    "GraphNodeDescriptor",
    "CreateInMemory",
    "RemoveFromGraph",
    "PurgeObj",
    "GetVal",
    "SetVal",
    "GetNode",
    "GetNodeChildren",
    "GetNodeParents",
    "InvalidateNode",
    "IsInstance",
    "ChildrenSet",
]


###############################################################################
class UseGraph(object):
    """
    Context manager used to created and activate the dependency graph.
    """
    def __init__(self, graph=None):
        self.graph = graph or DependencyGraph(db_clt=onyx_db.obj_clt)

    def __enter__(self):
        # --- make sure the database client is available
        if self.graph.db_clt is None:
            raise GraphError("global database "
                "client is not available (did you call UseDatabase?)")

        # --- we don't support nested graphs as it would make the API
        #     implementation more complicated.
        #     to isolate the active graph from changes GraphScope should be
        #     used instead
        if onyx_dg.active_graph is not None:
            raise GraphError(
                "Nested dependency graphs are "
                "not supported, use a GraphScope instead")

        # --- set the active graph
        onyx_dg.active_graph = self.graph

    def __exit__(self, *args, **kwds):
        onyx_dg.active_graph = None
        # --- returns False so that all execptions raised will be propagated
        return False


###############################################################################
class GraphNodeDescriptor(object):
    """
    This decorator trasforms methods of classes derived from UfoBase into a
    graph node descriptor which in turn is used to create the nodes of the
    DependencyGraph.
    """
    # -------------------------------------------------------------------------
    def __init__(self, node_type="Property", fget=None, fset=None):
        self.node_type = node_type
        if node_type == "Settable":
            if fget is None or fset is None:
                raise GraphError("Settable nodes need both getter and setter")
            else:
                self.fget = fget
                self.fset = fset

    # -------------------------------------------------------------------------
    def __call__(self, func):
        if self.node_type == "Property":
            return PropertyNodeDesc(func)
        elif self.node_type == "Settable":
            return SettableNodeDesc(self.fget, self.fset, func.__name__)
        elif self.node_type == "Callable":
            return CallableNodeDesc(func)
        elif self.node_type == "PropSubGraph":
            return PropSubGraphNodeDesc(func)
        else:
            raise GraphError(
                "Unrecognized node type {0:s}".format(self.node_type))


# -----------------------------------------------------------------------------
def CreateInMemory(instance):
    """
    Description:
        Helper function that adds an instance of an object derived from
        UfoBase in memory so that all its attributes and decorated methods
        are visible to the DependencyGraph and their values can be obtained
        using the standard graph API.
    Inputs:
        instance - the instance of an object derived from UfoBase
    Returns:
        The instance itself.
    """
    if instance.Name is None:
        raise GraphError("instance.Name was not set")

    try:
        # --- return a reference to the cached instance with same name
        return onyx_db.obj_instances[instance.Name]
    except KeyError:
        # --- add object instance to global cache
        onyx_db.obj_instances[instance.Name] = instance
        # --- return a reference to the instance
        return instance


# -----------------------------------------------------------------------------
def RemoveFromGraph(obj):
    """
    Description:
        Remove all nodes referencing a given object from the graph.
    Inputs:
        obj - instance (or name) of an object derived from UfoBase
    Returns:
        None.
    """
    obj_name = obj if isinstance(obj, str) else obj.Name

    # --- list of all nodes ids referencing the given object
    nodes = [node_id
        for node_id, node in onyx_dg.active_graph.nodes.items()
        if node_id[0] == obj_name]

    # --- invalidate all nodes referencing the given object
    for node_id in nodes:
        onyx_dg.active_graph.invalidate_node(node_id)

    # --- remove from the graph all nodes referencing the given object
    for node_id in nodes:
        del onyx_dg.active_graph.nodes[node_id]


# -----------------------------------------------------------------------------
def PurgeObj(obj):
    """
    Description:
        Remove all nodes referencing a given object from the graph and then
        delete the object itself from the database.
    Inputs:
        obj - an instance of an object derived from UfoBase (or its name)
    Returns:
        None.
    """
    RemoveFromGraph(obj)
    try:
        DelObj(obj)
    except ObjNotFound:
        pass


# -----------------------------------------------------------------------------
def GetVal(obj, attr, *args, **kwds):
    """
    Description:
        Get/calculate the value of a graph node. If the node doesn't currently
        exist, it will be created.
        NB: this function should never be used when writing ufo classes as
            it doesn't 'wire' caller and target together, leaving their
            relationship undefined. The injected graph handler should be used
            instead.
    Inputs:
        obj    - instance (or name) of an object derived from UfoBase
        attr   - target's attribute/method
        *args  - positional arguments used to call the target method
        **kwds -      named arguments used to call the target method
    Returns:
        The graph node's value.
    """
    name = obj if isinstance(obj, str) else obj.Name
    node = onyx_dg.active_graph.get_or_create((name, attr, args))
    return node.get_value(*args, **kwds)


# -----------------------------------------------------------------------------
def SetVal(obj, attr, value):
    """
    Description:
        Set the value of a stored attribute on-graph (i.e. the new value is
        visible on the graph). When the instance is persisted by calling
        UpdateObj(obj.Name), the new attribute's value is persisted as well.
        NB: only settable nodes (generally stored attributes) can be set.
    Inputs:
        obj   - instance (or name) of an object derived from UfoBase
        attr  - target's attribute/method
        value - the value to set the VT to
    Returns:
        None.
    """
    name = obj if isinstance(obj, str) else obj.Name

    # --- get the target node from the graph
    node_id = (name, attr, ())
    node = onyx_dg.active_graph.get_or_create(node_id)

    if not isinstance(node, SettableNode):
        raise GraphError(
            "({0!s}, {1!s}, {2!s}) is not a settable node".format(*node_id))

    # --- remove all its children and invalidate recursively the node and its
    #     ancestors
    onyx_dg.active_graph.clear_children(node_id)
    onyx_dg.active_graph.invalidate_node(node_id)

    # --- set the node value and set its state to valid
    node.value = value
    node.valid = True

    # --- set attribute in the cached instance of the object
    setattr(node.obj_ref(), attr, value)


# -----------------------------------------------------------------------------
def GetNode(obj, attr, args=()):
    """
    Description:
        Returns a node from the graph if present, otherwise it creates the new
        node and adds it to the graph.
        NB: application code should never need to fetch a node directly, but
            rather use GetVal.
    Inputs:
        obj  - instance (or name) of an object derived from UfoBase
        attr - name of the target attribute/method
        args - tuple of arguments defining a callable node (optional)
    Returns:
        A reference to the node in the graph.
    """
    name = obj if isinstance(obj, str) else obj.Name
    return onyx_dg.active_graph.get_or_create((name, attr, args))


# -----------------------------------------------------------------------------
def GetNodeChildren(obj, attr, args=()):
    """
    Description:
        Returns the set of children of a given node.
    Inputs:
        obj  - instance (or name) of an object derived from UfoBase
        attr - name of the target attribute/method
        args - tuple of arguments defining a callable node (optional)
    Returns:
        A set.
    """
    name = obj if isinstance(obj, str) else obj.Name
    return onyx_dg.active_graph.children[(name, attr, args)]


# -----------------------------------------------------------------------------
def GetNodeParents(obj, attr, args=()):
    """
    Description:
        Returns the set of parents of a given node.
    Inputs:
        obj  - instance (or name) of an object derived from UfoBase
        attr - name of the target attribute/method
        args - tuple of arguments defining a callable node (optional)
    Returns:
        A set.
    """
    name = obj if isinstance(obj, str) else obj.Name
    return onyx_dg.active_graph.parents[(name, attr, args)]


# -----------------------------------------------------------------------------
def InvalidateNode(obj, attr, args=()):
    """
    Description:
        Invalidate a node in the graph (if it exists).
    Inputs:
        obj  - instance (or name) of an object derived from UfoBase
        attr - target's attribute/method
        args - tuple of arguments defining a callable node (optional)
    Returns:
        None.
    """
    name = obj if isinstance(obj, str) else obj.Name
    node_id = (name, attr, args)

    try:
        node = onyx_dg.active_graph.nodes[node_id]
    except KeyError:
        pass
    else:
        if isinstance(node, CallableNode) and args == ():
            raise GraphError(
                "To invalidate a callable node it is "
                "mandatory to specify the tuple of arguments")

        onyx_dg.active_graph.invalidate_node(node_id)


## -----------------------------------------------------------------------------
#def NodesByObjName(obj):
#    """
#    Description:
#        Returns a list of all the nodes that reference the given object.
#    Inputs:
#        obj - instance (or name) of an object derived from UfoBase
#    Yields:
#        A list of Graph nodes.
#    """
#    obj_name = obj if isinstance(obj, str) else obj.Name
#    
#    return [node
#        for node_id, node in onyx_dg.active_graph.items()
#        if node_id[0] == obj_name]


# # -----------------------------------------------------------------------------
# def ValueTypesByInstance(obj):
#     """
#     Description:
#         Returns a list of all value types for object obj
#     Inputs:
#         obj - instance (or name) of an object derived from UfoBase
#     Returns:
#         A list of VT names.
#     """
#     if isinstance(obj, str):
#         obj = onyx_db.obj_clt.get(obj)
#
#     cls = obj.__class__
#     calc = [name for name, VT in
#             cls.__dict__.items() if isinstance(VT, BaseVT)]
#
#     return list(obj.StoredAttrs) + calc


# -----------------------------------------------------------------------------
def IsInstance(name, obj_type):
    """
    Description:
        This is the equivalent of isinstance, but takes the instance name and
        the class name as inputs.
    Inputs:
        name     - the instance name
        obj_type - the class name
    """
    obj = onyx_db.obj_clt.get(name)
    bases = set(get_base_classes(obj.__class__))
    return obj_type in bases


# -----------------------------------------------------------------------------
def children_iterator(node_id, child_attr, obj_type):
    for name, attr, args in onyx_dg.active_graph.children[node_id]:
        if attr == child_attr:
            if obj_type is None:
                yield name
            else:
                obj = onyx_db.obj_instances[name]
                bases = set(get_base_classes(obj.__class__))
                if obj_type in bases:
                    yield name
        else:
            yield from children_iterator(
                (name, attr, args), child_attr, obj_type)


# -----------------------------------------------------------------------------
def ChildrenSet(node_id, child_attr, obj_type=None, graph=None):
    """
    Description:
        Given a node_id, return the names of all those objects such that the
        node (object, attr) is a descendant of node_id.
        Optionally, children can be restricted to be instances of a given
        class.
    Inputs:
        node_id    - parent node_id, in the form (name, attr, args), where args
                     can be skipped in place of an empty tuple
        child_attr - children attribute's name
        obj_type   - if set, children must be instances of this class (or of a
                     subclass)
        graph      - if set, function used to get/calculate the node's value.
    Yields:
        A set with object names.
    """
    obj, attr, *args = node_id
    name = obj if isinstance(obj, str) else obj.Name
    node_id = (name, attr, tuple(args))

    if graph is None:
        GetVal(obj, attr, *args)
    else:
        graph(obj, attr, *args)

    return set(children_iterator(node_id, child_attr, obj_type))


## -----------------------------------------------------------------------------
#def leaves_iterator(node_id, get_val):
#    stored = get_val(node_id[0], "StoredAttrs")
#
#    for name, vt, args in onyx_dg.active_graph[node_id].children:
#        if vt in stored:
#            yield name, vt
#        else:
#            for leaf in leaves_iterator((name, vt, args), get_val):
#                yield leaf


## -----------------------------------------------------------------------------
#def LeafNodes(node_id, graph=None):
#    """
#    Description:
#        Return all leaf-level nodes (StoredAttrs) of a given node.
#    Inputs:
#        node_id - parent node_id, in the form (Name, VT, args), where args can
#                  be skipped in place of an empty tuple
#        graph   - if set, function used to generate graph topology
#    Yields:
#        A set of nodes.
#    """
#    obj, VT, *args = node_id
#    name = obj if isinstance(obj, str) else obj.Name
#    node_id = (name, VT, tuple(args))
#
#    get_val = graph or GetVal
#    get_val(obj, VT, *args)
#
#    return set(leaves_iterator(node_id, get_val))


## -----------------------------------------------------------------------------
#def settable_iterator(node_id):
#    for kid_id in onyx_dg.active_graph[node_id].children:
#        node = onyx_dg.active_graph[kid_id]
#        for leaf in settable_iterator(kid_id):
#            if leaf is not None:
#                yield leaf
#
#        if isinstance(node, SettableNode):
#            yield kid_id


## -----------------------------------------------------------------------------
#def SettableNodes(node_id, graph=None):
#    """
#    Description:
#        Return all settable children of a given node (stopping at the first
#        level).
#    Inputs:
#        node_id - parent node_id, in the form (Name, VT, args), where args can
#                  be skipped in place of an empty tuple
#        graph   - if set, function used to generate graph topology
#    Yields:
#        A set of nodes.
#    """
#    obj, VT, *args = node_id
#    name = obj if isinstance(obj, str) else obj.Name
#    node_id = (name, VT, tuple(args))
#
#    if graph is None:
#        GetVal(obj, VT, *args)
#    else:
#        graph(obj, VT, *args)
#
#    return set(settable_iterator(node_id))
