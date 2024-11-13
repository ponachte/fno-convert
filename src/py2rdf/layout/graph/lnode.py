# This Python code is based on Java code originally distributed under
# the Eclipse Public License v2.0.
#
# The accompanying program is provided under the terms of the EPL-2.0.
# You can find the full license here: https://www.eclipse.org/legal/epl-2.0/

import numpy as np

from enum import Enum, auto

from .layer import Layer

class NodeType(Enum):
    
    NORMAL = auto()
    LONG_EDGE = auto()
    EXTERNAL_POINT = auto()
    BREAKING_POINT = auto()
    

class LNode:
    
    def __init__(self, graph) -> None:
        
        # The containing graph
        self._graph = graph
        # The containing layer
        self._layer : Layer = None
        # the node type
        self._type = NodeType.NORMAL
        # the ports of the node
        self._ports = np.empty((0,))
        # the nested graph of a node if it exists
        self._nested_graph = None
    
    def graph(self):
        return self._graph
    
    def layer(self):
        return self._layer
    
    def set_layer(self, layer: Layer):
        if self._layer is not None:
            self._layer.remove_node(self)
        
        self._layer = layer
        
        if self._layer is not None:
            self._layer.add_node(self)
    
    def ports(self):
        return self._ports
    
    def ports(self, type):
        pass
    
    def type(self):
        return self._type
    
    def set_type(self, type: NodeType):
        self._type = type