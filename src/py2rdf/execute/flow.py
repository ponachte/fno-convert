from ..graph import PipelineGraph
from .process import FunctionLink, Function
from .composition import Composition
from .store import Mapping
from rdflib import URIRef

class FnOExecutable:

    def __init__(self, g: PipelineGraph, executeable: URIRef, outer_fun: Function=None) -> None:
        # get the executable composition
        if not g.is_composition(executeable):
            # Executable is an FnO Function(call)
            self.f_uri = g.check_call(executeable)
            
            comps = g.get_compositions(self.f_uri)
            if len(comps) == 0:
                raise Exception(f"No executable compositions found")
            elif len(comps) > 1:
                raise Exception(f"Choose from one composition: {comps}")
            self.comp = comps[0]
            
            # determine the scope
            self.scope = executeable
        else:
            # Executable is a FnO Composition
            self.comp = executeable
        
            # determine the scope
            reps = g.get_representations(self.comp)
            if len(reps) > 1:
                raise Exception(f"Composition has multiple representaitons {reps}")
            elif len(reps) == 1:
                self.f_uri = reps[0]
                self.scope = reps[0]
            else:
                self.f_uri = None
                self.scope = self.comp 

        # Create inputs and outputs
        self.input = FunctionLink(g, self.f_uri, self.scope, outer_fun)
        self.output = FunctionLink(g, self.f_uri, self.scope, outer_fun, is_output=True)
        
        self.functions = {}
        self.internals = {}

        self.start = Composition(g, self.comp, self)
    
    def add_internal_flow(self, g, fun):
        flow = FnOExecutable(g, fun.call_uri, outer_fun=fun)
        self.internals[fun] = flow
    
    def connect_links(self, fun: Function, comp: Composition):
        for input in fun.inputs():
            link = self.input.links[input.uri]
            for source in input.depends_on:
                comp.mappings.add(Mapping(source, link))
        
        for output in fun.outputs():
            link = self.output.links[output.uri]
            for target in output.sends_to:
                comp.mappings.add(Mapping(link, target))
    
    def get_terminal(self, fun, par):
        if fun == self.f_uri:
            ter = self.input.terminals.get(par, None)
            return ter if ter is not None else self.output.terminals.get(par, None)
        else:
            return self.functions[fun].terminals[par]
    
    def execute(self):
        # propagate input node
        self.input.execute()

        # continuously execute compositions
        next_comp = self.start

        while next_comp is not None:
            next_comp.execute()
            next_comp = next_comp.next()

        # propagate output node
        self.output.execute()

        # return the output
        return { out.name: out.value for out in self.output.outputs() }
    
    def close(self):
        self.closed = True
        self.input.close()
        for fun in self.functions.values():
            fun.close()
        self.output.close()
    
    def open(self):
        self.closed = False
        self.input.open()
        for fun in self.functions.values():
            fun.open()
        self.output.open()