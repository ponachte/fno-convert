from datetime import datetime
from ..graph import PipelineGraph, get_name
from ..map import ImpMap
from .store import Terminal, ParameterMapping, MappingType, Variable
from rdflib import URIRef
from typing import Set
from PyQt6.QtCore import QObject, pyqtSignal

class Process(QObject):

    statusChanged = pyqtSignal(bool)

    def __init__(self, name='') -> None:
        super().__init__()
        self.name = name

        ### TERMINALS ###

        self.terminals = {}
        self.self_input = None
        self.self_output = None
        self.output = None

        ### EXECUTION DETAILS ###

        self.closed = False

    def inputs(self) -> Set[Terminal]:
        return { self.terminals[name] for name in self.terminals if not self.terminals[name].is_output }

    def outputs(self) -> Set[Terminal]:
        return { self.terminals[name] for name in self.terminals if self.terminals[name].is_output }
    
    def depends_on(self, context) -> Set["Process"]:
        return { dep.fun for input in self.inputs() for dep in input.depends_on if isinstance(dep, Process) and dep.fun in context }
    
    def execute(self):
        { input.setValue(dep.value) for input in self.inputs() for dep in input.depends_on if isinstance(dep, Variable) }
    
    def propagate(self):
        for output in self.outputs():
            output.propagate()
    
    def open(self):
        self.closed = False
        self.statusChanged.emit(False)
    
    def close(self):
        self.closed = True
        self.statusChanged.emit(True)
    
    def __hash__(self) -> int:
        return hash(self.name)
    
    def __eq__(self, other: object) -> bool:
        return isinstance(other, Function) and self.name == other.name
    
class ObjectProcess(Process):

    def __init__(self, g: PipelineGraph, call: URIRef, fun: URIRef, scope: URIRef) -> None:
        super().__init__(get_name(fun if call is None else call))
        self.call_uri = call
        self.fun_uri = fun
        self.scope_uri = scope
        self.map_uri, self.imp_uri = g.get_implementation(fun)

        ### FUNCTION OBJECT ###

        self.f_object = ImpMap.rdf_to_imp(g, self.imp_uri)
    
    def __hash__(self) -> int:
        return hash(self.fun_uri)
    
    def __eq__(self, other: object) -> bool:
        return isinstance(other, Function) and self.call_uri == other.call_uri and self.fun_uri == other.fun_uri and self.scope_uri == other.scope_uri

class Function(ObjectProcess):

    def __init__(self, g: PipelineGraph, call: URIRef, fun: URIRef, scope: URIRef) -> None:
        super().__init__(g, call, fun, scope)

        ### TERMINALS ###

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
    
    def execute(self):
        super().execute()
        
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
            
            self.startedAt = datetime.now()
            ret = self.f_object(*args, *vargs, **keyargs, **vkeyargs)
            self.endedAt = datetime.now()

            self.output.setValue(ret)
            if self.self_input is not None:
                self.self_output.setValue(self.self_input.value)
        
        self.propagate()
    
class FunctionLink(ObjectProcess):

    def __init__(self, g: PipelineGraph, fun: URIRef, scope: URIRef, outer_fun: Function=None, is_output=False) -> None:
        super().__init__(g, None, fun, scope)
        self.is_output = is_output
        self.outer_fun = outer_fun
        self.links = {}

        if is_output:
            # Output terminals as input
            if g.has_output(fun):
                uri = g.get_output(fun)
                self.output = Terminal(self, uri, g.get_output_predicate(fun)[1], type=g.get_output_type(uri))
                self.terminals[self.output.uri] = self.output

                if outer_fun is not None:
                    link_uri = URIRef(f"{uri}_link")
                    link = Terminal(self, link_uri, g.get_output_predicate(fun)[1], type=g.get_output_type(uri), is_output=True)
                    self.links[self.output.uri] = link

            if g.has_self_output(fun):
                uri = g.get_self_output(fun)
                self.self_output = Terminal(self, uri, 'self_output', type=g.get_output_type(uri))
                self.terminals[self.self_output.uri] = self.self_output

                if outer_fun is not None:
                    link_uri = URIRef(f"{uri}_link")
                    link = Terminal(self, link_uri, 'self_output', type=g.get_output_type(uri), is_output=True)
                    self.links[self.self_output.uri] = link
        else:
            # Input terminals as output
            for par in g.get_parameters(fun):
                self.terminals[par] = Terminal(self, par, g.get_predicate(par), type=g.get_param_type(par), is_output=True)

                if outer_fun is not None:
                    link_uri = URIRef(f"{par}_link")
                    link = Terminal(self, link_uri, g.get_predicate(par), type=g.get_param_type(par))
                    self.links[par] = link

            if g.has_self(fun):
                uri = g.get_self(fun)
                self.self_input = Terminal(self, uri, 'self', type=g.get_param_type(uri), is_output=True)
                self.terminals[self.self_input.uri] = self.self_input

                if outer_fun is not None:
                    link_uri = URIRef(f"{uri}_link")
                    link = Terminal(self, link_uri, 'self', type=g.get_param_type(uri))
                    self.links[self.self_input.uri] = link
    
    def execute(self):
        super().execute()
        
        for uri, term in self.links.items():
            if self.is_output:
                term.setValue(self.terminals[uri].value)
                if self.outer_fun is not None:
                    self.outer_fun.output.setValue(term.value)
            else:
                self.terminals[uri].setValue(term.value)
        self.propagate()
    
    def inputs(self) -> Set[Terminal]:
        if self.is_output:
            return super().inputs()
        return { self.links[term] for term in self.links if not self.links[term].is_output }
    
    def outputs(self) -> Set[Terminal]:
        if not self.is_output:
            return super().outputs()
        return { self.links[term] for term in self.links if self.links[term].is_output }

class Constant(Process):

    count = 0

    def __init__(self, value, type) -> None:
        super().__init__("const")
        self.output = Terminal(self, None, 'value', value, type, is_output=True)

        # Unique identifier
        self.count = Constant.count
        Constant.count += 1
    
    def outputs(self) -> Set[Terminal]:
        return { self.output }
    
    def execute(self):
        self.propagate()
    
    def __hash__(self) -> int:
        return hash(self.count)
    
    def __eq__(self, other: object) -> bool:
        return isinstance(other, Constant) and self.count == other.count