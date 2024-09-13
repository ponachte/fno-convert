class Mapping:

    def __init__(self, mapfrom: "MappingNode", mapto: "MappingNode") -> None:
        self.mapfrom = mapfrom
        self.mapto = mapto
        self.conditions = {}
        self.conditions.update(mapfrom.conditions)
        self.conditions.update(mapto.conditions)
    
    def get_conditions(self, conditions={}) -> dict:
        self.conditions.update(conditions)
        return self.conditions

class MappingNode:

    def __init__(self) -> None:
        self.context = None
        self.parameter = None
        self.output = None
        self.index = None
        self.constant = None
        self.conditions = {}
    
    def set_function_par(self, context, parameter) -> "MappingNode":
        self.context = context
        self.parameter = parameter
        self.output = None
        self.constant = None

        return self
    
    def set_function_out(self, context, output) -> "MappingNode":
        self.context = context
        self.output = output
        self.parameter = None
        self.constant = None

        return self
    
    def get_value(self):
        if self.parameter is not None:
            return self.parameter
        if self.output is not None:
            return self.output
        return self.constant
    
    def set_constant(self, constant) -> "MappingNode":
        self.constant = constant
        self.context = None
        self.parameter = None
        self.output = None

        return self
    
    def set_strategy(self, index: int | str | None) -> "MappingNode":
        self.index = index

        return self

    def add_conditions(self, conditions: dict) -> "MappingNode":
        self.conditions.update(conditions)

        return self
    
    def is_output(self) -> bool:
        return self.output is not None

    def has_map_strategy(self) -> bool:
        return self.index is not None
    
    def from_term(self) -> bool:
        return self.parameter is None and self.output is None