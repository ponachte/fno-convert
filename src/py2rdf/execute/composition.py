from abc import abstractmethod
from ..graph import PipelineGraph, get_name
from ..map import ImpMap
from .process import Function, Constant
from .store import Mapping, Variable
from rdflib import URIRef

class Composition:

    def __init__(self, g: PipelineGraph, comp: URIRef, exe) -> None:
        self.uri = comp
        
        reps = g.get_representations(comp)
        if len(reps) > 1:
            raise Exception(f"Composition has multiple representaitons {reps}")
        elif len(reps) == 1:
            self.scope = reps[0]
        else:
            self.scope = comp

        self.functions = set()
        self.name = get_name(comp)

        ### USED FUNCTIONS ###

        # Get all the used functions
        for (call, fun) in g.get_used_functions(self.uri):
            if fun != call and call not in exe.functions:
                exe.functions[call] = Function(g, call, fun, self.scope)
                self.functions.add(exe.functions[call])
            if fun != self.scope and g.has_composition(fun):
                exe.add_internal_flow(g, exe.functions[call])

        ### MAPPINGS ###

        self.mappings = set()
        
        for mapfrom, mapto in g.get_mappings(comp):
            # Handle mapfrom
            if g.is_function_mapping(mapfrom):
                source = exe.get_terminal(*g.get_function_mapping(mapfrom))
            elif g.is_term_mapping(mapfrom):
                const = Constant(mapfrom.value, ImpMap.rdf_to_imp(g, mapfrom.datatype))
                exe.constants.add(const)
                self.functions.add(const)
                source = const.output
            
            # Handle mapto
            if g.is_function_mapping(mapto):
                target = exe.get_terminal(*g.get_function_mapping(mapto))
            
            self.mappings.add(Mapping(source, target))

        ### INTERNAL FLOWS ###

        for fun in self.used_functions:
            if fun in exe.internal_flows:
                int_flow = exe.internal_flows[fun]
                int_flow.connect_links(fun, self)
                int_flow.close()
        
        ### PROCESSING ORDER ###
        
        self.calculate_order()
    
    def calculate_order(self):
        # Maak een dict die bijhoudt hoeveel afhankelijkheden elke functie heeft
        in_degree = {func: 0 for func in self.used_functions}
        
        # Bereken de in-degree (aantal afhankelijkheden) voor elke functie
        for func in self.used_functions:
            in_degree[func] = len(func.depends_on(self.used_functions))

        # Begin met functies die geen afhankelijkheden hebben (in-degree == 0)
        no_dependencies = [func for func in self.used_functions if in_degree[func] == 0]
        order = []  # Dit zal de topologische sortering bevatten

        while no_dependencies:
            # Haal een functie zonder afhankelijkheden
            func = no_dependencies.pop()
            order.append(func)

            # Verlaag de in-degree van alle functies die afhankelijk zijn van deze functie
            for dependent in self.used_functions:
                if func in dependent.depends_on(self.used_functions):
                    in_degree[dependent] -= 1
                    # Als deze functie nu geen afhankelijkheden meer heeft, voeg het toe aan de lijst
                    if in_degree[dependent] == 0:
                        no_dependencies.append(dependent)

        # Controleer of alle functies zijn verwerkt
        if len(order) != len(self.used_functions):
            raise ValueError("A circular dependency has been found. No topological sorting can be done.")
        
        self.used_functions = order
    
    def execute(self):
        for fun in self.used_functions:
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
            self.used_functions.append(flow.functions[f])

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
            self.used_functions.append(flow.functions[f])

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