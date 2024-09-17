from ..graph import PipelineGraph
from ..map import ImpMap
from rdflib import URIRef

class FlowExecuter:

    def __init__(self) -> None:
        pass

    def execute_flow(self):
        pass

class Flow:

    def __init__(self, g: PipelineGraph, fun: URIRef) -> None:
        self.f_uri = fun

        self.functions = { fun: Function(g, fun, fun) }
        self.variables = {}
        self.compositions = {}

        self.start = Composition.build_composition(self, g, g.start_of_flow(fun))

class Composition:

    @staticmethod
    def build_composition(flow: "Flow", g: PipelineGraph, comp: URIRef) -> "Composition":
        if g.is_composition(comp):
            return LinearComposition(flow, g, comp)
        if g.is_if_composition(comp):
            return IfFlowComposition(flow, g, comp)
        if g.is_for_composition(comp):
            return ForFlowComposition(flow, g, comp)

    def __init__(self, flow: "Flow", g: PipelineGraph, comp: URIRef) -> None:
        self.uri = comp
        flow.compositions[comp] = self

        ### USED FUNCTIONS ###

        # Get all functions used inside the composition
        # TODO IfFlowComposition without mappings but with a composition !!
        flow.functions.update({
            call: Function(g, call, fun) 
            for (call, fun) in g.get_used_functions(self.uri) 
            if call not in flow.functions
        })

        ### MAPPINGS ###

        self.mappings = set()

        for f1, par1, f2, par2 in g.get_mappings(comp):
            ter1 = flow.functions[f1].terminals[par1]
            ter2 = flow.functions[f2].terminals[par2]
            self.mappings.add(Mapping(ter1, ter2))
        
        for const_value, const_type, f, par in g.get_term_mappings(comp):
            const = Constant(const_value, const_type)
            ter1 = const.output
            ter2 = flow.functions[f].terminals[par]
            self.mappings.add(Mapping(ter1, ter2))
        
        for var, f, par in g.get_fromvar_mappings(comp):
            if var not in flow.variables:
                flow.variables[var] = Variable(var)
            ter1 = flow.variables[var]
            ter2 = flow.functions[f].terminals[par]
            self.mappings.add(Mapping(ter1, ter2))
        
        for f, par, var in g.get_tovar_mappings(comp):
            if var not in flow.variables:
                flow.variables[var] = Variable(var)
            ter1 = flow.functions[f].terminals[par]
            ter2 = flow.variables[var]
            self.mappings.add(Mapping(ter1, ter2))

class LinearComposition(Composition):
        
    def __init__(self, flow: Flow, g: PipelineGraph, comp: URIRef) -> None:
        super().__init__(flow, g, comp)
        
        ### FOLLOWED BY ###

        next_comp = g.followed_by(comp)
        self.followed_by = flow.compositions.get(next_comp, Composition.build_composition(flow, g, next_comp))

class IfFlowComposition(Composition):

    def __init__(self, flow: Flow, g: PipelineGraph, comp: URIRef) -> None:
        super().__init__(flow, g, comp)

        ### CONDITION ###

        f, par = g.get_condition(comp)
        self.condition = flow.functions[f].terminals[par]

        ### IF TRUE ###

        next_comp = g.if_true(comp)
        self.if_true = flow.compositions.get(next_comp, Composition.build_composition(flow, g, next_comp))

        ### IF FALSE ###

        next_comp = g.if_false(comp)
        self.if_true = flow.compositions.get(next_comp, Composition.build_composition(flow, g, next_comp))

class ForFlowComposition(Composition):

    def __init__(self, flow: Flow, g: PipelineGraph, comp: URIRef) -> None:
        super().__init__(flow, g, comp)

        ### ITERATOR ###

        f, par = g.get_iterator(comp)
        self.iterator = flow.functions[f].terminals[par]

        ### IF NEXT ###

        next_comp = g.if_next(comp)
        self.if_next = flow.compositions.get(next_comp, Composition.build_composition(flow, g, next_comp))

        ### FOLLOWED BY ###

        next_comp = g.followed_by(comp)
        self.followed_by = flow.compositions.get(next_comp, Composition.build_composition(flow, g, next_comp))

class Function:

    def __init__(self, g: PipelineGraph, call: URIRef, fun: URIRef) -> None:
        self.call_uri = call
        self.fun_uri = fun
        self.imp_uri = g.get_implementation(fun)

        ### FUNCTION OBJECT ###

        self.f_object = ImpMap.rdf_to_imp(self.imp_uri)

        ### TERMINALS ###

        self.terminals = { par: Terminal(par, g.get_param_predicate(par), type=g.get_param_type(par)) for par in g.get_parameters(fun) }
        self.self_input = None
        self.self_output = None
        self.output = None
        if g.has_self(fun):
            uri = g.get_self(fun)
            self.self_input = Terminal(uri, 'self', type=g.get_param_type(uri))
            self.terminals[self.self_input.uri] = self.self_input
        if g.has_output(fun):
            uri = g.get_output(fun)
            self.output = Terminal(uri, g.get_output_predicate(fun), type=g.get_output_type(uri), is_output=True)
            self.terminals[self.output.uri] = self.output
        if g.has_self_output(fun):
            uri = g.get_self_output(fun)
            self.self_output = Terminal(uri, 'self_output', type=g.get_output_type(uri), is_output=True)
            self.terminals[self.self_output.uri] = self.self_output

class Constant:

    def __init__(self, value, type) -> None:
        self.output = Terminal(None, 'value', value, type, is_output=False)

class Mapping:

    def __init__(self, source: "ValueStore", target: "ValueStore") -> None:
        self.source = source
        self.target = target
        source.connect_to(target, self)

class ValueStore:

    def __init__(self, value=None, type=None) -> None:
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

    def __init__(self, uri: URIRef, name: str, value=None, type=None, is_output=False) -> None:
        super().__init__(value, type)
        self.uri = uri
        self.name = name
        self.is_output = is_output

class Variable(ValueStore):

    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name