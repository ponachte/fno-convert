from ..graph import get_name, ExecutableGraph
from rdflib import URIRef
from enum import Enum, auto

class MappingType(Enum):
    POSITIONAL = auto()
    KEYWORD = auto()
    VARPOSITIONAL = auto()
    VARKEYWORD = auto()

class ParameterMapping:

    def __init__(self, g: ExecutableGraph, fun: URIRef, par: URIRef) -> None:
        self.property = None
        self.type = None
        if g.is_varpositional(fun, par):
            self.type = MappingType.VARPOSITIONAL
        if g.is_varkeyword(fun, par):
            self.type = MappingType.VARKEYWORD
        
        index, prop = g.get_param_mapping(fun, par)

        if prop is not None:
            self.property = prop
            self.type = MappingType.KEYWORD
        if index is not None:
            self.property = index
            self.type = MappingType.POSITIONAL
        
        self.has_default, self.default = g.get_default_mapping(fun, par)    
        
    def get_type(self):
        return self.type
    
    def get_property(self):
        return self.property

class Mapping:

    def __init__(self, sources, target: "Terminal") -> None:
        self.priority = None
        self.sources = {}
        for source, priority, src_strat, src_key, tar_start, tar_key in sources:
            if priority not in self.sources:
                self.sources[priority] = []
            self.sources[priority].append((source, src_strat, src_key, tar_start, tar_key))
        self.target = target
    
    def set_priority(self, priority):
        self.priority = priority
    
    def execute(self):
        for source, src_strat, src_key, tar_start, tar_key in self.sources[self.priority]:
            self.target.set(source.get(src_strat, src_key), tar_start, tar_key)
    
    def list_sources(self):
        sources = set()
        for priority in self.sources:
            for source, _, _, _, _ in self.sources[priority]:
                sources.add(source)
        return sources
            
    def json_elk(self):
        edges = []
        for source in self.list_sources():
            if isinstance(source, Terminal):
                edges.append({
                    "id": f"{source.id()}_{self.target.id()}",
                    "target": self.target.fun.id(),
                    "targetPort": self.target.id(),
                    "source": source.fun.id(),
                    "sourcePort": source.id()
                })
        return edges

class ValueStore:
    
    def __init__(self, type=None):
        self.value = None
        self.type = type
        self.value_set = False
    
    def get(self, strat=None, key=None):
        return self.value if strat is None else self.value[key]
    
    def set(self, value):
        self.value_set = True
        self.value = value

class Terminal(ValueStore):

    def __init__(self, fun, uri: URIRef, pred: str, type=None, is_output=False, param_mapping=None) -> None:
        super().__init__(type)
        self.name = get_name(pred)
        self.fun = fun
        self.uri = uri
        self.pred = pred
        self.is_output = is_output
        self.param_mapping = param_mapping
    
    def set(self, value, strat=None, key=None):
        if strat is None:
            self.strat = None
            super().set(value)
        else:
            self.strat = strat
            if not isinstance(self.value, dict):
                super().set({})
            self.value[key] = value

    def get(self, strat=None, key=None):
        if self.is_output or self.param_mapping.get_type() is None:
            return super().get(strat, key)
        
        if (self.param_mapping.get_type() == MappingType.POSITIONAL and self.strat == "toList") or \
            self.param_mapping.get_type() == MappingType.VARPOSITIONAL:
                return self.to_list()
            
        return super().get(strat, key)
    
    def to_list(self):
        if self.strat != "toList":
            raise Exception(f"Terminal does not represent a list: {self.strat}")
        
        indexed = []
        for i, val in self.value.items():
            indexed.append((i, val))
        return [ x[1] for x in sorted(indexed, key=lambda x: x[0]) ]
    
    def id(self):
        return f"{self.fun.id()}_{get_name(self.uri)}"
                
    def json_elk(self):
        return {
            "id": self.id(),
            "width": 5,
            "height":5,
            "labels": [{
                "text":  get_name(self.pred)
            }] if not self.is_output else [],
            "layoutOptions": {
                "port.side": "EAST" if self.is_output else "WEST"
            }
        }

    def __hash__(self) -> int:
        return hash(self.uri)
    
    def __eq__(self, other: object) -> bool:
        return isinstance(other, Terminal) and self.uri == other.uri and self.fun == other.fun