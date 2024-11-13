# This Python code is based on Java code originally distributed under
# the Eclipse Public License v2.0.
#
# The accompanying program is provided under the terms of the EPL-2.0.
# You can find the full license here: https://www.eclipse.org/legal/epl-2.0/

import numpy as np

class Layer:
    
    def __init__(self) -> None:
        self._nodes: np.ndarray = np.empty((0,))
    
    def nodes(self) -> np.ndarray:
        return self._nodes
    
    def remove_node(self, node):
        self._nodes = self._nodes[self._nodes != node]
    
    def add_node(self, node):
        self._nodes = np.append(self._nodes, node)