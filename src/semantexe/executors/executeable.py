from ..graph import ExecutableGraph, get_name
from .store import Mapping, Terminal, ValueStore, ParameterMapping
from rdflib import URIRef
from typing import Set

class Composition:

    def __init__(self, g: ExecutableGraph, comp: URIRef, rep: "Function | AppliedFunction" = None) -> None:
        self.uri = comp
        self.name = get_name(comp)
        self.rep = rep
        
        if rep is None:
            reps = g.get_representations(comp)
            if len(reps) > 1:
                raise Exception(f"Composition has multiple representaitons {reps}")
            elif len(reps) == 1:
                self.rep = reps[0]
            else:
                self.rep = comp

        ### USED FUNCTIONS ###
        self.functions = {}

        # Get all the used functions
        for call in g.get_used_functions(self.uri):
            if call != self.rep.fun_uri and call not in self.functions:
                self.functions[call] = AppliedFunction(g, call, rep)

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
        
        # If this composition represents the internal flow of a function, set the output
        if self.rep:
            self.ingest(self.rep)
        
    
    def ingest(self, fun):
        for input in fun.inputs():
            if input in self.mappings:
                self.mappings[input].execute()            
    
    def get_terminal(self, call, ter):
        return  self.functions[call][ter] if call != self.rep.fun_uri else self.rep[ter]
    
    def json_elk(self, json_elk = None):
        if json_elk is None:
            json_elk = self.rep.json_elk()
         
        json_elk["children"] = []
        child_index_map = {}
        for i, fun in enumerate(self.functions.values()):
            json_elk["children"].append(fun.json_elk())
            child_index_map[fun.id()] = i
            
        json_elk["edges"] = []
        for mapping in self.mappings.values():
            json_elk["edges"].extend(mapping.json_elk())
        
        for fun in self.functions.values():
            # Only visualize control flow for nodes with non-linear control flow
            if fun.iftrue or fun.iffalse or fun.iterate:
                if fun.next:
                    self.json_elk_controlflow(json_elk, child_index_map, fun, self.functions[fun.next], "next")
                if fun.iterate:
                    self.json_elk_controlflow(json_elk, child_index_map, fun, self.functions[fun.iterate], "iterate")
                if fun.iftrue:
                    self.json_elk_controlflow(json_elk, child_index_map, fun, self.functions[fun.iftrue], "iftrue")
                if fun.iffalse:
                    self.json_elk_controlflow(json_elk, child_index_map, fun, self.functions[fun.iffalse], "iffalse")
            # Or nodes at the end of a for-loop
            elif fun.next and self.functions[fun.next].iterate:
                self.json_elk_controlflow(json_elk, child_index_map, fun, self.functions[fun.next], "next")
        
        return json_elk
                
    def json_elk_controlflow(self, json_elk, child_index_map, source, target, label):
        # create ports
        i = child_index_map[source.id()]
        json_elk["children"][i]["ports"].append({
            "id": f"{source.id()}_{label}_out",
            "width": 0,
            "height":0,
            "layoutOptions": {
                "allowNonFlowPortsToSwitchSides": "true",
                "port.side": "SOUTH"
            }
        })
        
        i = child_index_map[target.id()]
        json_elk["children"][i]["ports"].append({
            "id": f"{source.id()}_{label}_in",
            "width": 0,
            "height":0,
            "layoutOptions": {
                "allowNonFlowPortsToSwitchSides": "true",
                "port.side": "SOUTH"
            }
        })
        
        # create edge
        json_elk["edges"].append({
            "id": f"{source.id()}_{target.id()}_{label}",
            "target": target.id(),
            "targetPort": f"{source.id()}_{label}_in",
            "source": source.id(),
            "sourcePort": f"{source.id()}_{label}_out",
            "labels": [{
                "text": label,
                "layoutOptions": {
                    "edgeLabels.placement": "TAIL"
                }
            }]
        })
                
        return json_elk
    
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
    
    def id(self):
        # TODO Format prefix
        return get_name(self.fun_uri)

    def json_elk(self):
        json_elk = {
            "id": self.id(),
            "ports": [ ter.json_elk() for ter in self.terminals.values() ],
            "labels": [{ "text": self.name }],
            "children": [],
            "layoutOptions": {
                "nodeSize.constraints": "[PORTS, PORT_LABELS, NODE_LABELS]",
                "portConstraints": "FIXED_SIDE",
                "portLabels.placement": "[INSIDE]",
                "nodeLabels.placement": "[H_CENTER, V_TOP, INSIDE]",
                "elk.padding": "[top=0.0,left=20.0,bottom=15.0,right=20.0]"
            }
        }
        
        if self.comp:
            json_elk = self.comp.json_elk(json_elk)

        return json_elk
    
    def __hash__(self) -> int:
        return hash(self.fun_uri)
    
    def __eq__(self, other: object) -> bool:
        return isinstance(other, Function) and self.fun_uri == other.fun_uri

    
class AppliedFunction(Function):
    
    def __init__(self, g: ExecutableGraph, call: URIRef, scope: "URIRef | Function | AppliedFunction") -> None:
        fun = g.check_call(call)
        self.call_uri = call
        self.scope = scope
        
        super().__init__(g, fun)
        
        self._next = None
        self.next, self.iterate, self.iftrue, self.iffalse = g.get_order(call)
    
    def next_executeable(self):
        return self._next
    
    def id(self):
        if isinstance(self.scope, (Function, AppliedFunction)):
            return f"{self.scope.id()}_{get_name(self.call_uri)}"
        return f"{get_name(self.scope)}_{get_name(self.call_uri)}"
    
    def json_elk(self):
        json_elk = super().json_elk()
        json_elk["id"] = self.id()
        return json_elk
    
    def __hash__(self) -> int:
        return hash(self.call_uri)
    
    def __eq__(self, other: object) -> bool:
        return isinstance(other, AppliedFunction) and self.call_uri == other.call_uri and self.scope == other.scope