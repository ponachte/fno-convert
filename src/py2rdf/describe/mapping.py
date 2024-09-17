class Mapping:

    def __init__(self, mapfrom: "MappingNode", mapto: "MappingNode") -> None:
        self.mapfrom = mapfrom
        self.mapto = mapto

class MappingNode:

    def __init__(self) -> None:
        self.context = None
        self.parameter = None
        self.output = None
        self.index = None
        self.constant = None
        self.variable = None
    
    def set_function_par(self, context, parameter) -> "MappingNode":
        self.context = context
        self.parameter = parameter
        self.output = None
        self.constant = None
        self.variable = None

        return self
    
    def set_function_out(self, context, output) -> "MappingNode":
        self.context = context
        self.output = output
        self.parameter = None
        self.constant = None
        self.variable = None

        return self
    
    def set_constant(self, constant) -> "MappingNode":
        self.constant = constant
        self.context = None
        self.parameter = None
        self.output = None
        self.variable = None

        return self
    
    def set_variable(self, variable) -> "MappingNode":
        self.variable = variable
        self.constant = None
        self.context = None
        self.parameter = None
        self.output = None

        return self
    
    def get_value(self):
        if self.parameter is not None:
            return self.parameter
        if self.output is not None:
            return self.output
        if self.variable is not None:
            return self.variable
        return self.constant
    
    def set_strategy(self, index: int | str | None) -> "MappingNode":
        self.index = index

        return self
    
    def is_output(self) -> bool:
        return self.output is not None

    def has_map_strategy(self) -> bool:
        return self.index is not None
    
    def from_term(self) -> bool:
        return self.parameter is None and self.output is None and self.variable is None
    
    def is_variable(self) -> bool:
        return self.variable is not None