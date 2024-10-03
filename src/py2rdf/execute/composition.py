from abc import abstractmethod
from ..graph import PipelineGraph, get_name
from .process import Function, Constant
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
        self.flow = flow
        flow.compositions[comp] = self
        self.process = set()
        self.name = get_name(comp)

        ### USED FUNCTIONS ###

        # Get all functions used inside the composition
        # TODO IfFlowComposition without mappings but with a composition !!
        for (call, fun) in g.get_used_functions(self.uri):
            if fun != flow.f_uri and call not in flow.functions:
                flow.functions[call] = Function(g, call, fun, flow.scope)
            if g.in_composition(comp, call):
                self.process.add(flow.functions[call])
            if g.has_flow(fun):
                flow.add_internal_flow(g, flow.functions[call])

        ### MAPPINGS ###

        self.mappings = set()

        for f1, par1, f2, par2 in g.get_mappings(comp):
            ter1 = flow.get_terminal(f1, par1)
            ter2 = flow.get_terminal(f2, par2)
            self.mappings.add(Mapping(ter1, ter2))
        
        for const_value, const_type, f, par in g.get_term_mappings(comp):
            const = Constant(const_value, const_type)
            flow.constants.add(const)
            self.process.add(const)
            ter2 = flow.get_terminal(f, par)
            self.mappings.add(Mapping(const.output, ter2))
        
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

        ### INTERNAL FLOWS ###

        for fun in self.process:
            if fun in flow.internal_flows:
                int_flow = flow.internal_flows[fun]
                int_flow.connect_links(fun, self)
                int_flow.close()
        
        ### PROCESSING ORDER ###
        
        self.calculate_order()
    
    def calculate_order(self):
        # Maak een dict die bijhoudt hoeveel afhankelijkheden elke functie heeft
        in_degree = {func: 0 for func in self.process}
        
        # Bereken de in-degree (aantal afhankelijkheden) voor elke functie
        for func in self.process:
            in_degree[func] = len(func.depends_on(self.process))

        # Begin met functies die geen afhankelijkheden hebben (in-degree == 0)
        no_dependencies = [func for func in self.process if in_degree[func] == 0]
        order = []  # Dit zal de topologische sortering bevatten

        while no_dependencies:
            # Haal een functie zonder afhankelijkheden
            func = no_dependencies.pop()
            order.append(func)

            # Verlaag de in-degree van alle functies die afhankelijk zijn van deze functie
            for dependent in self.process:
                if func in dependent.depends_on(self.process):
                    in_degree[dependent] -= 1
                    # Als deze functie nu geen afhankelijkheden meer heeft, voeg het toe aan de lijst
                    if in_degree[dependent] == 0:
                        no_dependencies.append(dependent)

        # Controleer of alle functies zijn verwerkt
        if len(order) != len(self.process):
            raise ValueError("A circular dependency has been found. No topological sorting can be done.")
        
        self.process = order
    
    def execute(self):
        for fun in self.process:
            if not fun.closed:
                fun.execute()
            else:
                self.flow.internal_flows[fun].execute()
    
    def __hash__(self) -> int:
        return hash(self.uri)
    
    def __eq__(self, other: object) -> bool:
        return isinstance(other, Composition) and self.uri == other.uri
    
    @abstractmethod
    def next(self):
        pass

    @abstractmethod
    def control_flows(self):
        pass

class LinearComposition(Composition):
        
    def __init__(self, flow, g: PipelineGraph, comp: URIRef) -> None:
        self.name = "Block"
        super().__init__(flow, g, comp)
        
        ### FOLLOWED BY ###

        next_comp = g.followed_by(comp)
        self.followed_by = flow.compositions.get(next_comp, Composition.build_composition(flow, g, next_comp))
    
    def next(self):
        return self.followed_by

    def control_flows(self):
        return [(self.followed_by, 'FOLLOWED BY')]

class IfFlowComposition(Composition):

    def __init__(self, flow, g: PipelineGraph, comp: URIRef) -> None:
        self.name = "If"
        super().__init__(flow, g, comp)

        ### CONDITION ###

        f, par = g.get_condition(comp)
        self.condition = flow.functions[f].terminals[par]
        if g.in_composition(comp, f, full=False):
            self.process.append(flow.functions[f])

        ### IF TRUE ###

        next_comp = g.if_true(comp)
        self.if_true = flow.compositions.get(next_comp, Composition.build_composition(flow, g, next_comp))

        ### IF FALSE ###

        next_comp = g.if_false(comp)
        self.if_false = flow.compositions.get(next_comp, Composition.build_composition(flow, g, next_comp))
    
    def next(self):
        if self.condition.value:
            return self.if_true
        return self.if_false
    
    def control_flows(self):
        return [(self.if_true, 'IF TRUE'), (self.if_false, 'IF FALSE')]

class ForFlowComposition(Composition):

    def __init__(self, flow, g: PipelineGraph, comp: URIRef) -> None:
        self.name = "For"
        super().__init__(flow, g, comp)

        ### ITERATOR ###

        f, par = g.get_iterator(comp)
        self.iterator = flow.functions[f].terminals[par]
        if g.in_composition(comp, f):
            self.process.add(flow.functions[f])

        ### IF NEXT ###

        next_comp = g.if_next(comp)
        self.if_next = flow.compositions.get(next_comp, Composition.build_composition(flow, g, next_comp))

        ### FOLLOWED BY ###

        next_comp = g.followed_by(comp)
        self.followed_by = flow.compositions.get(next_comp, Composition.build_composition(flow, g, next_comp))
    
    def control_flows(self):
        return [(self.if_next, 'IF NEXT'), (self.followed_by, 'FOLLOWED BY')]