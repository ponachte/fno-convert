from ..graph import get_name
from rdflib import URIRef

class Mapping:

    def __init__(self, source: "ValueStore", target: "ValueStore") -> None:
        self.source = source
        self.target = target
        source.connect_to(target, self)

class ValueStore:

    def __init__(self, name, value=None, type=None) -> None:
        self.name = name
        self.value = None
        self.type = type
        self.set_value(value)

        self.sends_to = set()
        self.depends_on = set()
        self.mappings = {}

    def set_value(self, value):
        if value != self.value:
            if self.type is not None and not isinstance(value, self.type):
                raise Exception(f"Error while setting value of {self.uri}: Type of value '{value}' must be '{self.type}', while type is '{type(value)}'")
            self.value = value
    
    def connect_to(self, target: "ValueStore", mapping: "Mapping"):
        self.sends_to.add(target)
        target.depends_on.add(self)
        self.mappings[target] = mapping

class Terminal(ValueStore):

    def __init__(self, uri: URIRef, pred: str, fun_uri: URIRef, scope_uri: URIRef, value=None, type=None, is_output=False) -> None:
        super().__init__(get_name(pred), value, type)
        self.uri = uri
        self.pred = pred
        self.fun_uri = fun_uri
        self.scope_uri = scope_uri
        self.is_output = is_output

    def __hash__(self) -> int:
        return hash(self.uri)
    
    def __eq__(self, other: object) -> bool:
        return isinstance(other, Terminal) and self.uri == other.uri and self.fun_uri == other.fun_uri and self.scope_uri == other.scope_uri

class Variable(ValueStore):

    def __init__(self, name: str) -> None:
        super().__init__(name)