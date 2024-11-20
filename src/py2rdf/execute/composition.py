from abc import abstractmethod
from ..graph import PipelineGraph, get_name
from ..map import ImpMap
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
            if fun != call and call not in flow.functions:
                flow.functions[call] = Function(g, call, fun, flow.scope)
            if g.in_composition(comp, call):
                self.process.add(flow.functions[call])
            if fun != flow.f_uri and g.has_flow(fun):
                flow.add_internal_flow(g, flow.functions[call])

        ### MAPPINGS ###

        self.mappings = set()
        
        for mapfrom, mapto in g.get_mappings(comp):
            # Handle mapfrom
            if g.is_function_mapping(mapfrom):
                source = flow.get_terminal(*g.get_function_mapping(mapfrom))
            elif g.is_term_mapping(mapfrom):
                const = Constant(mapfrom.value, ImpMap.rdf_to_imp(g, mapfrom.datatype))
                flow.constants.add(const)
                self.process.add(const)
                source = const.output
            elif g.is_var_mapping(mapfrom):
                if mapfrom not in flow.variables:
                    flow.variables[mapfrom] = Variable(mapfrom)
                source = flow.variables[mapfrom]
            
            # Handle mapto
            if g.is_function_mapping(mapto):
                target = flow.get_terminal(*g.get_function_mapping(mapto))
            elif g.is_var_mapping(mapto):
                if mapto not in flow.variables:
                    flow.variables[mapto] = Variable(mapto)
                target = flow.variables[mapto]
            
            self.mappings.add(Mapping(source, target))

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
            if fun in self.flow.internal_flows:
                self.flow.internal_flows[fun].execute()
            else:
                fun.execute()
    
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
        if next_comp in flow.compositions:
            next_comp = flow.compositions[next_comp]
        else:
            next_comp = Composition.build_composition(flow, g, next_comp)
        self.followed_by = next_comp
    
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
        self.condition = flow.get_terminal(f, par)
        if g.in_composition(comp, f, full=False):
            self.process.append(flow.functions[f])

        ### IF TRUE ###

        next_comp = g.if_true(comp)
        if next_comp in flow.compositions:
            next_comp = flow.compositions[next_comp]
        else:
            next_comp = Composition.build_composition(flow, g, next_comp)
        self.if_true = next_comp

        ### IF FALSE ###

        next_comp = g.if_false(comp)
        if next_comp in flow.compositions:
            next_comp = flow.compositions[next_comp]
        else:
            next_comp = Composition.build_composition(flow, g, next_comp)
        self.if_false = next_comp
    
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

        f, _ = g.get_iterator(comp)
        self.iterator = flow.functions[f]
        self.hasNext = None
        if g.in_composition(comp, f, full=False):
            self.process.append(flow.functions[f])

        ### IF NEXT ###

        next_comp = g.if_next(comp)
        if next_comp in flow.compositions:
            next_comp = flow.compositions[next_comp]
        else:
            next_comp = Composition.build_composition(flow, g, next_comp)
        self.if_next = next_comp

        ### FOLLOWED BY ###

        next_comp = g.followed_by(comp)
        if next_comp in flow.compositions:
            next_comp = flow.compositions[next_comp]
        else:
            next_comp = Composition.build_composition(flow, g, next_comp)
        self.followed_by = next_comp
    
    def execute(self):
        try:
            if self.hasNext is None:
                super().execute()
            else:
                self.iterator.execute()
            self.hasNext = True
        except StopIteration:
            self.hasNext = False
           
    def next(self):        
        if self.hasNext:
            return self.if_next
        return self.followed_by
        
    def control_flows(self):
        return [(self.if_next, 'IF NEXT'), (self.followed_by, 'FOLLOWED BY')]