# This Python code is based on Java code originally distributed under
# the Eclipse Public License v2.0.
#
# The accompanying program is provided under the terms of the EPL-2.0.
# You can find the full license here: https://www.eclipse.org/legal/epl-2.0/

import numpy as np

from ..graph.lgraph import LGraph

class GreedyCycleBreaker:
    
    def __init__(self) -> None:
        pass
    
    def process(self, lgraph: LGraph):
        
        nodes = lgraph.layerless_nodes()
        
        unprocessed_node_count = nodes.size
        indeg = np.array([unprocessed_node_count])      # indegree values for the nodes
        outdeg = np.array([unprocessed_node_count])     # outdegree values for the nodes
        mark = np.array([unprocessed_node_count])       # mark for the nodes, including an ordering of the nodes
        
        index = 0
        for node in nodes:
            node.id = index
            
            for port in node.ports():
                for edge in port.incoming_edges():
                    pass