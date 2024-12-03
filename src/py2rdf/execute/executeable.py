from ..graph import PipelineGraph, get_name
from .store import Mapping, Terminal, ValueStore, ParameterMapping, MappingType
from ..map import ImpMap
from rdflib import URIRef
from typing import Set
import datetime

class Composition:

    def __init__(self, g: PipelineGraph, comp: URIRef, rep: "Function" = None) -> None:
        self.uri = comp
        self.name = get_name(comp)
        self.rep = rep
        
        if rep is None:
            reps = g.get_representations(comp)
            if len(reps) > 1:
                raise Exception(f"Composition has multiple representaitons {reps}")
            elif len(reps) == 1:
                self.scope = reps[0]
            else:
                self.scope = comp
        else:
            self.scope = rep.uri

        ### USED FUNCTIONS ###
        self.functions = {}

        # Get all the used functions
        for call in g.get_used_functions(self.uri):
            if call != self.scope and call not in self.functions:
                self.functions[call] = AppliedFunction(g, call, self.scope)

        ### MAPPINGS ###

        self.mappings = {}
        self.priorities = {}
        
        for mapfrom, mapto, priority in g.get_mappings(comp):          
            # Handle mapfrom
            if g.is_function_mapping(mapfrom):
                call, ter = g.get_function_mapping(mapfrom)
                source = self.get_terminal(call, ter)
            elif g.is_term_mapping(mapfrom):
                source = ValueStore(mapfrom.value, mapfrom.datatype)
            
            # Handle mapto
            call, ter = g.get_function_mapping(mapto)
            target = self.get_terminal(call, ter)
            
            # Create mapping
            if target not in self.mappings:
                self.mappings[target] = []
            self.mappings[target].append((source, priority))
            
            for target, sources in self.mappings.items():
                self.mappings[target] = Mapping(sources, target)
                for _, priority in sources:
                    if priority not in self.priorities:
                        self.priorities[priority] = self.mappings[target]
        
        ### EXECUTION START ###
        self.start = g.get_start(comp)
    
    def execute(self):
        # Execute each function and follow the control flow until no new function can be selected
        call = self.start
        while call:
            # Get the FnO Function Executeable
            fun = self.functions[call]
            # Fetch inputs from mappings
            self.ingest(fun)
            # Execute
            fun.execute()
            # Signify execution to relevant mappings
            if call in self.priorities:
                for mapping in self.priorities[call]:
                    mapping.set_priority(call)
            # Get the URI of the next executeable
            call = fun.next()
        
        # If this composition represents the internal flow of a function, set the output
        if self.rep:
            self.ingest(self.scope)
    
    def ingest(self, fun):
        for mapping in self.mappings[fun]:
            mapping.execute()            
    
    def get_terminal(self, call, ter):
        return  self.functions[call][ter] if call != self.scope else self.rep[ter]
    
    def __hash__(self) -> int:
        return hash(self.uri)
    
    def __eq__(self, other: object) -> bool:
        return isinstance(other, Composition) and self.uri == other.uri

