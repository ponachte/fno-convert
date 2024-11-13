# This Python code is based on Java code originally distributed under
# the Eclipse Public License v2.0.
#
# The accompanying program is provided under the terms of the EPL-2.0.
# You can find the full license here: https://www.eclipse.org/legal/epl-2.0/

import numpy as np

from .lnode import LNode

class LGraph:
    
    def __init__(self) -> None:
        self._layerless_nodes: np.ndarray = np.empty((0,))  # 1D Array
        self._layers: np.ndarray = np.empty((0,))
        self._parentNode: LNode = None 
    
    def layerless_nodes(self) -> np.ndarray:
        return self._layerless_nodes
    
    def layers(self) -> np.ndarray:
        return self._layers
    
    def size(self):
        """
        The total size of the drawing not including padding
        
        :returns: Tuple
        """
    
    def padding(self):
        pass
    
    def offset(self):
        pass