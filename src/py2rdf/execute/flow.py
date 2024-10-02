from ..graph import PipelineGraph
from .process import FunctionLink
from .composition import Composition
from rdflib import URIRef

class Flow:

    def __init__(self, g: PipelineGraph, fun: URIRef) -> None:
        self.f_uri = g.check_call(fun)
        self.scope = fun

        self.input = FunctionLink(g, self.f_uri, self.scope)
        self.output = FunctionLink(g, self.f_uri, self.scope, is_output=True)
        self.functions = {}
        self.variables = {}
        self.compositions = {}

        self.start = Composition.build_composition(self, g, g.start_of_flow(fun))
    
    def get_terminal(self, fun, par):
        if fun == self.f_uri:
            ter = self.input.terminals.get(par, None)
            return ter if ter is not None else self.output.terminals.get(par, None)
        else:
            return self.functions[fun].terminals[par]
    
    def execute(self):
        # propagate input node
        self.input.propagate()

        # continuously execute compositions
        next_comp = self.start

        while next_comp is not None:
            next_comp.execute()
            next_comp = next_comp.next()

        # return the output
        return { out.name: out.value for out in self.output.outputs() }