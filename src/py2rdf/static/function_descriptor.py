from typing import List
from rdflib import RDF, BNode, Literal
from .mapping import Mapping, MappingNode
from ..map import PrefixMap, InstMap
from ..graph import PipelineGraph, create_rdf_list, get_name
import inspect

class FunctionDescriptor():
    """
    Provides methods to describe functions, implementations, mappings, parameters, and outputs
    in the context of the Function Ontology (FNO).
    """

    @staticmethod
    def apply(call, f) -> PipelineGraph:
        """
        Apply a call to a function.

        Args:
            call (URIRef): The call URI.
            f (URIRef): The function URI.

        Returns:
            PipelineGraph: The resulting graph.
        """
        g = PrefixMap.bind_namespaces(PipelineGraph())
        g.add((call, PrefixMap.ns('fnoc')["applies"], f))
        return g
    
    @staticmethod
    def link_composition(g: PipelineGraph, function, composition):
        g.add((function, PrefixMap.ns('fnoc')['composition'], composition))

    @staticmethod
    def describe_composition(g: PipelineGraph, block_id, mappings: List[Mapping]):
        """
        Describe a composition.

        Args:
            g (Graph): The graph to describe.
            p (URIRef): The composition URI.
            mappings (list): List of mappings.
            conditions (dict, optional): Mapping conditions. Defaults to {}.
        """

        # create the composition
        composition = block_id

        # initiate the mapping nodes
        mapping_nodes = [BNode() for i in range(len(mappings))]

        for mapping, node in zip(mappings, mapping_nodes):

            g.add((composition, PrefixMap.ns('fnoc')["composedOf"], node))
            
            if mapping.mapfrom.from_term():
                # map from term
                term = mapping.mapfrom.get_value()
                term_lit, type_desc = InstMap.inst_to_rdf(term)
                if type_desc is not None:
                    g += type_desc
                g.add((node, PrefixMap.ns('fnoc')["mapFromTerm"], term_lit))
            elif mapping.mapfrom.is_variable():
                var = mapping.mapfrom.get_value()
                g.add((node, PrefixMap.ns('fnoc')["mapFromVariable"], Literal(var)))
            else:
                # map from function
                mapfrom = BNode()

                triples = [
                    (node, PrefixMap.ns('fnoc')["mapFrom"], mapfrom),
                    (mapfrom, PrefixMap.ns('fnoc')["constituentFunction"], mapping.mapfrom.context),
                    (mapfrom, PrefixMap.ns('fnoc')["functionOutput" if mapping.mapfrom.is_output() else "functionParameter"], mapping.mapfrom.get_value())
                ]
                
                # map from strategy
                if mapping.mapfrom.has_map_strategy():
                    index = mapping.mapfrom.index
                    triples.append((mapfrom, PrefixMap.ns('fnoc')["mappingStrategy"], PrefixMap.ns('fnoc')["getItem"]))
                    if isinstance(index, int):
                        triples.append((mapfrom, PrefixMap.ns('fnoc')["index"], Literal(index)))
                    else:
                        triples.append((mapfrom, PrefixMap.ns('fnoc')["property"], Literal(index)))

                [ g.add(x) for x in triples ]
                
            if mapping.mapto.is_variable():
                # map to variable
                var = mapping.mapto.get_value()
                g.add((node, PrefixMap.ns('fnoc')["mapToVariable"], Literal(var)))
            else:
                # map to function
                mapto = BNode()

                triples = [
                    (node, PrefixMap.ns('fnoc')["mapTo"], mapto),
                    (mapto, PrefixMap.ns('fnoc')["constituentFunction"], mapping.mapto.context),
                    (mapto, PrefixMap.ns('fnoc')["functionOutput" if mapping.mapto.is_output() else "functionParameter"], mapping.mapto.get_value())
                ]

                # map to strategy
                if mapping.mapto.has_map_strategy():
                    index = mapping.mapto.index
                    triples.append((mapto, PrefixMap.ns('fnoc')["mappingStrategy"], PrefixMap.ns('fnoc')["setItem"]))
                    if isinstance(index, int):
                        triples.append((mapto, PrefixMap.ns('fnoc')["index"], Literal(index)))
                    else:
                        triples.append((mapto, PrefixMap.ns('fnoc')["property"], Literal(index)))

                [ g.add(x) for x in triples ]
    
    @staticmethod
    def link_with_condition(g: PipelineGraph, condition: MappingNode, source_id, if_true, if_false):
        conditionNode = BNode()
        triples = [
            (source_id, RDF.type, PrefixMap.ns('fnoc')["IfFlowComposition"]),
            (source_id, RDF.type, PrefixMap.ns('prov')["Entity"]),
            (source_id, PrefixMap.ns('fnoc')['condition'], conditionNode),
            (conditionNode, PrefixMap.ns('fnoc')["constituentFunction"], condition.context),
            (conditionNode, PrefixMap.ns('fnoc')["functionOutput" if condition.is_output() else "functionParameter"], condition.get_value()),
            (source_id, PrefixMap.ns('fnoc')['ifTrue'], if_true),
            (source_id, PrefixMap.ns('fnoc')['ifFalse'], if_false)
        ]
        [ g.add(x) for x in triples ]
    
    @staticmethod
    def link_with_iterator(g: PipelineGraph, iterator: MappingNode, source_id, if_next, followed_by):
        iteratorNode = BNode()
        triples = [
            (source_id, RDF.type, PrefixMap.ns('fnoc')["ForFlowComposition"]),
            (source_id, RDF.type, PrefixMap.ns('prov')["Entity"]),
            (source_id, PrefixMap.ns('fnoc')['iterator'], iteratorNode),
            (iteratorNode, PrefixMap.ns('fnoc')["constituentFunction"], iterator.context),
            (iteratorNode, PrefixMap.ns('fnoc')["functionOutput" if iterator.is_output() else "functionParameter"], iterator.get_value()),
            (source_id, PrefixMap.ns('fnoc')['ifNext'], if_next),
            (source_id, PrefixMap.ns('fnoc')['followedBy'], followed_by)
        ]
        [ g.add(x) for x in triples ]
    
    @staticmethod
    def link(g: PipelineGraph, source_id, target_id):
        triples = [
            (source_id, RDF.type, PrefixMap.ns('fnoc')["Composition"]),
            (source_id, RDF.type, PrefixMap.ns('prov')["Entity"]),
            (source_id, PrefixMap.ns('fnoc')['followedBy'], target_id)
        ]
        [ g.add(x) for x in triples ]
    
    @staticmethod
    def describe_part_function(call, applies, parameters, terms):
        """
        Describe a partially applied function.

        Args:
            call (str): The name of the call.
            applies (URIRef): The URI of the function being applied.
            parameters (list): List of parameters.
            terms (list): List of terms.

        Returns:
            Tuple: URI of the function and the resulting graph.
        """
        g = PrefixMap.bind_namespaces(PipelineGraph())

        triples = [
            (PrefixMap.ns('')[call], RDF.type, PrefixMap.ns('fnoc')["PartiallyAppliedFunction"]),
            (PrefixMap.ns('')[call], PrefixMap.ns('fnoc')["partiallyApplies"], applies)
        ]

        for parameter, term in zip(parameters, terms):
            binding = BNode()
            triples.append((PrefixMap.ns('')[call], PrefixMap.ns('fnoc')["parameterBinding"], binding))
            triples.append((binding, PrefixMap.ns('fnoc')["boundToTerm"], PrefixMap.ns('')[term]))
            triples.append((binding, PrefixMap.ns('fnoc')["boundParameter"], PrefixMap.ns('')[parameter]))
        
        [ g.add(x) for x in triples ]

        return PrefixMap.ns('')[call], g
        
    @staticmethod
    def describe_function(f_name, context,
                          inputs = [], input_types = [], 
                          output = None, output_type = None, self_type=None):
        """
        Describe a function.

        Args:
            f_name (str): The name of the function.
            context (str): The context of the function.
            inputs (list, optional): List of input parameters. Defaults to [].
            input_types (list, optional): List of input parameter types. Defaults to [].
            input_defaults (list, optional): List of default values for input parameters. Defaults to None.
            output (str, optional): Output parameter name. Defaults to None.
            output_type (str, optional): Output parameter type. Defaults to None.
            self_type (str, optional): Type of the self parameter. Defaults to None.

        Returns:
            Tuple: URI of the function and the resulting graph.
        """
        g = PrefixMap.bind_namespaces(PipelineGraph())

        g_params_outputs = PrefixMap.bind_namespaces(PipelineGraph())

        # create inputs
        for i, input in enumerate(inputs):
            type = input_types[i]
            g_params_outputs += FunctionDescriptor.describe_parameter(context, type, input, i)
        
        if self_type is not None:
            # create self parameter
            # TO DO get type of self instance
            g_params_outputs += FunctionDescriptor.describe_parameter(context, self_type)
            g_params_outputs += FunctionDescriptor.describe_output(context, self_type, "self_output", f"{context}SelfOutput")
            
        # create output
        if output and output_type:
            g_params_outputs += FunctionDescriptor.describe_output(context, output_type, output)
            
        # create fno:expects container
        c_expects = create_rdf_list(
                g,
                [x['s']
                for x in g_params_outputs.query(
                        '''SELECT ?s ?p ?o WHERE {  ?s a fno:Parameter }''',
                        initNs=PrefixMap.NAMESPACES)
                ]
        )   

        # create fno:returns list
        c_returns = create_rdf_list(
                g,
                [x['s']
                for x in g_params_outputs.query(
                        '''SELECT ?s ?p ?o WHERE {  ?s a fno:Output }''',
                        initNs=PrefixMap.NAMESPACES)
                ]
        )

        g += g_params_outputs

        s = PrefixMap.ns('')[context]

        g.add((s, RDF.type, PrefixMap.ns('fno')["Function"]))
        g.add((s, RDF.type, PrefixMap.ns('prov')["Entity"]))
        g.add((s, PrefixMap.ns('fno')['name'], Literal(f_name)))
        g.add((s, PrefixMap.ns('fno')['expects'], c_expects.uri))
        g.add((s, PrefixMap.ns('fno')['returns'], c_returns.uri))

        return s, g

    @staticmethod
    def describe_parameter(f_name, type, pred = 'self', i=-1) -> PipelineGraph:
        """
        Describe a parameter.

        Args:
            f_name (str): The name of the function.
            type (str): The parameter type.
            pred (str, optional): The predicate. Defaults to 'self'.
            default (any, optional): The default value. Defaults to None.
            i (int, optional): The index. Defaults to -1.

        Returns:
            PipelineGraph: The resulting graph.
        """
        g = PrefixMap.bind_namespaces(PipelineGraph())

        if i >= 0:
            s = PrefixMap.ns('')[f"{f_name}Parameter{i}"]
        else:
            s = PrefixMap.ns('')[f"{f_name}ParameterSelf"]

        triples = [
            (s, RDF.type, PrefixMap.ns('fno')["Parameter"]),
            (s, PrefixMap.ns('fno')["predicate"], PrefixMap.ns('')[pred]),
            (s, PrefixMap.ns('fno')["type"], type)
        ]

        [ g.add(x) for x in triples ]

        return g
    
    @staticmethod
    def describe_output(f_name, type, pred = 'selfResult', name = None) -> PipelineGraph:
        """
        Describe an output.

        Args:
            f_name (str): The name of the function.
            type (str): The output type.
            pred (str, optional): The predicate. Defaults to 'selfResult'.
            name (str, optional): The output name. Defaults to None.

        Returns:
            PipelineGraph: The resulting graph.
        """
        g = PrefixMap.bind_namespaces(PipelineGraph())

        if name is None:
            s = PrefixMap.ns('')[f"{f_name}Output"]
        else:
            s = PrefixMap.ns('')[name]

        triples = [
            (s, RDF.type, PrefixMap.ns('fno')["Output"]),
            (s, PrefixMap.ns('fno')["predicate"], PrefixMap.ns('')[pred]),
            (s, PrefixMap.ns('fno')["type"], type)
        ]
        [ g.add(x) for x in triples ]

        return g
    
    @staticmethod
    def describe_implementation(f_name, m_name=None, p_name=None) -> PipelineGraph:
        """
        Describe the implementation of a function.

        Args:
            f_name (str): The name of the function.
            m_name (str, optional): The module name. Defaults to None.
            p_name (str, optional): The package name. Defaults to None.

        Returns:
            PipelineGraph: The resulting graph.
        """
        g = PrefixMap.bind_namespaces(PipelineGraph())

        triples = [
            (PrefixMap.ns('')[f"{f_name}Implementation"], RDF.type, PrefixMap.ns('fnoi')['PythonFunction']),
            (PrefixMap.ns('')[f"{f_name}Implementation"], PrefixMap.ns('doap')['name'], Literal(f_name))
        ]

        if m_name:
            triples.append((PrefixMap.ns('')[f"{f_name}Implementation"], PrefixMap.ns('fnoi')['module-name'], Literal(m_name)))

        if p_name:
            triples.append((PrefixMap.ns('')[f"{f_name}Implementation"], PrefixMap.ns('fnoi')['package-name'], Literal(p_name)))

        [ g.add(x) for x in triples ]
        
        return PrefixMap.ns('')[f"{f_name}Implementation"], g
    
    @staticmethod
    def describe_mapping(f, imp, f_name, positional, keyword, args, kargs, output, self_output, defaults={}) -> PipelineGraph:
        """
        Describe a mapping.

        Args:
            f: The function.
            imp: The implementation.
            f_name (str): The name of the function.
            positional (list): List of positional arguments.
            keyword (list): List of keyword arguments.
            args: Variable positional argument.
            kargs: Variable keyword argument.
            output: Output parameter.
            self_output: Self output parameter.

        Returns:
            PipelineGraph: The resulting graph.
        """
        g = PrefixMap.bind_namespaces(PipelineGraph())

        methodNode = BNode()
        returnNode = BNode()
        selfNode = BNode()

        context = get_name(f)
        s = PrefixMap.ns('')[f"{context}Mapping"]

        triples = [
            (s, RDF.type, PrefixMap.ns('fno')['Mapping']),
            (s, PrefixMap.ns('fno')['function'], f),
            (s, PrefixMap.ns('fno')['implementation'], imp),
            (s, PrefixMap.ns('fno')['methodMapping'], methodNode),
            (methodNode, RDF.type, PrefixMap.ns('fnom')['StringMethodMapping']),
            (methodNode, PrefixMap.ns('fnom')['method-name'], Literal(f_name)),
            (s, PrefixMap.ns('fno')['returnMapping'], returnNode),
            (returnNode, RDF.type, PrefixMap.ns('fnom')['DefaultReturnMapping']),
            (returnNode, PrefixMap.ns('fnom')['functionOutput'], output),
        ]

        if self_output is not None:
            triples.extend([
                (s, PrefixMap.ns('fno')['returnMapping'], selfNode),
                (selfNode, RDF.type, PrefixMap.ns('fnom')['ValueReturnMapping']),
                (selfNode, PrefixMap.ns('fnom')['functionOutput'], self_output)
            ])

        ### POSITIONAL PARAMETER MAPPING ###

        for i, param in enumerate(positional):
            paramNode = BNode()

            triples.extend([
                (s, PrefixMap.ns('fno')['parameterMapping'], paramNode),
                (paramNode, RDF.type, PrefixMap.ns('fnom')['PositionParameterMapping']),
                (paramNode, PrefixMap.ns('fnom')['functionParameter'], param),
                (paramNode, PrefixMap.ns('fnom')['implementationParameterPosition'], Literal(i))
            ])

            if param in defaults:
                triples.append((param, PrefixMap.ns('fno')["required"], Literal(False)))
            else:
                triples.append((param, PrefixMap.ns('fno')["required"], Literal(True)))

        ### PROPERTY PARAMETER MAPPING ###
        
        for (param, key) in keyword:
            paramNode = BNode()

            triples.extend([
                (s, PrefixMap.ns('fno')['parameterMapping'], paramNode),
                (paramNode, RDF.type, PrefixMap.ns('fnom')['PropertyParameterMapping']),
                (paramNode, PrefixMap.ns('fnom')['functionParameter'], param),
                (paramNode, PrefixMap.ns('fnom')['implementationProperty'], Literal(key))

            ])

            if param in defaults:
                triples.append((param, PrefixMap.ns('fno')["required"], Literal(False)))
            else:
                triples.append((param, PrefixMap.ns('fno')["required"], Literal(True)))
        
        ### DEFAULT PARAMETER MAPPING ###

        for (param, default) in defaults.items():
            defaultNode = BNode()
            default_lit, type_desc = InstMap.inst_to_rdf(default)
            if type_desc is not None:
                g += type_desc
                
            triples.extend([
                (s, PrefixMap.ns('fno')['parameterMapping'], defaultNode),
                (defaultNode, RDF.type, PrefixMap.ns('fnom')['DefaultParameterMapping']),
                (defaultNode, PrefixMap.ns('fnom')['functionParameter'], param),
                (defaultNode, PrefixMap.ns('fnom')['defaultValue'], default_lit),
            ])

        ### VAR POSITIONAL PARAMETER MAPPING ###
        
        if args is not None:
            argNode = BNode()
            triples.extend([
                (s, PrefixMap.ns('fno')['parameterMapping'], argNode),
                (argNode, RDF.type, PrefixMap.ns('fnom')['VarPositionalParameterMapping']),
                (argNode, PrefixMap.ns('fnom')['functionParameter'], args)
            ])
        
        ### VAR KEYWORD PARAMETER MAPPING ###

        if kargs is not None:
            kargNode = BNode()
            triples.extend([
                (s, PrefixMap.ns('fno')['parameterMapping'], kargNode),
                (kargNode, RDF.type, PrefixMap.ns('fnom')['VarPropertyParameterMapping']),
                (kargNode, PrefixMap.ns('fnom')['functionParameter'], kargs)
            ])

        [ g.add(x) for x in triples ]

        return s, g