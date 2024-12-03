from ..graph import get_name, PipelineGraph
from rdflib import URIRef
from enum import Enum, auto

class MappingType(Enum):
    POSITIONAL = auto()
    KEYWORD = auto()
    VARPOSITIONAL = auto()
    VARKEYWORD = auto()

class ParameterMapping:

    def __init__(self, g: PipelineGraph, fun: URIRef, par: URIRef) -> None:
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
    
    def getType(self):
        return self.type
    
    def getProperty(self):
        return self.property

class Mapping:

    def __init__(self, sources, target: "ValueStore") -> None:
        self.priority = None
        self.sources = { priority: source for priority, source in sources }
        self.target = target
    
    def set_priority(self, priority):
        self.priority = priority
    
    def execute(self):
        self.target.set_value(self.sources[self.priority].value)

class ValueStore:

    def __init__(self, value=None, type=None) -> None:        
        self.value = None
        self.type = type
        
        if value is not None:
            self.set_value(value)

    def set_value(self, value):
        if value != self.value:
            self.value = value
    
    def __hash__(self) -> int:
        return hash(self.value)
    
    def __eq__(self, other: object) -> bool:
        return isinstance(other, ValueStore) and self.value == other.value

class Terminal(ValueStore):

    def __init__(self, fun, uri: URIRef, pred: str, value=None, type=None, is_output=False, param_mapping=None) -> None:
        super().__init__(value, type)
        self.name = get_name(pred)
        self.fun = fun
        self.uri = uri
        self.pred = pred
        self.is_output = is_output
        self.param_mapping = param_mapping

    def __hash__(self) -> int:
        return hash(self.uri)
    
    def __eq__(self, other: object) -> bool:
        return isinstance(other, Terminal) and self.uri == other.uri and self.fun == other.fun