from ..graph import ExecutableGraph
from ..executors import Composition

from rdflib import URIRef
import json
import ipyelk

class Visualizer:
    
    def __init__(self):
        self.node_hierarchy = {}
        self.nodes = set()
    
    def establish_node_hierarchy(self, g: ExecutableGraph, comp: Composition):
        self.node_hierarchy[comp.rep] = list(comp.functions.values())

        for fun in comp.functions.values():
            self.nodes.add({"id": hash(fun)})
            if fun.comp:
                self.establish_node_hierarchy(g, fun.comp)

    def to_elk(self, g: ExecutableGraph, comp: Composition):
        elk = { "directed": True, "graph": {}, "multigraph": False }
        
        self.establish_node_hierarchy(g, comp)
        elk["nodes"] = list(self.nodes)
        elk["links"] = [ {"source": hash(s), "target": hash(t) } for s, ts in self.node_hierarchy.items() for t in ts ]
    
    def show(self):
        
        py_elk = {
            "id": "root",
            "properties": { "elk.direction": "RIGHT" },
            "children": [
                { "id": "n1", "width": 10, "height": 10 },
                { "id": "n2", "width": 10, "height": 10 }
            ],
            "edges": [{
                "id": "e1", "sources": ["n1"], "targets": ["n2"]
            }]
        }
        
        return ipyelk.from_elkjson(py_elk)
        
        