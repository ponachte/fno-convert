from ..graph import PipelineGraph
from ..map import ImpMap
from .store import Terminal
from rdflib import URIRef
from typing import Set

class Process:

    def __init__(self, g: PipelineGraph, call: URIRef, fun: URIRef, scope: URIRef) -> None:
        self.call_uri = call
        self.fun_uri = fun
        self.scope_uri = scope
        self.map_uri, self.imp_uri = g.get_implementation(fun)
        self.name = g.get_name(fun)

        ### FUNCTION OBJECT ###

        self.f_object = ImpMap.rdf_to_imp(g, self.imp_uri)

        ### TERMINALS ###

        self.terminals = {}
        self.self_input = None
        self.self_output = None
        self.output = None

    def inputs(self) -> Set[Terminal]:
        return { self.terminals[name] for name in self.terminals if not self.terminals[name].is_output }

    def outputs(self) -> Set[Terminal]:
        return { self.terminals[name] for name in self.terminals if self.terminals[name].is_output }
    
    def __hash__(self) -> int:
        return hash(self.fun_uri)
    
    def __eq__(self, other: object) -> bool:
        return isinstance(other, Function) and self.call_uri == other.call_uri and self.fun_uri == other.fun_uri and self.scope_uri == other.scope_uri

class Function(Process):

    def __init__(self, g: PipelineGraph, call: URIRef, fun: URIRef, scope: URIRef) -> None:
        super().__init__(g, call, fun, scope)

        ### TERMINALS ###

        self.terminals.update({ par: Terminal(par, g.get_param_predicate(par), call, scope, type=g.get_param_type(par)) for par in g.get_parameters(fun) })
        if g.has_self(fun):
            uri = g.get_self(fun)
            self.self_input = Terminal(uri, 'self', call, scope, type=g.get_param_type(uri))
            self.terminals[self.self_input.uri] = self.self_input
        if g.has_output(fun):
            uri = g.get_output(fun)
            self.output = Terminal(uri, g.get_output_predicate(fun)[1], call, scope, type=g.get_output_type(uri), is_output=True)
            self.terminals[self.output.uri] = self.output
        if g.has_self_output(fun):
            uri = g.get_self_output(fun)
            self.self_output = Terminal(uri, 'self_output', call, scope, type=g.get_output_type(uri), is_output=True)
            self.terminals[self.self_output.uri] = self.self_output
    
class FunctionLink(Process):

    def __init__(self, g: PipelineGraph, fun: URIRef, scope: URIRef, is_output=False) -> None:
        super().__init__(g, None, fun, scope)

        if is_output:
            # Output terminals as input
            if g.has_output(fun):
                uri = g.get_output(fun)
                self.output = Terminal(uri, g.get_output_predicate(fun)[1], fun, scope, type=g.get_output_type(uri))
                self.terminals[self.output.uri] = self.output
            if g.has_self_output(fun):
                uri = g.get_self_output(fun)
                self.self_output = Terminal(uri, 'self_output', fun, type=g.get_output_type(uri))
                self.terminals[self.self_output.uri] = self.self_output
        else:
            # Input terminals as output
            self.terminals.update({ par: Terminal(par, g.get_param_predicate(par), fun, scope, type=g.get_param_type(par), is_output=True) 
                              for par in g.get_parameters(fun) })
            if g.has_self(fun):
                uri = g.get_self(fun)
                self.self_input = Terminal(uri, 'self', fun, scope, type=g.get_param_type(uri))
                self.terminals[self.self_input.uri] = self.self_input

class Constant:

    def __init__(self, value, type) -> None:
        self.output = Terminal(None, 'value', None, value, type, is_output=False)