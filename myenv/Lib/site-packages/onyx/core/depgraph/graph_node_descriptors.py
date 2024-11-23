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

from .graph import PropertyNode, SettableNode, CallableNode, PropSubGraphNode
from .graph import GraphError

from .. import depgraph as onyx_dg

import functools


# -------------------------------------------------------------------------
def get_node_val(caller, obj, attr, *args, **kwds):
    """
    Inputs:
        caller - caller node identity
        obj    - the instance of the ufo class or its name
        attr   - name of a stored attribute or of a method decorated by
                 @GraphNodeDescriptor()
        *args  - positional arguments used to call the target method
        **kwds -      named arguments used to call the target method
    Returns:
        The value of the node.
    """    
    # --- define target node id tuple
    if isinstance(obj, str):
        target = (obj, attr, args)
    else:
        target = (obj.Name, attr, args)

    # --- get the target node from the graph (the node is created and added
    #     to the graph if it doesn't exsist)
    #     NB: this will raise the following exceptions BEFORE changing the
    #         state of the graph:
    #         - ObjNotFound    if obj is not found in database or memory
    #         - AttributeError if obj doesn't have a the required attribute
    target_node = onyx_dg.active_graph.get_or_create(target)

    # --- add target to the children set of the caller
    onyx_dg.active_graph.add_child(caller, target)

    # --- now that the graph is set up, we return the value of the target
    #     node.
    return target_node.get_value(*args, **kwds)


###############################################################################
class BaseNodeDesc(object):
    pass


###############################################################################
class PropertyNodeDesc(BaseNodeDesc):
    # -------------------------------------------------------------------------
    def __init__(self, fget):
        # --- ensure that the decorated method has the following signature:
        #         f(self, graph)
        if fget.__code__.co_argcount == 2:
            self.fget = fget
        elif fget.__code__.co_argcount < 2:
            raise GraphError(
                "Missing self and/or graph in the method definition")
        elif fget.__code__.co_argcount > 2:
            raise GraphError(
                "A 'Property' node cannot accept "
                "extra arguments besides self and graph")

    # -------------------------------------------------------------------------
    def __get__(self, instance, cls=None):
        if instance is None:
            # --- it's convenient to return the descriptor itself when accessed
            #     on the class so that getattr(type(obj)), attr) works as
            #     expected
            return self
        caller = (instance.Name, self.fget.__name__, ())
        return self.fget(instance, functools.partial(get_node_val, caller))

    # -------------------------------------------------------------------------
    def __set__(self, instance, value):
        raise AttributeError("Cannot set a Property node")

    # -------------------------------------------------------------------------
    def node(self, attr, ref, args):
        return PropertyNode(attr, ref)


###############################################################################
class SettableNodeDesc(BaseNodeDesc):
    # -------------------------------------------------------------------------
    def __init__(self, fget, fset, name):
        self.__name__ = name
        # ---ensure that getter and setter functions have the following
        #     signature:
        #         fget(self, graph), fset(self, graph, value)
        if fget.__code__.co_argcount == 2:
            self.fget = fget
        elif fget.__code__.co_argcount < 2:
            raise GraphError(
                "Missing self and/or graph in the getter definition")
        elif fget.__code__.co_argcount > 2:
            raise GraphError(
                "A 'Settable' node getter cannot accept "
                "extra arguments besides self and graph")
        if fset.__code__.co_argcount == 3:
            self.fset = fset
        elif fset.__code__.co_argcount < 3:
            raise GraphError(
                "Missing self and/or graph "
                "and/or value in the setter definition")
        elif fset.__code__.co_argcount > 3:
            raise GraphError(
                "A 'Settable' node setter cannot accept "
                "extra arguments besides self, graph, and value")

    # -------------------------------------------------------------------------
    def __get__(self, instance, cls=None):
        if instance is None:
            # --- it's convenient to return the descriptor itself when accessed
            #     on the class so that getattr(type(obj)), attr) works as
            #     expected
            return self
        caller = (instance.Name, self.__name__, ())
        return self.fget(instance, functools.partial(get_node_val, caller))

    # -------------------------------------------------------------------------
    def __set__(self, instance, value):
        caller = (instance.Name, self.__name__, ())
        self.fset(instance, functools.partial(get_node_val, caller), value)

    # -------------------------------------------------------------------------
    def node(self, attr, ref, args):
        return SettableNode(attr, ref)


###############################################################################
class CallableNodeDesc(BaseNodeDesc):
    """
    Description:
        Descriptor used for callable graph nodes, i.e. methods accepting input
        arguments.
        For callable graph nodes the input arguments are part of the node_id so
        that the same method called with different arguments will lead to
        different nodes in the graph.
        The limitation is that only positional arguments are supported.
    Signature, example:
        func(self, graph, x, y, z=1, ...)
    """
    # -------------------------------------------------------------------------
    def __init__(self, func):
        if func.__code__.co_argcount < 3:
            raise GraphError(
                "Callable node's signature requires a "
                "minimum of one argument besides self and graph")
        self.func = func

    # -------------------------------------------------------------------------
    def __get__(self, instance, cls=None):
        self.instance = instance
        return self

    # -------------------------------------------------------------------------
    def __set__(self, instance, value):
        raise AttributeError("Cannot set a Callable node")

    # -------------------------------------------------------------------------
    def __call__(self, *args):
        caller = (self.instance.Name, self.func.__name__, args)
        return self.func(
            self.instance, functools.partial(get_node_val, caller), *args)

    # -------------------------------------------------------------------------
    def node(self, attr, ref, args):
        return CallableNode(attr, ref, args)


###############################################################################
class PropSubGraphNodeDesc(BaseNodeDesc):
    """
    Description:
        Descriptor used to represent a subgraph with property-like leaf nodes.
        The input arguments are treated as children of the node so that when
        called with a different set of arguments the node in the graph will be
        invalidated.
        The limitation is that only keyword arguments are supported.
    Signature, example:
        func(self, graph, x=1, y=None, ...)
    """
    # -------------------------------------------------------------------------
    def __init__(self, func):
        argcount = func.__code__.co_argcount
        if argcount < 3:
            raise GraphError(
                "PropSubGraph node's signature requires a "
                "minimum of one argument besides self and graph")
        if not func.__defaults__ or  (argcount - 2 != len(func.__defaults__)):
            raise GraphError(
                "PropSubGraph node's signature requires all "
                "arguments besides self and graph to provide a default value")
        self.func = func

    # -------------------------------------------------------------------------
    def __get__(self, instance, cls=None):
        self.instance = instance
        return self

    # -------------------------------------------------------------------------
    def __set__(self, instance, value):
        raise AttributeError("Cannot set a PropSubGraph node")

    # -------------------------------------------------------------------------
    def __call__(self, **kwds):
        caller = (self.instance.Name, self.func.__name__, ())
        graph = functools.partial(get_node_val, caller)
        return self.func(self.instance, graph, **kwds)

    # -------------------------------------------------------------------------
    def node(self, attr, ref, args):
        return PropSubGraphNode(attr, ref)
