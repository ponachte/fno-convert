from ..graph import get_name, PipelineGraph
from rdflib import URIRef
from PyQt6.QtCore import pyqtSignal, QObject
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

    def __init__(self, source: "ValueStore", target: "ValueStore") -> None:
        self.source = source
        self.target = target
        source.connect_to(target, self)

class ValueStore(QObject):

    valueChange = pyqtSignal(bool)

    def __init__(self, name, value=None, type=None) -> None:
        super().__init__()
        
        self.name = name
        self.value = None
        self.type = type
        self.setValue(value)

        self.sends_to = set()
        self.depends_on = set()
        self.mappings = {}

    def setValue(self, value):
        if value != self.value:
            if self.type is not None and not type(value) == self.type:
                self.valueChange.emit(False)
            self.value = value
            self.valueChange.emit(True)
    
    def connect_to(self, target: "ValueStore", mapping: "Mapping"):
        self.sends_to.add(target)
        target.depends_on.add(self)
        self.mappings[target] = mapping
    
    def propagate(self):
        for target in self.sends_to:
            target.setValue(self.value)

class Terminal(ValueStore):

    def __init__(self, fun, uri: URIRef, pred: str, value=None, type=None, is_output=False, param_mapping=None) -> None:
        super().__init__(get_name(pred), value, type)
        self.fun = fun
        self.uri = uri
        self.pred = pred
        self.is_output = is_output
        self.param_mapping = param_mapping

    def __hash__(self) -> int:
        return hash(self.uri)
    
    def __eq__(self, other: object) -> bool:
        return isinstance(other, Terminal) and self.uri == other.uri and self.fun.call_uri == other.fun.call_uri and self.fun.scope_uri == other.fun.scope_uri

class Variable(ValueStore):

    def __init__(self, name: str) -> None:
        super().__init__(name)