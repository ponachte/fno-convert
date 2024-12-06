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

    def __init__(self, sources, target: "ValueStore") -> None:
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
            self.target.set_value(source.get_value(src_strat, src_key), tar_start, tar_key)

class ValueStore:

    def __init__(self, type=None) -> None:        
        self.value = None
        self.value_set = False
        self.type = type

    def set_value(self, value):
        self.value_set = True
        self.value = value
    
    def get_value(self, strat=None, key=None):
        if strat is not None:
           return self.value[key]
        return self.value
    
    def __hash__(self) -> int:
        return hash(self.value)
    
    def __eq__(self, other: object) -> bool:
        return isinstance(other, ValueStore) and self.value == other.value

class Terminal(ValueStore):

    def __init__(self, fun, uri: URIRef, pred: str, type=None, is_output=False, param_mapping=None) -> None:
        super().__init__(type)
        self.name = get_name(pred)
        self.fun = fun
        self.uri = uri
        self.pred = pred
        self.is_output = is_output
        self.param_mapping = param_mapping
    
    def set_value(self, value, strat=None, key=None):
        if self.is_output:
            super().set_value(value)
            return True
        
        if strat is None:
            self.strat = None
            super().set_value(value)
        else:
            self.strat = strat
            if not isinstance(self.value, dict):
                super().set_value({})
            self.value[key] = value
    
    def get_value(self, strat=None, key=None):
        if strat is not None:
            return super().get_value(strat, key)
        if self.is_output:
            return super().get_value(strat, key)
        
        if (self.param_mapping.get_type() == MappingType.POSITIONAL and self.strat == "fromList") or \
            self.param_mapping.get_type() == MappingType.VARPOSITIONAL:
                indexed = []
                for i, val in super().get_value().items():
                    indexed.append((i, val))
                return [ x[1] for x in sorted(indexed, key=lambda x: x[0]) ]
            
        return super().get_value()
                

    def __hash__(self) -> int:
        return hash(self.uri)
    
    def __eq__(self, other: object) -> bool:
        return isinstance(other, Terminal) and self.uri == other.uri and self.fun == other.fun