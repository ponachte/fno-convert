from ..graph import PipelineGraph, get_name
from .processable import Function, Constant
from .store import Mapping, Variable
from rdflib import URIRef

class Composition:

    @staticmethod
    def build_composition(flow, g: PipelineGraph, comp: URIRef) -> "Composition":
        if comp is None:
            return
        if g.is_composition(comp):
            return LinearComposition(flow, g, comp)
        if g.is_if_composition(comp):
            return IfFlowComposition(flow, g, comp)
        if g.is_for_composition(comp):
            return ForFlowComposition(flow, g, comp)

    def __init__(self, flow, g: PipelineGraph, comp: URIRef) -> None:
        self.uri = comp
        flow.compositions[comp] = self
        self.functions = []

        ### USED FUNCTIONS ###

        # Get all functions used inside the composition
        # TODO IfFlowComposition without mappings but with a composition !!
        for (call, fun) in g.get_used_functions(self.uri):
            if fun != flow.f_uri and call not in flow.functions:
                flow.functions[call] = Function(g, call, fun, flow.scope)
            if g.in_composition(comp, call):
                self.functions.append(flow.functions[call])

        ### MAPPINGS ###

        self.mappings = set()

        for f1, par1, f2, par2 in g.get_mappings(comp):
            ter1 = flow.get_terminal(f1, par1)
            ter2 = flow.get_terminal(f2, par2)
            self.mappings.add(Mapping(ter1, ter2))
        
        for const_value, const_type, f, par in g.get_term_mappings(comp):
            const = Constant(const_value, const_type)
            ter1 = const.output
            ter2 = flow.get_terminal(f, par)
            self.mappings.add(Mapping(ter1, ter2))
        
        for var, f, par in g.get_fromvar_mappings(comp):
            if var not in flow.variables:
                flow.variables[var] = Variable(var)
            ter1 = flow.variables[var]
            ter2 = flow.get_terminal(f, par)
            self.mappings.add(Mapping(ter1, ter2))
        
        for f, par, var in g.get_tovar_mappings(comp):
            if var not in flow.variables:
                flow.variables[var] = Variable(var)
            ter1 = flow.get_terminal(f, par)
            ter2 = flow.variables[var]
            self.mappings.add(Mapping(ter1, ter2))
    
    def __hash__(self) -> int:
        return hash(self.uri)
    
    def __eq__(self, other: object) -> bool:
        return isinstance(other, Composition) and self.uri == other.uri

class LinearComposition(Composition):
        
    def __init__(self, flow, g: PipelineGraph, comp: URIRef) -> None:
        self.name = "Block"
        super().__init__(flow, g, comp)
        
        ### FOLLOWED BY ###

        next_comp = g.followed_by(comp)
        self.followed_by = flow.compositions.get(next_comp, Composition.build_composition(flow, g, next_comp))

class IfFlowComposition(Composition):

    def __init__(self, flow, g: PipelineGraph, comp: URIRef) -> None:
        self.name = "If"
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

    def __init__(self, flow, g: PipelineGraph, comp: URIRef) -> None:
        self.name = "For"
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