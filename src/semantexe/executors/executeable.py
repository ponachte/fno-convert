from ..graph import ExecutableGraph, get_name
from .store import Mapping, Terminal, ValueStore, ParameterMapping
from rdflib import URIRef
from typing import Set

class Composition:

    def __init__(self, g: ExecutableGraph, comp: URIRef, rep: "Function" = None) -> None:
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
            self.scope = rep.fun_uri

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
                source = ValueStore(mapfrom.datatype)
                source.set(mapfrom.value)
            
            # Handle mapto
            call, ter = g.get_function_mapping(mapto)
            target = self.get_terminal(call, ter)
            
            # Group mappings by target
            if target not in self.mappings:
                self.mappings[target] = []
            src_strat, src_key = g.get_strategy(mapfrom)
            tar_strat, tar_key = g.get_strategy(mapto)
            self.mappings[target].append((source, priority, src_strat, src_key, tar_strat, tar_key))
        
        # Create mapping for each target    
        for target, sources in self.mappings.items():
            self.mappings[target] = Mapping(sources, target)
            for source in sources:
                priority = source[1]
                if priority not in self.priorities:
                    self.priorities[priority] = self.mappings[target]
        
        ### EXECUTION START ###
        self.start = g.get_start(comp)
    
    def execute(self, executor):
        # Execute each function and follow the control flow until no new function can be selected
        call = self.start
        while call is not None:
            # Get the FnO Function Executeable
            fun = self.functions[call]
            # Fetch inputs from mappings
            self.ingest(fun)
            # Execute
            executor.execute_applied(fun)
            # Signify execution to relevant mappings
            if call in self.priorities:
                for mapping in self.priorities[call]:
                    mapping.set_priority(call)
            # Get the URI of the next executeable
            call = fun.next_executeable()
        
    
    def ingest(self, fun):
        for input in fun.inputs():
            if input in self.mappings:
                self.mappings[input].execute()            
    
    def get_terminal(self, call, ter):
        return  self.functions[call][ter] if call != self.scope else self.rep[ter]
    
    def __hash__(self) -> int:
        return hash(self.uri)
    
    def __eq__(self, other: object) -> bool:
        return isinstance(other, Composition) and self.uri == other.uri

class Function:

    def __init__(self, g: ExecutableGraph, fun: URIRef, map: URIRef = None, imp: URIRef = None, internal=True) -> None:
        self.fun_uri = fun
        self.name = g.get_name(fun)
        self.map = map
        self.imp = imp

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
            self.self_input = Terminal(self, uri, 'self', 
                                       type=g.get_param_type(uri), 
                                       param_mapping=ParameterMapping(g, fun, uri))
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
        
        if g.has_composition(fun):
            # TODO Function is represented by multiple compositions
            self.comp_uri = g.get_compositions(fun)[0]
            if internal:
                self.comp = Composition(g, self.comp_uri, self)
        else:
            self.comp_uri = None
            self.comp = None

    def inputs(self) -> Set[Terminal]:
        return { self.terminals[name] for name in self.terminals if not self.terminals[name].is_output }

    def outputs(self) -> Set[Terminal]:
        return { self.terminals[name] for name in self.terminals if self.terminals[name].is_output }
    
    def __getitem__(self, key) -> Terminal:
        # Based on parameter URI
        if isinstance(key, URIRef):
            return self.terminals[key]
        
        # Based on parameter predicate
        for ter in self.terminals.values():
            if ter.name == key:
                return ter
        
        raise KeyError(f"No terminal found with key '{key}'")
    
    def __hash__(self) -> int:
        return hash(self.fun_uri)
    
    def __eq__(self, other: object) -> bool:
        return isinstance(other, Function) and self.fun_uri == other.fun_uri

    
class AppliedFunction(Function):
    
    def __init__(self, g: ExecutableGraph, call: URIRef, scope: URIRef, internal=False) -> None:
        fun = g.check_call(call)
        super().__init__(g, fun)
        
        self.call_uri = call
        self.scope = scope
        
        if internal:
            self.init_composition(g)
        
        self._next = None
        self.next, self.iterate, self.iftrue, self.iffalse = g.get_order(call)
    
    def next_executeable(self):
        return self._next
    
    def __hash__(self) -> int:
        return hash(self.call_uri)
    
    def __eq__(self, other: object) -> bool:
        return isinstance(other, AppliedFunction) and self.call_uri == other.call_uri and self.scope == other.scope