class Function:

    def __init__(self, g: PipelineGraph, fun: URIRef, internal=False) -> None:
        self.uri = fun
        self.name = g.get_name(fun)
        self.map, self.imp = g.get_implementation(fun)
        
        ### FUNCTION OBJECT ###
        
        self.f_object = ImpMap.rdf_to_imp(g, self.imp)

        ### TERMINALS ###

        self.terminals = {}
        self.self_input = None
        self.self_output = None
        self.output = None
        
        self.terminals.update({ par: Terminal(self, par, g.get_predicate(par), 
                                              type=g.get_param_type(par), 
                                              param_mapping=ParameterMapping(g, fun, par)) for par in g.get_parameters(fun) })
        
        if g.has_self(fun):
            uri = g.get_self(fun)
            self.self_input = Terminal(self, uri, 'self', type=g.get_param_type(uri))
            self.terminals[self.self_input.uri] = self.self_input
        if g.has_output(fun):
            uri = g.get_output(fun)
            self.output = Terminal(self, uri, g.get_output_predicate(fun)[1], type=g.get_output_type(uri), is_output=True)
            self.terminals[self.output.uri] = self.output
        if g.has_self_output(fun):
            uri = g.get_self_output(fun)
            self.self_output = Terminal(self, uri, 'self_output', type=g.get_output_type(uri), is_output=True)
            self.terminals[self.self_output.uri] = self.self_output
        
        ### COMPOSITION ###
        
        self.comp = None
        if g.has_composition(fun):
            # TODO Function is represented by multiple compositions
            self.comp_uri = g.get_compositions(fun)[0]
        else:
            self.comp_uri = None
        
        if internal:
            self.init_composition(g)
        
    def init_composition(self, g):
        if self.comp_uri:
            self.comp = Composition(g, self.comp_uri, self)

    def inputs(self) -> Set[Terminal]:
        return { self.terminals[name] for name in self.terminals if not self.terminals[name].is_output }

    def outputs(self) -> Set[Terminal]:
        return { self.terminals[name] for name in self.terminals if self.terminals[name].is_output }
    
    def execute(self):
        if self.comp:
            self.comp.execute()
        else:            
            # If there is a self input, use the function object from that terminal's value
            if self.self_input is not None:
                self.f_object = getattr(self.self_input.value, self.name, None)
            
            # Only execute when there is a function object
            if self.f_object is not None:
                args = []
                vargs = []
                keyargs = {}
                vkeyargs = {}

                for param in self.inputs():
                    mapping = param.param_mapping
                    value = param.value

                    if mapping.getType() == MappingType.VARPOSITIONAL:
                        for i, val in value.items():
                            vargs.append((i, val))
                    elif mapping.getType() == MappingType.VARKEYWORD:
                        if isinstance(value, dict):
                            vkeyargs = value
                    elif mapping.getType() == MappingType.KEYWORD:
                        keyargs[mapping.getProperty()] = value
                    elif mapping.getType() == MappingType.POSITIONAL:
                        args.append((mapping.getProperty(), value))
                
                # correctly sort the positional arguments
                args = [ x[1] for x in sorted(args, key=lambda x: x[0])]
                vargs = [ x[1] for x in sorted(vargs, key=lambda x: x[0])]

                # Remove the self parameter as we already have the method object
                if self.self_input is not None:
                    if 'self' in keyargs:
                        del keyargs['self']
                    else:
                        args = args[1:]
                
                self.startedAt = datetime.datetime.now()
                ret = self.f_object(*args, *vargs, **keyargs, **vkeyargs)
                self.endedAt = datetime.datetime.now()

                self.output.set_value(ret)
                if self.self_input is not None:
                    self.self_output.set_value(self.self_input.value)
    
    def __getitem__(self, key):
        # Based on parameter URI
        if isinstance(key, URIRef):
            return self.terminals[key]
        
        # Based on parameter predicate
        for ter in self.terminals.values():
            if ter.name == key:
                return ter
        
        raise KeyError(f"No terminal found with key '{key}'")
    
    def __hash__(self) -> int:
        return hash(self.uri)
    
    def __eq__(self, other: object) -> bool:
        return isinstance(other, Function) and self.uri == other.uri

    
class AppliedFunction(Function):
    
    def __init__(self, g: PipelineGraph, call: URIRef, scope: URIRef, internal=False) -> None:
        fun = g.check_call(call)
        super().__init__(g, fun)
        
        self.uri = call
        self.scope = scope
        
        if internal:
            self.init_composition(g)
        
        self._next = None
        self.next, self.iterate, self.iftrue, self.iffalse = g.get_order(call)
    
    def execute(self):
        if self.iterate is not None:
            try:
                super().execute()
                self._next = self.iterate
            except StopIteration:
                self._next = self.next
        elif self.iftrue is not None:
            super().execute()
            self._next = self.iftrue if self.output.value else self.iffalse
    
    def next_function(self):
        return self._next
    
    def __eq__(self, other: object) -> bool:
        return isinstance(other, AppliedFunction) and self.uri == other.uri and self.scope == other.scope