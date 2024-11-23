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

from .graph_api import GraphNodeDescriptor

import types

__all__ = [
    "RetainedFactory",
    "InheritAsProperty",
    "DiscardInheritedAttribute",
]


###############################################################################
class RetainedFactory(object):
    """
    Description:
        GraphNodeDescriptor factory that implements a descriptor protocol used
        to represent pseudo-attribute nodes, i.e. nodes that can be set but are
        not persisted in database.

    Typical use cases are for the implementation of retained properties (such
    as Spot) where the syntax is as follows:

        @RetainedFactory()
        def Spot(self, graph):
            ...
    """
    # -------------------------------------------------------------------------
    def __init__(self):
        self.values = {}

    # -------------------------------------------------------------------------
    def __call__(self, func):
        def getter(instance, graph):
            try:
                return self.values[instance.Name]
            except KeyError:
                return func(instance, graph)

        def setter(instance, graph, value):
            self.values[instance.Name] = value

        # --- return a settable descriptor ValueType
        return GraphNodeDescriptor("Settable", getter, setter)(func)


###############################################################################
class InheritAsProperty(object):
    """
    Description:
        Class decorator used to replace one or more stored attributes of the
        super class with properties pointing to the same attribute of another
        object.
    Inputs:
        attrs - a list of stored attributes of the super-class that are to be
                replaced by Property value types.
        ptr   - a pointer to the instance of the ufo class from which we are
                inheriting stored attributes as properties.
                Each stored attribute in attrs will be replaced with by
                property node.
    """
    template = ("def template(self, graph):\n"
                "    return graph(graph(self, '{0:s}'), '{1:s}')")

    # -------------------------------------------------------------------------
    def __init__(self, attrs, ptr):
        self.attrs = attrs
        self.ptr = ptr

    # -------------------------------------------------------------------------
    def __call__(self, cls):
        for attr in self.attrs:
            # --- discard from set of StoredAttrs attributes (discard does
            #     nothing if cls doesn't have such attribute)
            cls._json_fields.discard(attr)
            cls.StoredAttrs.discard(attr)

            # --- create Property-NodeDescriptor
            mod = types.ModuleType("__templates")
            exec(self.template.format(self.ptr, attr), mod.__dict__)
            func = types.FunctionType(mod.template.__code__, {}, name=attr)
            setattr(cls, attr, GraphNodeDescriptor()(func))

        return cls


###############################################################################
class DiscardInheritedAttribute(object):
    """
    Description:
        Class decorator used to dis-inherit one or more stored attributes of
        the super class, ususally so that they can be re-implemented as
        properties.
    Inputs:
        attrs - a list of stored attributes of the super-class that are
                to be discarded.
    """
    # -------------------------------------------------------------------------
    def __init__(self, attrs):
        self.attrs = attrs

    # -------------------------------------------------------------------------
    def __call__(self, cls):
        for attr in self.attrs:
            # --- discard from set of StoredAttrs attributes (discard does
            #     nothing if cls doesn't have such attribute)
            cls._json_fields.discard(attr)
            cls.StoredAttrs.discard(attr)

        return cls
