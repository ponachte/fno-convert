import inspect
import builtins
import traceback
import ast

from operator import (__add__, __and__, __contains__, __eq__, __floordiv__, __ge__, __getitem__, __gt__, 
                      __iadd__, __iand__, __ifloordiv__, __ilshift__, __imatmul__, __imod__, __imul__, __invert__, 
                      __ior__, __ipow__, __irshift__, __isub__, __itruediv__, __ixor__, __le__, __lshift__, __lt__, 
                      __matmul__, __mod__, __mul__, __ne__, __neg__, __not__, __or__, __pos__, __pow__, __rshift__,
                        __setitem__, __sub__, __truediv__, __xor__)

from scalpel.cfg.builder import CFGBuilder
from scalpel.cfg.model import Block

from rdflib import URIRef

from .mapping import Mapping, MappingNode
from .importer import Importer
from .fno_builder import FnOBuilder
from ..graph import PipelineGraph, to_uri, get_name
from ..map import ImpMap, PrefixMap

class CompositionDescriptor:

    @staticmethod
    def name_node(name: str):
        return ast.Name(id=name, ctx=ast.Load())

    def from_function(self, fun, max_depth=3):
        self.g = PrefixMap.bind_namespaces(PipelineGraph())
        self.importer = Importer()

        self.scope = None
        self.block = None

        self.fun_cfgs = {}
        self.f_counter = {}
        self.assigned = {}
        self.used_by = {}
        self.default_map = {}
        self.var_types = {}
        self.returns = []
        self.mappings = []
        self.iterators = {}
        self.conditions = {}
        self.prev_function = (None, None)
        self.start = None

        self.depth = 0
        self.max_depth = max_depth

        self.uri = self.describe_composition(fun.__name__, fun.__name__, fun)

        return self.g, self.uri
    
    def get_flow(self):
        return self.g, self.uri
    
    def get_type(self, var):
        """
        Retrieves the stored type of a given variable, if available.

        This method attempts to find and return the type of a variable that has been propagated
        through the system. It first checks if the type is directly stored in `self.var_types`.
        If the type is not found, it checks if the variable is assigned to the output of a function
        that has a stored type.

        Parameters:
        -----------
        var : Any
            The variable for which the type is to be retrieved.

        Returns:
        --------
        type or None
            The stored type of the variable if available; otherwise, None.
        """
        
        # Check if the type of the variable is directly stored
        if var in self.var_types:
            # Return None if no type annotation was found (inspect._empty)
            if self.var_types[var] is inspect._empty:
                return None
            return self.var_types[var]
        
        # Check if the variable is assigned to the output of a function with a stored type
        if var in self.assigned:
            return self.get_type(self.assigned[var].get_value())
        
        # Return None if no type information is found
        return None

    def describe_composition(self, name, context, fun, num=0, keywords=[]):

        ### IMPORTS ###

        try:
            self.importer.import_from_function(fun)
        except Exception as e:
            print(f"Error importing from {name}: {e}")
            print(traceback.format_exc())

        ### FUNCTION DESCRIPTION ###

        s = self.function_to_rdf(name, context, fun, num, keywords)

        ### FLOW ###

        try:
            src = inspect.getsource(fun)
            def_cfg = CFGBuilder().build_from_src(fun.__name__, src)

            for (_, fun_name), fun_cfg in def_cfg.functioncfgs.items():
                if fun_name == fun.__name__:
                    self.fun_cfgs[fun] = fun_cfg
                    dot = fun_cfg.build_visual('png')
                    dot.render(f"cfg_diagrams/{fun_name}_cfg_diagram", view=False)

                    # Store current scope
                    prev_scope = self.scope
                    prev_assigned = self.assigned
                    prev_used = self.used_by
                    prev_returns = self.returns
                    prev_types = self.var_types
                    prev_mappings = self.mappings
                    prev_iterators = self.iterators
                    prev_conditions = self.conditions
                    prev_prev_function = self.prev_function
                    prev_start = self.start

                    # Enter scope of function
                    self.scope = s
                    self.assigned = {}
                    self.used_by = {}
                    self.returns = []
                    self.var_types = {}
                    self.mappings = []
                    self.iterators = {}
                    self.conditions = {}
                    self.prev_function = (None, None)
                    self.start = None

                    # Assign parameters to function arguments
                    parameters = self.g.get_param_predicates(s)
                    for par, pred in parameters:
                        self.handle_assignment(MappingNode().set_function_par(s, par), [self.name_node(pred)])                   

                    # Iterate blocks
                    for block in fun_cfg:
                        self.handle_block(block)
                
                    # Handle returns
                    self.handle_returns()

                    # Create composition
                    comp_uri = URIRef(f"{s}Composition")
                    FnOBuilder.describe_composition(self.g, comp_uri, self.mappings, represents=self.scope)
                    
                    # Set starting point
                    self.g += FnOBuilder.start(comp_uri, self.start)
                    
                    # Reset to previous scope
                    self.scope = prev_scope
                    self.assigned = prev_assigned
                    self.used_by = prev_used
                    self.returns = prev_returns
                    self.var_types = prev_types
                    self.mappings = prev_mappings
                    self.iterators = prev_iterators
                    self.conditions = prev_conditions
                    self.prev_function = prev_prev_function
                    self.start = prev_start
                    
        except TypeError as e:
            print("Error: Unable to describe flow of builtin functions.")
            traceback.print_exc()
        return s
    
    def handle_block(self, block: Block):
        """
        Describes a block as a sequential composition of function executions

        Parameters:
        -----------
        block : scalpel.cfg.model.Block
            A CFG Block consisting of a sequence of statements without control structures.
        """

        prev_block = self.block
        self.block = block
        
        for predecessor in block.predecessors:
            # Check if input block is an iterator
            if predecessor.source in self.iterators:
                if predecessor.exitcase is not None:
                    self.prev_function = (self.iterators[predecessor.source], "iterate")
                else: 
                    self.prev_function = (self.iterators[predecessor.source], "next")
            # Check if input block is a conditional
            if predecessor.source in self.conditions:
                if predecessor == predecessor.source.exits[0]:
                    self.prev_function = (self.conditions[predecessor.source], "true")
                else:
                    self.prev_function = (self.conditions[predecessor.source], "false")
        
        for stmt in block.statements:
            self.handle_stmt(stmt)
        
        for i, exit in enumerate(block.exits):
            # Check if output block is an iterator
            if exit.target in self.iterators:
                # Check if this block is a conditional
                if self.block in self.conditions:
                    if i == 0:
                        self.g += FnOBuilder.link(self.conditions[self.block], "true", self.iterators[exit.target])
                    else:
                        self.g += FnOBuilder.link(self.conditions[self.block], "false", self.iterators[exit.target])
                else:
                    self.g += FnOBuilder.link(*self.prev_function, self.iterators[exit.target])
        
        # Variables used in previous blocks have ambiguos mapping
        for var in self.assigned:
            if var not in self.used_by:
                self.used_by[var] = set()

        self.block = prev_block
    
    def handle_mapping(self, mapfrom, mapto):
        if mapfrom.from_variable():
            var = mapfrom.get_variable()
            if var in self.used_by:
                self.used_by[var].add(mapto)
        
        self.mappings.append(Mapping(mapfrom, mapto))
    
    def order(self, call):
        if self.prev_function[0] is None:
            self.start = call
        else:
            self.g += FnOBuilder.link(*self.prev_function, call)
        self.prev_function = (call, "next")

    def handle_stmt(self, stmt):
        if isinstance(stmt, ast.Constant):
            return self.handle_constant(stmt.value)
        elif isinstance(stmt, ast.Name):
            return self.handle_name(stmt.id)
        elif isinstance(stmt, ast.Attribute):
            return self.handle_attr(stmt.attr, stmt.value)
        elif isinstance(stmt, ast.List):
            return self.handle_list(stmt.elts)
        elif isinstance(stmt, ast.Dict):
            return self.handle_dict(stmt.keys, stmt.values)
        elif isinstance(stmt, ast.Tuple):
            return self.handle_tuple(stmt.elts)
        elif isinstance(stmt, ast.JoinedStr):
            return self.handle_strjoin(stmt.values)
        elif isinstance(stmt, ast.FormattedValue):
            return self.handle_format(stmt.value, stmt.conversion, stmt.format_spec)
        elif isinstance(stmt, ast.Assign):
            return self.handle_assignment(stmt.value, stmt.targets)
        elif isinstance(stmt, ast.AugAssign):
            return self.handle_augassignment(stmt.target, stmt.op, stmt.value)
        elif isinstance(stmt, ast.Call):
            return self.handle_call(stmt.func, stmt.args, stmt.keywords)
        elif isinstance(stmt, ast.UnaryOp):
            return self.handle_unop(stmt.op, stmt.operand)
        elif isinstance(stmt, ast.BinOp):
            return self.handle_binop(stmt.op, stmt.left, stmt.right)
        elif isinstance(stmt, ast.BoolOp):
            return self.handle_boolop(stmt.op, stmt.values)
        elif isinstance(stmt, ast.Compare):
            return self.handle_compare(stmt.left, stmt.ops, stmt.comparators)
        elif isinstance(stmt, ast.IfExp):
            return self.handle_ifexpr(stmt.test, stmt.body, stmt.orelse)
        elif isinstance(stmt, ast.Slice):
            return self.handle_slice(stmt.lower, stmt.upper, stmt.step)
        elif isinstance(stmt, ast.Subscript):
            return self.handle_subscript(stmt.value, stmt.slice)
        elif isinstance(stmt, ast.Return):
            return self.handle_return(stmt.value)
        elif isinstance(stmt, ast.For):
            return self.handle_for(stmt.target, stmt.iter)
        elif isinstance(stmt, ast.If):
            return self.handle_if(stmt.test)
        elif isinstance(stmt, MappingNode):
            return stmt
        return MappingNode().set_constant("Unknown source")
    
    def handle_constant(self, value) -> MappingNode:
        """
        Handles an AST constant node.

        This method simply returns the constant value without any additional context or transformation.

        Parameters:
        -----------
        value : Any
            The constant value to be handled.

        Returns:
        --------
        MappingNode
            A MappingNode containing the constant
        """
        return MappingNode().set_constant(value)
    
    def handle_name(self, id):
        """
        Handles a AST name node by resolving the identifier to its meaning within the system.

        This method attempts to resolve a variable name by checking if it is assigned to a function output,
        an imported function, class, or module. It provides meaning to the string value contained within
        by looking at assigned values or imported objects.

        Parameters:
        -----------
        id : str
            The identifier of the variable to be handled.

        Returns:
        --------
        MappingNode
            A mapping node containing:
            - None or the node name (if applicable)
            - The assigned value/output

        Workflow:
        ---------
        1. Checks if the identifier is assigned to a function output.
        2. Checks if the identifier references an imported object.
        3. Adds full description if the object is callable.
        4. Returns the object or identifier without context.
        """
        # Check if the variable is assigned to a function output
        if id in self.assigned:
            return self.assigned[id]
        
        # Check if it references an imported object
        obj = self.importer.get_object(id)
        if callable(obj):
            # Add full description for extra provenance
            if obj.__name__ not in self.f_counter:
                self.describe_composition(obj)
            # Return the object without context
            return MappingNode().set_constant(obj)
        
        # Return the identifier without context if no resolution is found
        return MappingNode().set_constant(id)
    
    def handle_augassignment(self, target, op, value):
        self.handle_assignment(ast.BinOp(target, op, value), [target])
    
    def handle_assignment(self, value, targets):
        """
        Handles an AST assignment node which assigns a value to one or multiple targets.

        This method correctly handles various assignment scenarios including augmented assigns disguised as normal assigns,
        merges assignments made in different conditional bodies using if-expr, and supports indexing and unpacking.

        Parameters:
        -----------
        value : ast.AST
            The value node to be assigned to the targets.
        
        targets : list of ast.AST
            The target nodes to which the value is assigned. This can be a list of variables, subscript nodes, or tuples.

        Workflow:
        ---------
        1. Handle binary operations within the value if the target is used in the operation.
        2. Handle the value node to generate its RDF representation.
        3. For each target:
            - If it is a variable name:
                - Handle conditional assignments within if-then-else bodies if present.
                - Map the variable name to the value output and propagate the type if available.
            - If it is a subscript, handle the subscript assignment appropriately.
            - If it is a tuple, handle unpacking by assigning each element of the tuple.
        """

        # TODO Handle binary operations within the value
        for target in targets:
            if isinstance(target, ast.Name):
                # Handle assignment to variable
                target = get_name(target.id)
                value_output = self.handle_stmt(value)
                self.assigned[target] = value_output
                value_output.set_variable(target)
                
                # If this variable is used by other inputs in another block, create new mappings that use the new value
                if target in self.used_by:
                    for used_by in self.used_by[target]:
                        self.mappings.append(Mapping(value_output, used_by))    

                # Copy the type if the assigned value has a type
                val_type = self.get_type(value_output.get_value())
                if val_type:
                    self.var_types[target] = val_type

            elif isinstance(target, ast.Subscript):
                # Handle assignment to subscript nodes
                value_output = self.handle_stmt(value)
                subscript_output = self.handle_subscript(target.value, target.slice, value_output)
                self.handle_assignment(subscript_output, [target.value])

            elif isinstance(target, ast.Tuple):
                # Handle unpacking assignments
                value_output = self.handle_stmt(value)
                for i, el in enumerate(target.elts):
                    subscript_output = self.handle_subscript(value_output, ast.Constant(value=i))
                    self.handle_assignment(subscript_output, [el])
    
    def handle_return(self, value):
        self.returns.append((value, self.block, self.scope))
        
    def handle_returns(self):
        """
        Handles an AST return node, mapping the value output to the output of the outer scope.
        This method also manages conditional return statements within if expressions.

        Parameters:
        -----------
        value : ast.AST
            The value node to be returned.

        Workflow:
        ---------
        1. Retrieve the output node of the outer scope.
        2. Handle the value node to generate its RDF representation.
        3. Manage conditional return statements based on the current test context:
            - If the test is true, create an if-expr that returns the value output when the test is true.
            - Store the if-expr to allow merging if there is a return statement in the corresponding if-else body.
            - If the test is false and there was a return statement in the if-then body, update the if-expr to handle the false case.
            - If the test is false and there was no return statement in the if-then body, create an if-expr for the false case.
        4. Map the value output to the outer scope output.
        5. Propagate the type of the value output to the outer scope output if available.
        6. Describe the composition in the RDF graph using `FnODescriptor`.
        """
        for value, block, scope in self.returns:
            # Store current scope
            prev_scope = self.scope

            # Change scope
            self.scope = scope

            # Retrieve the output node of the outer scope
            output = self.g.get_output(scope)

            # Handle the value node
            mapfrom = self.handle_stmt(value)
            mapto = MappingNode().set_function_par(scope, output)
            self.handle_mapping(mapfrom, mapto)

            # Propagate the type of the value output to the outer scope output if available
            out_type = self.get_type(mapfrom.get_value())
            if out_type:
                self.var_types[output] = out_type

            # Restore previous scope
            self.scope = prev_scope
    
    def handle_call(self, func, args, kargs):
        """
        Handles an AST Call node to obtain the corresponding function object and process the call.

        This method identifies the function object being called, including methods, attributes, or built-in functions.
        It then invokes the handle_func method to process the call and generate the RDF representation.

        Parameters:
        -----------
        func : ast.AST
            The AST node representing the function being called.
        args : list
            The arguments passed to the function call.
        kargs : list
            The keyword arguments passed to the function call.

        Returns:
        --------
        Any
            The result of the handle_func method call, which processes the function call.

        Workflow:
        ---------
        1. Initialize variables to store information about the function object, such as name, context, and type.
        2. Identify the type of function call:
            - Attribute call: If the function is called as an attribute of an object.
            - Name call: If the function is a simple name.
            - Nested call: If the function call is nested within another call.
        3. Determine the function object based on the type of call:
            - For attribute calls: Get the function object from the attribute or method.
            - For name calls: Retrieve the function object from the importer or built-ins.
            - For nested calls: Obtain the function object from the type of the output of the nested call.
        4. Invoke the handle_func method with the appropriate parameters to process the function call and generate the RDF representation.
        5. Return the result of the handle_func method call.
        """

        ### FUNCTION OBJECT ###
        
        name = None
        context = None
        func_object = None
        value_name = None
        value_type = None
        static = None

        # attribute call
        if isinstance(func, ast.Attribute):
            name = str.strip(func.attr, '_')
            context = name
            value_name = self.handle_stmt(func.value)
            value_type = self.get_type(value_name.get_value())

            # The value is an imported object
            if callable(value_name.get_value()):
                func_object = getattr(value_name.get_value(), name, None)
                context = f"{getattr(value_name.get_value(), '__name__', getattr(type(value_name.get_value()), '__name__', value_name.get_value()))}_{name}"
                value_type = False

            # If the value is called on an instance, try to get the object from that type
            elif value_type is not None:
                func_object = getattr(value_type, name, None)
                context = f"{getattr(value_type, '__name__', getattr(type(value_type), '__name__', value_type))}_{name}"
                static = False
            
            # If the value is called on a module, get the object from that module
            elif self.importer.is_module(value_name.get_value()):
                func_object = self.importer.object_from_module(value_name.get_value(), name)
                context = f"{value_name.get_value()}_{name}"
                value_type = False
                
            # If the value is called on a class, get the object from that class
            elif get_name(value_name.get_value()) in self.importer.objects():
                value_type = self.importer.get_object(get_name(value_name.get_value()))
                func_object = getattr(value_type, name, None)
                context = f"{getattr(value_type, '__name__', getattr(type(value_type), '__name__', value_type))}_{name}"
                value_type = False
                static = True
            
            if value_type is None:
                value_type = True
        
        # the function is called on the output of another function
        elif isinstance(func, ast.Call):
            value_name = self.handle_stmt(func)
            value_type = self.get_type(value_name.get_value())
            name = "call"
            context = f"{value_type.__name__}_call"
            func_object = getattr(value_type, 'call', getattr(value_type, '__call__', None))
        
        if isinstance(func, ast.Name):
            name = func.id
            context = name
            func_object = self.importer.objects().get(name)
        
            if func_object is None:
                func_object = self.importer.object_from_builtins(name)
        
        return self.handle_func(name, context, func_object, args, kargs, value_name, value_type, static, func)
    
    def handle_func(self, name, context, func_object, args=[], kargs=[],
                    value_name=None, value_type=None, static=None,
                    func=None):
        """
        Handles the processing of a function call, including generating its RDF representation and composing function descriptions.

        This method manages the creation of function descriptions, handling of function composition, 
        and mapping of function arguments to RDF nodes.
        It also updates the RDF graph with the function composition and ensures that function outputs are properly mapped.

        Parameters:
        -----------
        name : str
            The name of the function.
        context : str
            The context in which the function is called.
        func_object : callable or None
            The function object corresponding to the function being called.
        args : list, optional
            The positional arguments passed to the function call. Default is an empty list.
        kargs : list, optional
            The keyword arguments passed to the function call. Default is an empty list.
        value_name : tuple or None, optional
            A tuple containing the context and output URIs on which the function is called, if applicable. Default is None.
        value_type : type or None, optional
            The type of the object on which the function is called, if applicable. Default is None.
        static : bool or None, optional
            Indicates whether the function call is static (True), dynamic (False), or not applicable (None). Default is None.
        func : ast.AST or None, optional
            The AST node representing the function call, if available. Default is None.

        Returns:
        --------
        tuple
            A tuple containing the URI of the function call and the URI for the function output.

        Workflow:
        ---------
        1. Check if a function description already exists in the RDF graph. If not, create a new one.
        2. Determine if the function call is recursive or defined by the user. If not, create its RDF representation.
        3. Determine the function composition by mapping arguments to RDF nodes and update the RDF graph accordingly.
        4. Handle function outputs and potential variable changes resulting from the function call.
        5. Return the URI of the function call and its output.
        """
        
        ### FUNCTION DESCRIPTION ###
        
        # Don't create function description twice
        if context not in self.f_counter:
            self.f_counter[context] = 1

            # Not a recursive call
            if not context == get_name(self.scope):
                # Do not describe flow of functions that were not defined by the user
                if self.importer.skip(func_object):
                    self.function_to_rdf(name, context, func_object, len(args), kargs, value_type, static)
                # Do not go deeper then necesary
                elif self.depth < self.max_depth:
                    self.depth += 1
                    self.describe_composition(name, context, func_object, len(args), kargs)
                    self.depth -= 1
                else:
                    self.function_to_rdf(name, context, func_object, len(args), kargs, value_type, static)
        else:
            self.f_counter[context] += 1
        
        ### FUNCTION COMPOSITION ###

        f = self.g.get_function(context)
        call = URIRef(f"{f}_{self.f_counter[context]}")
        self.g += FnOBuilder.apply(call, f)
            
        # Get usefull information from description
        self_par = self.g.get_self(f)
        output = self.g.get_output(f)
        f_output = MappingNode().set_function_out(call, output)
        
        # Create mappings for composition
        positional = self.g.get_positional(f)
        varpos = self.g.get_varpositional(f)
        varkey = self.g.get_varkeyword(f)
        defaults = set(positional)
        defaults.update(self.g.get_keyword(f))

        # Map value to self parameter if called upon a variable
        if self_par:
            mapto = MappingNode().set_function_par(call, self_par)
            self.handle_mapping(value_name, mapto)       
        
        # first map all positional arguments
        # If no more positional arguments, add to variable positional argument
        for i, arg in enumerate(args):
            mapfrom = self.handle_stmt(arg)
            if i < len(positional):
                par = positional[i]
                mapto = MappingNode().set_function_par(call, par)
                self.handle_mapping(mapfrom, mapto)
                defaults.remove(par)
            elif varpos is not None:
                mapto = MappingNode().set_function_par(call, varpos).set_strategy(i - len(positional))    
                self.handle_mapping(mapfrom, mapto)
        
        # Then map all keywords arguments to the parameter with the same predicate
        # If no such parameter exists add it to the variable keyword parameter
        for karg in kargs:
            mapfrom = self.handle_stmt(karg.value)
            par = self.g.get_predicate_param(f, karg.arg)
            if par is not None:
                mapto = MappingNode().set_function_par(call, par)
                self.handle_mapping(mapfrom, mapto)
                defaults.remove(par)
            elif varkey is not None:
                mapto = MappingNode().set_function_par(call, varkey).set_strategy(karg.arg)
                self.handle_mapping(mapfrom, mapto)
        
        # Map all parameters that were not mapped to its default values
        for par in defaults:
            pred = get_name(self.g.get_predicate(par))
            if context in self.default_map and pred in self.default_map[context]:
                default = self.default_map[context][pred]
                mapfrom = MappingNode().set_constant(default)
                mapto = MappingNode().set_function_par(call, par)
                self.handle_mapping(mapfrom, mapto)

        # Functions called upon a variable may potentially change the variable
        # TODO Take a better look at this!
        if value_name in self.assigned.values():
            self_output = MappingNode().set_function_out(call, self.g.get_self_output(f))
            if value_name.from_term():
                # called upon a constant
                self.handle_assignment(self_output, [self.name_node(value_name.get_value())])
                if value_type != True:
                    self.var_types[self_output.get_value()] = value_type
            else:
                # variable is the value called upon
                self.handle_assignment(self_output, [func.value])
                if value_type != True:
                    self.var_types[self_output.get_value()] = value_type

        self.order(call)
        
        return f_output
    
    def handle_attr(self, attr, value):
        """
        Handles an AST attribute node using a standard description format.

        This method processes an attribute node by creating a function description if it does not exist,
        generating an RDF representation of the attribute access, and handling the attribute and value
        nodes appropriately.

        Parameters:
        -----------
        attr : ast.AST or str
            The attribute node or a string representing the attribute to be handled.
        
        value : ast.AST
            The value node to which the attribute belongs.

        Returns:
        --------
        tuple
            A tuple containing:
            - The URIRef of the function call representing the attribute access.
            - The URI of the attribute output in the RDF graph.

        Workflow:
        ---------
        1. Create a function description for the attribute if it does not exist.
        2. Generate a unique URI for the attribute access call.
        3. Handle the value node to determine if it comes from an imported module.
        4. Convert simple string attributes to AST Name nodes if necessary.
        5. Handle the attribute and value nodes to generate their RDF representations.
        6. Describe the composition of the attribute access in the RDF graph.
        """
        # Create function description if it does not exist
        name = 'attribute'
        context = 'attribute'
        if name not in self.f_counter:
            self.f_counter[context] = 1
            _, desc = PipelineGraph.from_std(name)
            self.g += desc
        else:
            self.f_counter[context] += 1

        s = to_uri(PrefixMap.pf(), context)
        call = URIRef(f"{s}_{self.f_counter[context]}")
        self.g += FnOBuilder.apply(call, s)

        # Handle the value node
        if isinstance(value, ast.Name) and self.importer.is_module(value.id):
            # An object from an imported module is used
            mapfrom = MappingNode().set_constant(self.importer.get_module(value.id).__name__)
            mapto = MappingNode().set_function_par(call, to_uri(PrefixMap.pf(), 'ValueParameter'))
            self.handle_mapping(mapfrom, mapto)
        else:
            mapfrom = self.handle_stmt(value)
            mapto = MappingNode().set_function_par(call, to_uri(PrefixMap.pf(), 'ValueParameter'))
            self.handle_mapping(mapfrom, mapto)            

        # Convert simple string attributes to AST Name nodes if necessary
        if not isinstance(attr, ast.AST):
            attr = self.name_node(attr)

        mapfrom = self.handle_stmt(attr)
        mapto = MappingNode().set_function_par(call, to_uri(PrefixMap.pf(), 'AttributeParameter'))
        self.handle_mapping(mapfrom, mapto)

        self.order(call)
        
        return MappingNode().set_function_out(call, to_uri(PrefixMap.pf(), 'AttributeOutput'))
    
    def handle_slice(self, lower, upper, step):
        """
        Handles an AST slice node using a standard function description.

        This method processes a slice node by creating a function description for the slice,
        generating an RDF representation of the slice operation, and handling the lower, upper,
        and step components of the slice appropriately.

        Parameters:
        -----------
        lower : ast.AST or None
            The lower bound of the slice. Can be None if no lower bound is specified.
        
        upper : ast.AST or None
            The upper bound of the slice. Can be None if no upper bound is specified.
        
        step : ast.AST or None
            The step of the slice. Can be None if no step is specified.

        Returns:
        --------
        tuple
            A tuple containing:
            - The URIRef of the function call representing the slice operation.
            - The URI of the slice output in the RDF graph.

        Workflow:
        ---------
        1. Create a function description for the slice if it does not exist.
        2. Generate a unique URI for the slice operation call.
        3. Handle the lower, upper, and step nodes to generate their RDF representations.
        4. Describe the composition of the slice operation in the RDF graph.
        """
        f_name = "slice"

        if f_name not in self.f_counter:
            self.f_counter[f_name] = 1
            _, desc = PipelineGraph.from_std(f_name)
            self.g += desc
        else:
            self.f_counter[f_name] += 1

        f = to_uri(PrefixMap.pf(), f_name)
        call = URIRef(f"{f}_{self.f_counter[f_name]}")
        self.g += FnOBuilder.apply(call, f)

        # Handle the lower, upper, and step components of the slice
        lower_name = self.handle_stmt(lower) if lower else [MappingNode().set_constant(None)]
        upper_name = self.handle_stmt(upper) if upper else [MappingNode().set_constant(None)]
        step_name = self.handle_stmt(step) if step else [MappingNode().set_constant(None)]

        mapto = MappingNode().set_function_par(call, to_uri(PrefixMap.pf(), 'LowerIndexParameter'))
        self.handle_mapping(lower_name, mapto)
        
        mapto = MappingNode().set_function_par(call, to_uri(PrefixMap.pf(), 'UpperIndexParameter'))
        self.handle_mapping(upper_name, mapto)
        
        mapto = MappingNode().set_function_par(call, to_uri(PrefixMap.pf(), 'StepParameter'))
        self.handle_mapping(step_name, mapto)
        
        self.order(call)

        return MappingNode().set_function_out(call, to_uri(PrefixMap.pf(), 'SliceOutput'))
    
    def handle_subscript(self, value, index, assign=None):
        """
        Handles an AST subscript node, representing indexing using the __getitem__ and __setitem__ functions.

        This method processes a subscript node by determining whether it represents a get or set operation,
        handling the index node, and then calling the appropriate function with the correct arguments.

        Parameters:
        -----------
        value : ast.AST
            The value node that is being indexed.
        
        index : ast.AST
            The index node that specifies the position or range within the value.
        
        assign : ast.AST or None, optional
            The value to be assigned if this is a set operation. If None, the operation is assumed to be a get operation.

        Returns:
        --------
        Any
            The result of the handle_func method call, which processes the subscript operation.

        Workflow:
        ---------
        1. Handle the index node to generate its RDF representation.
        2. Determine if the operation is a get or set operation based on the presence of the assign parameter.
        3. Prepare the function name, context, and arguments for the corresponding indexing function.
        4. Call the handle_func method with the appropriate parameters to process the subscript operation.
        """

        # Determine the function and context based on whether this is a get or set operation
        f = __setitem__ if assign else __getitem__
        name = f.__name__
        context = f.__name__
        
        args = [value, index]
        if assign:
            args.append(assign)

        # Call the handle_func method with the appropriate parameters
        return self.handle_func(name, context, f, args)
    
    def handle_list(self, elts):
        """
        Handles an AST node representing a list, generating its RDF representation and managing element assignments.

        This method creates a description for a list, assigns elements to it, and updates the RDF graph accordingly.
        It also ensures that the list type is properly propagated.

        Parameters:
        -----------
        elements : list of ast.AST
            The elements to be included in the list. Each element is processed to generate its RDF representation.

        Returns:
        --------
        tuple
            A tuple containing the URI of the list call and the URI for the list output.

        Workflow:
        ---------
        1. Check if the "list" function has been encountered before and update its counter.
        2. Create a URI for the list function and apply it to the RDF graph.
        3. Handle each element in the list to generate its RDF representation and map it to the list.
        4. Describe the composition of the list in the RDF graph using `FnODescriptor`.
        5. Set the type of the list output to `list`.
        6. Return the URI of the list call and the list output.
        """
        # Check if the "list" function has been encountered before and update its counter
        if "list" not in self.f_counter:
            self.f_counter["list"] = 1
            _, desc = PipelineGraph.from_std('list')
            self.g += desc
        else:
            self.f_counter["list"] += 1

        # Create a URI for the list function and apply it to the RDF graph
        f = to_uri(PrefixMap.pf(), "list")
        call = URIRef(f"{f}_{self.f_counter['list']}")
        self.g += FnOBuilder.apply(call, f)

        # Handle each element in the list to generate its RDF representation and map it to the list
        for i, el in enumerate(elts):
            el_output = self.handle_stmt(el)
            mapto = MappingNode().set_function_par(call, to_uri(PrefixMap.pf(), 'Elements')).set_strategy(i)
            self.handle_mapping(el_output, mapto)

        # Set the type of the list output to `list`
        self.var_types[to_uri(PrefixMap.pf(), "ListOutput")] = list

        # Return the URI of the list call and the list output
        self.order(call)
        
        return MappingNode().set_function_out(call, to_uri(PrefixMap.pf(), 'ListOutput'))
    
    def handle_tuple(self, elts):
        """
        Handles an AST node representing a tuple, generating its RDF representation and managing element assignments.

        This method creates a description for a tuple, assigns elements to it, and updates the RDF graph accordingly.
        It also ensures that the tuple type is properly propagated.

        Parameters:
        -----------
        elts : list of ast.AST
            The elements to be included in the tuple. Each element is processed to generate its RDF representation.

        Returns:
        --------
        tuple
            A tuple containing the URI of the tuple call and the URI for the tuple output.

        Workflow:
        ---------
        1. Check if the "tuple" function has been encountered before and update its counter.
        2. Create a URI for the tuple function and apply it to the RDF graph.
        3. Handle each element in the tuple to generate its RDF representation and map it to the tuple.
        4. Describe the composition of the tuple in the RDF graph using `FnODescriptor`.
        5. Set the type of the tuple output to `tuple`.
        6. Return the URI of the tuple call and the tuple output.

        Assumptions:
        ------------
        This method assumes that `self.f_counter`, `self.f_generator`, `to_uri`, `PrefixMap.pf()`, `URIRef`, `FnODescriptor`,
        `self.g`, `self.handle_node`, `self._scope`, and `self.var_types` are properly defined and accessible within the class or module.
        """
        if "tuple" not in self.f_counter:
            self.f_counter["tuple"] = 1
            _, desc = PipelineGraph.from_std('tuple')
            self.g += desc
        else:
            self.f_counter["tuple"] += 1
        
        f = to_uri(PrefixMap.pf(), "tuple")
        call = URIRef(f"{f}_{self.f_counter['tuple']}")
        self.g += FnOBuilder.apply(call, f)

        for i, el in enumerate(elts):
            el_output = self.handle_stmt(el)
            mapto = MappingNode().set_function_par(call, to_uri(PrefixMap.pf(), 'Elements')).set_strategy(i)
            self.handle_mapping(el_output, mapto)

        # TupleOutput has type tuple
        self.var_types[to_uri(PrefixMap.pf(), "TupleOutput")] = tuple
        
        self.order(call)

        return MappingNode().set_function_out(call, to_uri(PrefixMap.pf(), 'TupleOutput'))
    
    def handle_dict(self, keys, values):
        """
        Handles an AST node representing a dictionary, generating its RDF representation and managing key-value assignments.

        This method creates a description for a dictionary, assigns key-value pairs to it, and updates the RDF graph accordingly.
        It also ensures that the dictionary type is properly propagated.

        Parameters:
        -----------
        keys : list of ast.AST
            The key nodes of the dictionary.
        values : list of ast.AST
            The value nodes corresponding to the keys.

        Returns:
        --------
        tuple
            A tuple containing the URI of the dictionary call and the URI for the dictionary output.

        Workflow:
        ---------
        1. Check if the "dict" function has been encountered before and update its counter.
        2. Create a URI for the dict function and apply it to the RDF graph.
        3. Handle each key-value pair in the dictionary to generate its RDF representation and map it to the dictionary.
        4. Describe the composition of the dictionary in the RDF graph using `FnODescriptor`.
        5. Set the type of the dictionary output to `dict`.
        6. Return the URI of the dict call and the dict output.

        Assumptions:
        ------------
        This method assumes that `self.f_counter`, `self.f_generator`, `to_uri`, `PrefixMap.pf()`, `URIRef`, `FnODescriptor`,
        `self.g`, `self.handle_tuple`, `self._scope`, and `self.var_types` are properly defined and accessible within the class or module.
        """
        if "dict" not in self.f_counter:
            self.f_counter["dict"] = 1
            _, desc = PipelineGraph.from_std('dict')
            self.g += desc
        else:
            self.f_counter["dict"] += 1

        f = to_uri(PrefixMap.pf(), "dict")
        call = URIRef(f"{f}_{self.f_counter['dict']}")
        self.g += FnOBuilder.apply(call, f)
        
        for i, (key, val) in enumerate(zip(keys, values)):
            pair_output = self.handle_tuple([key, val])
            mapto = MappingNode().set_function_par(call, to_uri(PrefixMap.pf(), 'Pairs')).set_strategy(i)
            self.handle_mapping(pair_output, mapto)
    
        # DictOutput has type dict
        self.var_types[to_uri(PrefixMap.pf(), "DictOutput")] = dict
        
        self.order(call)

        return MappingNode().set_function_out(call, to_uri(PrefixMap.pf(), 'DictOutput'))
    
    def handle_strjoin(self, values):
        """
        Handles an AST node representing a string join operation, generating its RDF representation and managing string parameter assignments.

        This method creates a description for a string join operation, assigns string parameters to it, and updates the RDF graph accordingly.
        It also ensures that the output type is properly propagated.

        Parameters:
        -----------
        values : list of ast.AST
            The string nodes to be joined.

        Returns:
        --------
        tuple
            A tuple containing the URI of the strjoin call and the URI for the strjoin output.

        Workflow:
        ---------
        1. Check if the "strjoin" function has been encountered before and update its counter.
        2. Create a URI for the strjoin function and apply it to the RDF graph.
        3. Handle each string parameter in the operation to generate its RDF representation and map it to the strjoin.
        4. Describe the composition of the strjoin operation in the RDF graph using `FnODescriptor`.
        5. Set the type of the strjoin output to `str`.
        6. Return the URI of the strjoin call and the strjoin output.

        Assumptions:
        ------------
        This method assumes that `self.f_counter`, `self.f_generator`, `to_uri`, `PrefixMap.pf()`, `URIRef`, `FnODescriptor`,
        `self.g`, `self.handle_node`, `self._scope`, and `self.var_types` are properly defined and accessible within the class or module.
        """
        name = "strjoin"
        if name not in self.f_counter:
            self.f_counter[name] = 1
            _, desc = PipelineGraph.from_std('strjoin')
            self.g += desc
        else:
            self.f_counter[name] += 1

        f = to_uri(PrefixMap.pf(), "strjoin")
        call = URIRef(f"{f}_{self.f_counter[name]}")
        self.g += FnOBuilder.apply(call, f)
        
        for i, value in enumerate(values):
            for mapfrom in self.handle_stmt(value):
                mapto = MappingNode().set_function_par(call, to_uri(PrefixMap.pf(), 'StringsParameter')).set_strategy(i)
                self.handle_mapping(mapfrom, mapto)

        # StrJoinOutput has type str
        self.var_types[to_uri(PrefixMap.pf(), "StrJoinOutput")] = str
        
        self.order(call)

        return MappingNode().set_function_out((call, to_uri(PrefixMap.pf(), 'StrJoinOutput')))
    
    def handle_format(self, value, conversion, spec):
        """
        Handles an AST node representing a string formatting operation.

        This method creates a description for a string formatting operation and calls the handle_func method to handle the operation.

        Parameters:
        -----------
        value : ast.AST
            The value node to be formatted.
        conversion : ast.AST
            The conversion node (not currently used in the implementation).
        spec : ast.AST
            The specification node for formatting.

        Returns:
        --------
        Any
            The result of the handle_func method call, which processes the format operation.

        Workflow:
        ---------
        1. Set the name and context for the format function.
        2. Call the handle_func method with the appropriate parameters to process the format operation.

        Assumptions:
        ------------
        This method assumes that `self.handle_func` is properly defined and accessible within the class or module.
        """
        # TODO what with conversion ?

        name = 'format'
        context = 'format'

        return self.handle_func(name, context, format, [value, spec])
    
    def handle_unop(self, op, operand):
        """
        Handles an AST Unary Operation node, processing the unary operation and generating its RDF representation.

        This method identifies the type of unary operation and adds the corresponding FnO Description if not already implemented.
        It then invokes the handle_func method to process the unary operation and generate the RDF representation.

        Parameters:
        -----------
        op : ast.AST
            The AST node representing the unary operator.
        operand : ast.AST
            The AST node representing the operand of the unary operation.

        Returns:
        --------
        tuple
            A tuple containing the URI of the unary operation and the URI for the function output.

        Workflow:
        ---------
        1. Determine the type of unary operator based on the AST node.
        2. Create a context for the unary operation based on the operator type.
        3. Invoke the handle_func method with the appropriate parameters to process the unary operation and generate the RDF representation.
        4. Return the URI of the unary operation and its output.
        """
        # Get the type of operator and add the FnO Description if it has not been implemented
        if isinstance(op, ast.UAdd):
            op_type = __pos__
        elif isinstance(op, ast.USub):
            op_type = __neg__
        elif isinstance(op, ast.Not):
            op_type = __not__
        elif isinstance(op, ast.Invert):
            op_type = __invert__

        name = op_type.__name__
        context = f"op_{name}"

        return self.handle_func(name, context, op_type, [operand])
    
    def handle_binop(self, op, left, right, assign=False):
        # Get the type of operator and add the FnO Description if it has not been implemented
        if isinstance(op, ast.Add):
            op_type = __iadd__ if assign else __add__
        elif isinstance(op, ast.Sub):
            op_type = __isub__ if assign else __sub__
        elif isinstance(op, ast.Mult):
            op_type = __imul__ if assign else __mul__
        elif isinstance(op, ast.Div):
            op_type = __itruediv__ if assign else __truediv__
        elif isinstance(op, ast.FloorDiv):
            op_type = __ifloordiv__ if assign else __floordiv__
        elif isinstance(op, ast.Mod):
            op_type = __imod__ if assign else __mod__
        elif isinstance(op, ast.Pow):
            op_type = __ipow__ if assign else __pow__
        elif isinstance(op, ast.LShift):
            op_type = __ilshift__ if assign else __lshift__
        elif isinstance(op, ast.RShift):
            op_type = __irshift__ if assign else __rshift__
        elif isinstance(op, ast.BitOr):
            op_type = __ior__ if assign else __or__
        elif isinstance(op, ast.BitXor):
            op_type = __ixor__ if assign else __xor__
        elif isinstance(op, ast.BitAnd):
            op_type = __iand__ if assign else __and__
        elif isinstance(op, ast.MatMult):
            op_type = __imatmul__ if assign else __matmul__
        
        name = op_type.__name__
        context = f"op_{name}"

        return self.handle_func(name, context, op_type, [left, right])
    
    def handle_boolop(self, op, values):
        """
        Handles an AST Binary Operation node, processing the binary operation and generating its RDF representation.

        This method identifies the type of binary operation and adds the corresponding FnO Description if not already implemented.
        It then invokes the handle_func method to process the binary operation and generate the RDF representation.

        Parameters:
        -----------
        op : ast.AST
            The AST node representing the binary operator.
        left : ast.AST
            The AST node representing the left operand of the binary operation.
        right : ast.AST
            The AST node representing the right operand of the binary operation.
        assign : bool, optional
            Indicates whether the binary operation is an assignment (True) or not (False). Default is False.

        Returns:
        --------
        tuple
            A tuple containing the URI of the binary operation and the URI for the function output.

        Workflow:
        ---------
        1. Determine the type of binary operator based on the AST node.
        2. Create a context for the binary operation based on the operator type.
        3. Invoke the handle_func method with the appropriate parameters to process the binary operation and generate the RDF representation.
        4. Return the URI of the binary operation and its output.
        """
        # Capture the values recursively for the boolop-function
        left = values[0]
        if len(values) > 2:        
            right = ast.BoolOp(op=op, values=values[1:])
        else:
            right = values[1]
        
        # Get the type of operator
        op_type = __and__ if isinstance(op, ast.And) else __or__
        name = op_type.__name__
        context = f"op_{name}"

        return self.handle_func(name, context, op_type, [left, right])
    
    def handle_compare(self, left, ops, comparators):
        """
        Handles an AST Compare node, processing the comparison operation and generating its RDF representation.

        This method identifies the type of comparison operation and adds the corresponding FnO Description if not already implemented.
        It then invokes the appropriate method to process the comparison operation and generate the RDF representation.

        Parameters:
        -----------
        left : ast.AST
            The AST node representing the left operand of the comparison.
        ops : list
            A list of AST nodes representing comparison operators.
        comparators : list
            A list of AST nodes representing comparators (right operands) for the comparison.

        Returns:
        --------
        tuple
            A tuple containing the URI of the comparison operation and the URI for the function output.

        Workflow:
        ---------
        1. If the node holds multiple comparators, treat it as an AND operation consisting of multiple compare operations.
        2. Determine the type of comparison operator and handle it accordingly:
            - For 'is' and 'is not', invoke handle_memcompare method.
            - For other comparison operators, handle them using the corresponding function.
        3. Return the URI of the comparison operation and its output.
        """
        # ops is a function that takes 2 arguments (left and comparator)
        # If the node holds multiple comparators treat it as an And consisting of multiple compares
        if len(comparators) > 1:
            nodes = []
            for op, comparator in zip(ops, comparators):
                nodes.append(ast.Compare(ops=[op], comparators=[comparator]))
            return self.handle_boolop(ast.And(), nodes)
        else:
            comparator = comparators[0]
            op = ops[0]

            if isinstance(op, ast.Is):
                return self.handle_memcompare("Is", left, comparator)
            if isinstance(op, ast.IsNot):
                return self.handle_memcompare("IsNot", left, comparator)
            
            if isinstance(op, ast.Eq):
                op_type = __eq__
            elif isinstance(op, ast.NotEq):
                op_type = __ne__
            elif isinstance(op, ast.Lt):
                op_type = __lt__
            elif isinstance(op, ast.LtE):
                op_type = __le__
            elif isinstance(op, ast.Gt):
                op_type = __gt__
            elif isinstance(op, ast.GtE):
                op_type = __ge__
            elif isinstance(op, ast.In):
                op_type = __contains__
            elif isinstance(op, ast.NotIn):
                name = __contains__.__name__
                context = f"op_{name}"
                return self.handle_unop(ast.Not(), self.handle_func(name, context, __contains__, [left, comparator]))

            name = op_type.__name__
            context = f"op_{name}"
            return self.handle_func(name, context, op_type, [left, comparator])
    
    def handle_memcompare(self, name, left, right):
        """
        Handles an AST Compare node for 'is' and 'is not' comparisons, generating their RDF representation.

        This method adds the FnO Description for the 'is' and 'is not' comparisons if not already implemented.
        It then processes the comparison operation and generates the RDF representation.

        Parameters:
        -----------
        name : str
            The name of the comparison operation ('Is' for 'is', 'IsNot' for 'is not').
        left : ast.AST
            The AST node representing the left operand of the comparison.
        right : ast.AST
            The AST node representing the right operand of the comparison.

        Returns:
        --------
        tuple
            A tuple containing the URI of the comparison operation and the URI for the function output.

        Workflow:
        ---------
        1. Add the FnO Description for the 'is' and 'is not' comparisons if not already implemented.
        2. Create a call to the corresponding function using FnO Descriptor.
        3. Process the left and right operands using the handle_node method.
        4. Map the left and right operands to the function parameters.
        5. Return the URI of the comparison operation and its output.
        """
        if name not in self.f_counter:
            self.f_counter[name] = 1
            _, desc = PipelineGraph.from_std(name)
            self.g += desc
        else:
            self.f_counter[name] += 1

        f = to_uri(PrefixMap.pf(), name)
        call = URIRef(f"{f}_{self.f_counter[name]}")
        self.g += FnOBuilder.apply(call, f)

        mapfrom in self.handle_stmt(left)
        mapto = MappingNode().set_function_par(call, to_uri(PrefixMap.pf(), 'ObjectParameter1'))
        self.handle_mapping(mapfrom, mapto)
        
        mapfrom = self.handle_stmt(right)
        mapto = MappingNode().set_function_par(call, to_uri(PrefixMap.pf(), 'ObjectParameter2'))
        self.handle_mapping(mapfrom, mapto)
        
        self.order(call)

        return MappingNode().set_function_out(call, to_uri(PrefixMap.pf(), 'BoolOutput'))
    
    def handle_ifexpr(self, test, true, false):
        """
        Handles an AST IfExp node, generating its RDF representation.

        This method processes the IfExp node, which represents a ternary conditional expression (test ? true : false),
        and generates its RDF representation using FnO descriptors.

        Parameters:
        -----------
        test : ast.AST
            The AST node representing the condition of the conditional expression.
        true : ast.AST or None
            The AST node representing the expression to be evaluated if the condition is true.
        false : ast.AST or None
            The AST node representing the expression to be evaluated if the condition is false.
        expr_name : str or None, optional
            The name of the expression. If None, a new name will be generated.

        Returns:
        --------
        tuple
            A tuple containing the URI of the IfExpr function call and the URI for the function output.

        Workflow:
        ---------
        1. Process the condition, true expression, and false expression using the handle_node method.
        2. If expr_name is None, generate a new name for the IfExpr function call and add its FnO Description.
        Otherwise, use the provided expr_name.
        3. Map the condition, true expression, and false expression to the corresponding parameters of the IfExpr function.
        4. Describe the composition using FnO Descriptor.
        5. Return the URI of the IfExpr function call and its output.
        """
      
        if "ifexpr" not in self.f_counter:
            self.f_counter["ifexpr"] = 1
            _, desc = PipelineGraph.from_std("ifexpr")
            self.g += desc
        else:
            self.f_counter["ifexpr"] += 1
            
        f = to_uri(PrefixMap.pf(), 'ifexpr')
        call = URIRef(f"{f}_{self.f_counter['ifexpr']}")
        self.g += FnOBuilder.apply(call, f)

        mapfrom = self.handle_stmt(test)
        mapto = MappingNode().set_function_par(call, to_uri(PrefixMap.pf(), 'TestParameter'))
        self.handle_mapping(mapfrom, mapto)
        
        if true is not None:
            mapfrom = self.handle_stmt(true)
            mapto = MappingNode().set_function_par(call, to_uri(PrefixMap.pf(), 'IfTrueParameter'))
            self.handle_mapping(mapfrom, mapto)

        if false is not None:
            mapfrom in self.handle_stmt(false)
            mapto = MappingNode().set_function_par(call, to_uri(PrefixMap.pf(), 'IfFalseParameter'))
            self.handle_mapping(mapfrom, mapto)
        
        self.order(call)

        return MappingNode().set_function_out(call, to_uri(PrefixMap.pf(), 'IfExprOutput'))
    
    def handle_for(self, target, iterator):    
        # Create the iterator      
        mapfrom = self.handle_stmt(iterator)
        name = iter.__name__
        context = "iter"
        iter_output = self.handle_func(name, context, iter, [mapfrom])
        
        # Create the next call
        name = next.__name__
        context = "next"
        next_output = self.handle_func(name, context, next, [iter_output])
        self.iterators[self.block] = next_output.context

        # Create a variable for the targets
        if isinstance(target, ast.Tuple):
            for i, elt in enumerate(target.elts):
                elt_output = self.handle_stmt(elt)
                self.handle_assignment(next_output.set_strategy(i), [self.name_node(elt_output.get_value())])
                next_output.set_strategy(None)
        else:
            target_output = self.handle_stmt(target)
            self.handle_assignment(next_output, [self.name_node(target_output.get_value())])
    
    def handle_if(self, test):       
        if "if" not in self.f_counter:
            self.f_counter["if"] = 1
            _, desc = PipelineGraph.from_std("if")
            self.g += desc
        else:
            self.f_counter["if"] += 1
        
        f = to_uri(PrefixMap.pf(), 'if')
        call = URIRef(f"{f}_{self.f_counter['if']}")
        self.g += FnOBuilder.apply(call, f)
        
        condition = self.handle_stmt(test)
        if_input = MappingNode().set_function_par(call, to_uri(PrefixMap.pf(), 'TestParameter')) 
        self.handle_mapping(condition, if_input)
        
        self.conditions[self.block] = call
        
        self.order(call)
    
    def function_to_rdf(self, fun_name, context, fun, num, keywords, self_class=None, static=None):
        """
        Converts a Python function definition into its RDF representation.

        This method generates an RDF representation of a Python function definition 
        using FnO descriptors based on the provided function name, context, and function object.

        Parameters:
        -----------
        f_name : str
            The name of the function.
        context : str
            The context or namespace in which the function is defined.
        f : callable
            The function object.
        num : int
            The number of parameters.
        keywords : list
            A list of keyword parameters.
        self_class : type, optional
            The class type for the self parameter, if applicable (default is None).
        static : bool, optional
            Indicates whether the method is a static method (default is None).

        Returns:
        --------
        s : str
            The unique identifier (URI) representing the function in the RDF graph.
        """

        # Get the function object if it is a method
        fun = getattr(fun, '__func__', fun)

        ### FUNCTION DESCRIPTION ###

        try:
            s, output, self_output, self_type = self.desc_with_sig(fun_name, context, fun, self_class)
        except:
            s, output, self_output, self_type = self.desc_with_amount(fun_name, context, num, keywords, self_class)
        
        ### FUNCTION IMPLEMENTATION ###

        try:
            if fun is not None:
                imp, descr = ImpMap.imp_to_rdf(fun, context, self_type, static)
            else:
                imp, descr = FnOBuilder.describe_implementation(context)
        except:
            imp, descr = FnOBuilder.describe_implementation(context, fun.__module__, getattr(fun, '__package__', None))
        self.g += descr

        ### FUNCTION MAPPING ###

        try:
            self.map_with_sig(fun, s, imp, fun_name, output, self_output)
        except:
            self.map_with_num(s, keywords, imp, fun_name, output, self_output)
        
        return s
    
    def std_to_rdf(self, f_name, context, f, self_type=None, static=False):
        """
        Converts a standard Python function definition into its RDF representation.

        This method generates an RDF representation of a standard Python function definition 
        using FnO descriptors based on the provided function name, context, and function object.

        Parameters:
        -----------
        f_name : str
            The name of the function.
        context : str
            The context or namespace in which the function is defined.
        f : callable
            The function object.
        self_type : type, optional
            The type of the self parameter for a method, if applicable (default is None).
        static : bool, optional
            Indicates whether the method is a static method (default is False).

        Returns:
        --------
        s : str
            The unique identifier (URI) representing the function in the RDF graph.
        """
        s, desc = PipelineGraph.from_std(f_name)
        self.g += desc
        output = desc.get_output(s)
        self_output = desc.get_self_output(s)

        ### FUNCTION IMPLEMENTATION ###

        try:
            if f is not None:
                imp, descr = ImpMap.imp_to_rdf(f, context, self_type, static)
            else:
                imp, descr = FnOBuilder.describe_implementation(context)
        except:
            imp, descr = FnOBuilder.describe_implementation(context, builtins.__name__, builtins.__package__)
        self.g += descr

        ### FUNCTION MAPPING ###

        try:
            self.map_with_sig(f, s, imp, f_name, output, self_output)
        except:
            self.map_with_num(s, [], imp, f_name, output, self_output)

        return s
    
    def desc_with_sig(self, f_name, context, f, self_class):
        """
        Creates a function description based on the function signature.

        This method generates a function description based on the function signature 
        using FnO descriptors.

        Parameters:
        -----------
        f_name : str
            The name of the function.
        context : str
            The context or namespace in which the function is defined.
        f : callable
            The function object.
        self_class : type
            The class type for the self parameter.

        Returns:
        --------
        s : str
            The unique identifier (URI) representing the function in the RDF graph.
        output : str
            The unique identifier (URI) representing the output of the function.
        self_output : str
            The unique identifier (URI) representing the self parameter output of the function.
        self_type : type
            The type of the self parameter.
        """
        sig = inspect.signature(f)
        params = sig.parameters
        return_type = sig.return_annotation
        
        # Check if there is a default description
        default = PipelineGraph.from_dict(context)
        if default is None:
            default = PipelineGraph.from_dict(context)
        if default:
            s, desc = default
            self.g += desc
        else:
            # Create function description from signature
            parameter_preds = []
            parameter_types = []
            self_type = None

            for i, (name, param) in enumerate(params.items()):
                if name == 'self':
                    if self_class == False:
                        continue
                    self_type, type_desc = ImpMap.imp_to_rdf(self_class)
                    self.g += type_desc
                else:
                    parameter_preds.append(name)
                    par_name = f"{context}Parameter{i}"
                    
                    param_type, type_desc = ImpMap.imp_to_rdf(param.annotation)
                    if type_desc:
                        self.g += type_desc
                    parameter_types.append(param_type)
                    self.var_types[to_uri(PrefixMap.base(), par_name)] = param.annotation
        
            output_pred = f"{context}Result"
            output = to_uri(PrefixMap.base(), f"{context}Output")

            if f is not None and type(f) is type:
                # If the function is a class constructor, the output wil have the class type
                output_type, type_desc = ImpMap.imp_to_rdf(f)
                self.var_types[output] = f
            else:
                # Convert return annotation
                output_type, type_desc = ImpMap.imp_to_rdf(return_type)
                self.var_types[output] = return_type
            
            if type_desc:
                self.g += type_desc
        
            # Add function description
            s, desc = FnOBuilder.describe_function(f_name, context,
                                                 parameter_preds, parameter_types,
                                                 output_pred, output_type,
                                                 self_type=self_type)
            self.g += desc

            self_output = to_uri(PrefixMap.base(), f"{context}SelfOutput") if self_type else None

            return s, output, self_output, self_type
    
    def desc_with_amount(self, f_name, context, num_of_params, keywords, self_class):
        """
        Creates a function description based on the number of parameters and keywords.

        This method generates a function description based on the number of parameters 
        and keywords using FnO descriptors.

        Parameters:
        -----------
        f_name : str
            The name of the function.
        context : str
            The context or namespace in which the function is defined.
        num_of_params : int
            The number of parameters.
        keywords : list
            A list of keyword parameters.
        self_class : type
            The class type for the self parameter.

        Returns:
        --------
        s : str
            The unique identifier (URI) representing the function in the RDF graph.
        output : str
            The unique identifier (URI) representing the output of the function.
        self_output : str
            The unique identifier (URI) representing the self parameter output of the function.
        self_type : type
            The type of the self parameter.
        """
        default = PipelineGraph.from_dict(context)
        if default is None:
            default = PipelineGraph.from_dict(context)
        if default:
            s, desc = default
            self.g += desc
        else:
            # Create the python any type
            any_type, type_descr = ImpMap.any()
            self.g += type_descr

            # Create function description from call
            parameter_preds = []
            parameter_types = []

            for i in range(num_of_params):
                parameter_preds.append(f"{context}ParameterPred{i}")
                parameter_types.append(any_type)
            
            for keyword in keywords:
                parameter_preds.append(keyword.arg)
                parameter_types.append(any_type)
        
            output_pred = f"{context}Result"
            output = to_uri(PrefixMap.base(), f"{context}Output")
            output_type = any_type
        
            # Add function description
            if self_class:
                self_type = any_type 
            else: 
                self_type = None

            s, desc = FnOBuilder.describe_function(f_name, context,
                                                     parameter_preds, parameter_types,
                                                     output_pred, output_type,
                                                     self_type=self_type)
            self.g += desc

            self_output = to_uri(PrefixMap.base(), f"{context}SelfOutput") if self_type else None

            return s, output, self_output, self_type
    
    def map_with_sig(self, f, s, imp, f_name, output, self_output):
        """
        Maps function parameters and outputs to RDF representations based on the function signature.

        This method maps function parameters and outputs to RDF representations 
        based on the function signature using FnO descriptors.

        Parameters:
        -----------
        f : callable
            The function object.
        s : str 
            The unique identifier (URI) representing the function in the RDF graph.
        imp : str
            The unique identifier (URI) representing the implementation of the function.
        f_name : str
            The name of the function.
        output : str
            The unique identifier (URI) representing the output of the function.
        self_output : str
            The unique identifier (URI) representing the self parameter output of the function.
        """
        sig = inspect.signature(f)
        params = sig.parameters

        # Capture the kinds
        positional = []
        keyword = []
        args = None
        kargs = None
        defaults = {}

        if s not in self.default_map:
            self.default_map[s] = {}

        for name, param in params.items():
            # Get the parameter linked to this predicate
            par = self.g.get_predicate_param(s, name)
            if param.kind == inspect.Parameter.POSITIONAL_ONLY:
                positional.append(par)
            if param.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD:
                positional.append(par)
                keyword.append((par, name))
            elif param.kind == inspect.Parameter.KEYWORD_ONLY:
                keyword.append((par, name))
            elif param.kind == inspect.Parameter.VAR_POSITIONAL:
                args = par
            elif param.kind == inspect.Parameter.VAR_KEYWORD:
                kargs = par
            
            if param.default is not inspect._empty:
                defaults[par] = param.default
                self.default_map[s].update({name: param.default})

        _, desc = FnOBuilder.describe_mapping(s, imp, f_name, positional, keyword, args, kargs, output, self_output, defaults)
        self.g += desc

    def map_with_num(self, s, keywords, imp, f_name, output, self_output):
        """
        Maps function parameters and outputs to RDF representations based on the number of parameters and keywords.

        This method maps function parameters and outputs to RDF representations 
        based on the number of parameters and keywords using FnO descriptors.

        Parameters:
        -----------
        s : str
            The unique identifier (URI) representing the function in the RDF graph.
        keywords : list
            A list of keyword parameters.
        imp : str
            The unique identifier (URI) representing the implementation of the function.
        f_name : str
            The name of the function.
        output : str
            The unique identifier (URI) representing the output of the function.
        self_output : str
            The unique identifier (URI) representing the self parameter output of the function.
        """
        positional = []
        self_param = self.g.get_self(s)
        if self_param is not None:
            positional.append(self_param) 
        positional.extend(self.g.get_parameters(s))
        keyword = []
        for pred in keywords:
            par = self.g.get_predicate_param(s, pred.arg)
            if par is not None:
                keyword.append((par, pred.arg))

        _, desc = FnOBuilder.describe_mapping(s, imp, f_name, positional, keyword, None, None, output, self_output)
        self.g += desc