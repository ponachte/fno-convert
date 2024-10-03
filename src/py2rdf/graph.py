from rdflib import Graph, BNode, Literal, URIRef
from rdflib.container import Container
from .map import PrefixMap, FnODescriptionMap, ImpMap
from pyparsing.exceptions import ParseException
from typing import Any

def create_rdf_list(g, elements):
    """
    Helper function to create an RDF List with the given elements.
    
    This function creates a Container of type 'Seq' (sequence) in the given RDF graph.
    
    :param g: rdflib.Graph
        The RDF Graph on which the RDF list will be attached.
    :param elements: list
        A list of elements to be included in the RDF list.
    :return: rdflib.collection.Container
        A Container object representing the RDF list.
    """
    return Container(g, BNode(), seq=elements, rtype='Seq')

def get_prefix(s):
    """
    Extracts the prefix from a given URI string.
    
    The prefix is considered to be everything before the last '#' character.
    
    :param s: str
        The URI string from which to extract the prefix.
    :return: str
        The prefix of the URI.
    """
    return '#'.join(s.split('#')[:-1])

def get_name(s):
    """
    Extracts the name from a given URI string.
    
    The name is considered to be everything after the last '#' character. If no '#' is present, 
    the entire string is returned.
    
    :param s: str
        The URI string from which to extract the name.
    :return: str
        The name extracted from the URI.
    """
    if '#' in s:
        return s.split('#')[-1]
    return s

def to_uri(prefix, s):
    """
    Converts a prefix and a name into a full URI.
    
    This function takes a prefix and a name, combines them with a '#' separator, and returns a URIRef object.
    
    :param prefix: str
        The prefix part of the URI. Typically this is the base URI or namespace.
    :param s: str
        The name or identifier to be appended to the prefix.
    :return: rdflib.term.URIRef
        A URIRef object representing the full URI.
    """
    return URIRef(f"{prefix}#{s}")


class PipelineGraph(Graph):
     """
     A subclass of rdflib.Graph tailored for handling pipeline graphs
     with specific functionalities for managing function descriptions.
     """
     @staticmethod
     def from_std(name):
        """
        Creates a PipelineGraph from a standard description.
        
        :param name: str
            The name of the standard to look up.
        :return: tuple or None
            A tuple containing the standard identifier and its function description, or None if not found.
        """
        info = FnODescriptionMap.get_std(name)
        if info:
            s, desc = info
            return s, PipelineGraph(desc).get_function_description(s)
        return

     @staticmethod
     def from_dict(name):
        """
        Creates a PipelineGraph from a dictionary description.
        
        :param name: str
            The name of the description to look up.
        :return: tuple or None
            A tuple containing the description identifier and its function description, or None if not found.
        """
        info = FnODescriptionMap.get_description(name)
        if info:
            s, desc = info
            return s, PipelineGraph(desc).get_function_description(s)
        return

     def __init__(self, graph=None):
        """
        Initializes a PipelineGraph.
        
        :param graph: rdflib.Graph or None
            An optional RDF graph to initialize the PipelineGraph with.
        """
        super().__init__()
        if graph:
            self += graph

     def check_call(self, f):
        """
        Checks if a function call is applied in the graph and returns the function it applies.
        
        :param f: URIRef
            The function URI to check.
        :return: URIRef
            The applied function URI or the original URI if no specific function is found.
        """
        result = [x['f'] for x in self.query(
            f'''SELECT ?f WHERE {{ <{f}> fnoc:applies ?f . }}''', 
            initNs=PrefixMap.NAMESPACES
        )]
        if len(result) == 1:
            return result[0]
        return f

     def get_name(self, f):
        """
        Retrieves the context-free name of a function.
        
        :param f: URIRef
            The function URI to retrieve the name for.
        :return: str or None
            The function's context-free name or None if not found.
        """
        f = self.check_call(f)
        result = [x['name'].value for x in self.query(
            f'''
            SELECT ?name WHERE {{
                ?mapping fno:function <{f}> ;
                         fno:methodMapping ?methodmap .
                ?methodmap fnom:method-name ?name .
            }}''', 
            initNs=PrefixMap.NAMESPACES
        )]
        return result[0] if len(result) > 0 else None

     def is_parameter(self, s) -> bool:
        """
        Checks if a URI is a parameter.
        
        :param s: URIRef
            The URI to check.
        :return: bool
            True if the URI is a parameter, False otherwise.
        """
        s = self.check_call(s)
        results = self.query(
            f'''ASK WHERE {{ <{s}> a fno:Parameter . }}''', 
            initNs=PrefixMap.NAMESPACES
        )
        return True if results else False

     def is_output(self, s) -> bool:
        """
        Checks if a URI is an output.
        
        :param s: URIRef
            The URI to check.
        :return: bool
            True if the URI is an output, False otherwise.
        """
        s = self.check_call(s)
        results = self.query(
            f'''ASK WHERE {{ <{s}> a fno:Output . }}''', 
            initNs=PrefixMap.NAMESPACES
        )
        return True if results else False

     def in_composition(self, comp, call, full=True) -> bool:
        """
        Checks if a function call is within a composition.

        :param comp: URIRef
            The URI of the composition.
        :param call: URIRef
            The function call URI to check.
        :param full: bool
            If True, checks both mappings (mapFrom and mapTo). 
            If False, only mapFrom is checked.
        :return: bool
            True if the function call is within the composition, False otherwise.
        """
        # Query to check the 'mapTo' part
        mapto_query = self.query(f'''
            ASK WHERE {{
                <{comp}> fnoc:composedOf ?mapping .
                ?mapping fnoc:mapTo ?mapto .
                ?mapto fnoc:constituentFunction <{call}> .
            }}''', initNs=PrefixMap.NAMESPACES)

        # If 'full' is True, also check the 'mapFrom' part
        mapfrom_query = True  # Default to True if full is False
        if full:
            mapfrom_query = self.query(f'''
                ASK WHERE {{
                    <{comp}> fnoc:composedOf ?mapping .
                    ?mapping fnoc:mapFrom ?mapfrom .
                    ?mapfrom fnoc:constituentFunction <{call}> .
                }}''', initNs=PrefixMap.NAMESPACES)

        # Both queries need to return True if 'full' is True; otherwise, only 'mapTo' matters
        return (True if mapto_query else False) and (True if mapfrom_query else False)

     def has_pipeline(self, s) -> bool:
        """
        Checks if a function has an associated pipeline.
        
        :param s: URIRef
            The function URI to check.
        :return: bool
            True if the function has an associated pipeline, False otherwise.
        """
        p = to_uri(PrefixMap.base(), f"{self.get_name(s)}Pipeline")
        results = self.query(
            f'''ASK WHERE {{ <{p}> a fnoc:Composition . }}''', 
            initNs=PrefixMap.NAMESPACES
        )
        return True if results else False

     def get_function(self, name):
        """
        Retrieves the function URI for a given name.

        :param name: str
            The name of the function to retrieve.
        :return: URIRef or None
            The function URI or None if not found.
        """
        try:
            result = [
                x['f'] for x in self.query(f'''
                SELECT ?f WHERE {{
                    ?f a fno:Function
                }}''', initNs=PrefixMap.NAMESPACES)
            ]

            for f in result:
                if get_name(f) == name:
                    return f
            raise Exception("Could not find function")
        except Exception as e:
            print(f"Error while querying function from name {name}: <{e}>")
            return

     def get_pipeline(self, call):
        """
        Retrieves the pipeline URI associated with a function call.

        :param call: URIRef
            The function call URI to check.
        :return: URIRef or None
            The pipeline URI or None if not found.
        """
        result = [
            x['p'] for x in self.query(f'''
                SELECT ?p WHERE {{
                    <{call}> fno:composition ?p .
                }}''', initNs=PrefixMap.NAMESPACES)
        ]
        if len(result) > 0:
          return result[0]
        
        result = [
            x['p'] for x in self.query(f'''
                SELECT ?p WHERE {{
                    <{self.check_call(call)}> fno:composition ?p .
                }}''', initNs=PrefixMap.NAMESPACES)
        ]

        return result[0] if len(result) > 0 else None

     def get_parameters(self, f) -> list[str]:
        """
        Retrieves the list of parameters for a function, excluding 'self' parameters.

        :param f: URIRef
            The function URI to retrieve parameters for.
        :return: list[str]
            A sorted list of parameter URIs.
        """
        return sorted([
            x['param']
            for x in self.query(f'''
                SELECT ?param WHERE {{
                    <{f}> a fno:Function ;
                           fno:expects ?list .
                    ?list ?index ?param .
                    ?param fno:predicate ?pred .
                    FILTER(?pred != <{to_uri(get_prefix(f), 'self')}>)
                }}
            ''', initNs=PrefixMap.NAMESPACES)
        ])

     def get_parameter_at(self, f, i) -> list[str]:
        """
        Retrieves the parameter at a given position for a function.

        :param f: URIRef
            The function URI to retrieve the parameter for.
        :param i: int
            The position index of the parameter.
        :return: list[str]
            The parameter URI at the given position, or None if not found.
        """
        result = [
            x['param'] for x in self.query(f'''
                SELECT ?param WHERE {{
                    ?mapping a fnom:Mapping ;
                             fno:function <{f}> ;
                             fno:parameterMapping ?parmapping .
                    ?parmapping a fnom:PositionParameterMapping ;
                                fnom:functionParameter ?param ;
                                fnom:implementationParameterPosition {Literal(i).n3()} .
                }}
            ''', initNs=PrefixMap.NAMESPACES)
        ]
        return result[0] if len(result) == 1 else None

     def get_parameter_index(self, f, param) -> list[str]:
        """
        Retrieves the position index of a given parameter for a function.

        :param f: URIRef
            The function URI to retrieve the parameter index for.
        :param param: str
            The parameter name.
        :return: list[str]
            The position index of the parameter, or None if not found.
        """
        prefix = get_prefix(f)
        result = [
            x['index'].value for x in self.query(f'''
                SELECT ?index WHERE {{
                    ?mapping a fnom:Mapping ;
                             fno:function <{f}> ;
                             fno:parameterMapping ?parmapping .
                    ?parmapping a fnom:PositionParameterMapping ;
                                fnom:functionParameter <{to_uri(prefix, param)}> ;
                                fnom:implementationParameterPosition ?index .
                }}
            ''', initNs=PrefixMap.NAMESPACES)
        ]
        return result[0] if len(result) == 1 else None

     def get_param_predicates(self, f) -> list[str]:
        """
        Retrieves the predicates for all parameters of a function.

        :param f: URIRef
            The function URI to retrieve parameter predicates for.
        :return: list[str]
            A list of tuples containing parameter URIs and their predicates.
        """
        return [
            (x['param'], x['pred'])
            for x in self.query(f'''
                SELECT ?param ?pred WHERE {{
                    <{f}> a fno:Function ;
                           fno:expects ?list .
                    ?list ?index ?param .
                    ?param fno:predicate ?pred .
                    FILTER(?pred != <{to_uri(get_prefix(f), 'self')}>)
                }}
            ''', initNs=PrefixMap.NAMESPACES)
        ]

     def get_param_predicate(self, param) -> str:
        """
        Retrieves the predicate of a given parameter.

        :param param: URIRef
            The parameter URI to retrieve the predicate for.
        :return: str
            The predicate of the parameter.
        """
        return [
            x['pred']
            for x in self.query(f'''
                SELECT ?pred WHERE {{
                    <{param}> a fno:Parameter ;
                              fno:predicate ?pred .
                }}
            ''', initNs=PrefixMap.NAMESPACES)
        ][0]

     def get_predicate_param(self, f, pred) -> str:
        """
        Retrieves the parameter corresponding to a given predicate for a function.

        :param f: URIRef
            The function URI to retrieve the parameter for.
        :param pred: str
            The predicate name.
        :return: str
            The parameter URI corresponding to the predicate, or None if not found.
        """
        f = self.check_call(f)
        prefix = get_prefix(f)
        result = [
            x['param']
            for x in self.query(f'''
                SELECT ?param WHERE {{
                    <{f}> a fno:Function ;
                          fno:expects ?list .
                    ?list ?index ?param .
                    ?param a fno:Parameter ;
                           fno:predicate <{to_uri(prefix, pred)}> .
                }}
            ''', initNs=PrefixMap.NAMESPACES)
        ]
        return result[0] if len(result) > 0 else None

     def get_param_type(self, param) -> str:
        """
        Retrieves the type of a given parameter.

        :param param: URIRef
            The parameter URI to retrieve the type for.
        :return: str
            The type of the parameter, or a default type if not found.
        """
        result = [
            ImpMap.rdf_to_imp(self, x['type'])
            for x in self.query(f'''
                SELECT ?type WHERE {{
                    <{param}> a fno:Parameter ;
                              fno:type ?type .
                }}
            ''', initNs=PrefixMap.NAMESPACES)
        ]
        return result[0] if len(result) > 0 else Any

     def get_self(self, f) -> str:
        """
        Retrieves the 'self' parameter of a function.

        :param f: URIRef
            The function URI to retrieve the 'self' parameter for.
        :return: str
            The 'self' parameter URI, or None if not found.
        """
        f = self.check_call(f)

        result = [
            x['param']
            for x in self.query(f'''
                SELECT ?param WHERE {{
                    <{f}> a fno:Function ;
                           fno:expects ?list .
                    ?list ?index ?param .
                    ?param fno:predicate ?pred .
                    FILTER(?pred = <{to_uri(get_prefix(f), 'self')}>)
                }}
            ''', initNs=PrefixMap.NAMESPACES)
        ]

        return result[0] if len(result) > 0 else None
     
     def has_self(self, f: URIRef) -> bool:
        """
        Check if a FnO Function has a `self` parameter.

        :param f: rdflib.URIRef
            The URI of the function you want to check.
        
        :return: bool
            `True` if the function has a `self` parameter, `False` otherwise
        """
        results = self.query(
            f'''ASK WHERE {{ 
                <{f}> fno:expects ?list . 
                ?list ?index ?param .
                ?param fno:predicate ?pred .
                FILTER(?pred = <{to_uri(get_prefix(f), 'self')}>)
            }}''', 
            initNs=PrefixMap.NAMESPACES
        )
        return True if results else False

     def get_output(self, f) -> str:
        """
        Retrieves the output of a function.

        :param f: URIRef
            The function URI to retrieve the output for.
        :return: str
            The output URI, or None if not found.
        """
        f = self.check_call(f)
        result = [
            x['output']
            for x in self.query(f'''
                SELECT ?output ?pred WHERE {{
                    <{f}> a fno:Function ;
                           fno:returns ?list .
                    ?list ?index ?output .
                    ?output a fno:Output ;
                            fno:predicate ?pred .
                    FILTER(?pred != <{to_uri(get_prefix(f), 'self_output')}>)
                }}
            ''', initNs=PrefixMap.NAMESPACES)
        ]

        return result[0] if len(result) > 0 else None
     
     def has_output(self, f: URIRef) -> bool:
        """
        Check if a FnO Function has an output which is not a `self` output.

        :param f: rdflib.URIRef
            The URI of the function you want to check.
        
        :return: bool
            `True` if the function has an output which is not a `self` output., `False` otherwise.
        """
        results = self.query(
            f'''ASK WHERE {{ 
                <{f}> fno:returns ?list . 
                ?list ?index ?output .
                ?output fno:predicate ?pred .
                FILTER(?pred != <{to_uri(get_prefix(f), 'self_output')}>)
            }}''', 
            initNs=PrefixMap.NAMESPACES
        )
        return True if results else False

     def get_self_output(self, f) -> str:
        """
        Retrieves the 'self_output' of a function.

        :param f: URIRef
            The function URI to retrieve the 'self_output' for.
        :return: str
            The 'self_output' URI, or None if not found.
        """
        f = self.check_call(f)
        result = [
            x['output']
            for x in self.query(f'''
                SELECT ?output ?pred WHERE {{
                    <{f}> a fno:Function ;
                           fno:returns ?list .
                    ?list ?index ?output .
                    ?output a fno:Output ;
                            fno:predicate ?pred .
                    FILTER(?pred = <{to_uri(get_prefix(f), 'self_output')}>)
                }}
            ''', initNs=PrefixMap.NAMESPACES)
        ]

        return result[0] if len(result) > 0 else None
     
     def has_self_output(self, f: URIRef) -> bool:
        """
        Check if a FnO Function has a `self` output.

        :param f: rdflib.URIRef
            The URI of the function you want to check.
        
        :return: bool
            `True` if the function has a `self` output., `False` otherwise.
        """
        results = self.query(
            f'''ASK WHERE {{ 
                <{f}> fno:returns ?list . 
                ?list ?index ?output .
                ?output fno:predicate ?pred .
                FILTER(?pred = <{to_uri(get_prefix(f), 'self_output')}>)
            }}''', 
            initNs=PrefixMap.NAMESPACES
        )
        return True if results else False

     def get_predicate(self, s):
        """
        Retrieves the predicate of a given parameter or output.

        :param s: URIRef
            The parameter or output URI to retrieve the predicate for.
        :return: str
            The predicate of the parameter or output.
        """
        return [
            x['pred']
            for x in self.query(f'''
                SELECT ?pred WHERE {{
                    VALUES ?type {{ fno:Parameter fno:Output }}
                    <{s}> a ?type ;
                          fno:predicate ?pred .
                }}
            ''', initNs=PrefixMap.NAMESPACES)
        ][0]

     def get_output_predicate(self, f) -> str:
        """
        Retrieves the predicate for the output of a function.

        :param f: URIRef
            The function URI to retrieve the output predicate for.
        :return: str
            A tuple containing the output URI and its predicate.
        """
        return [
            (x['output'], x['pred'])
            for x in self.query(f'''
                SELECT ?output ?pred WHERE {{
                    <{f}> a fno:Function ;
                           fno:returns ?list .
                    ?list ?index ?output .
                    ?output fno:predicate ?pred .
                FILTER(?pred != <{to_uri(get_prefix(f), 'self_output')}>)
                }}
            ''', initNs=PrefixMap.NAMESPACES)
        ][0]

     def get_output_type(self, out) -> str:
        """
        Retrieves the type of a given output.

        :param out: URIRef
            The output URI to retrieve the type for.
        :return: str
            The type of the output, or a default type if not found.
        """
        result = [
            ImpMap.rdf_to_imp(self, x['type'])
            for x in self.query(f'''
                SELECT ?type WHERE {{
                    <{out}> a fno:Output ;
                            fno:type ?type .
                }}
            ''', initNs=PrefixMap.NAMESPACES)
        ]
        return result[0] if len(result) > 0 else Any
     
     def has_flow(self, f):
         result = self.query(f'''
                ASK WHERE {{
                    <{f}> a fno:Function ;
                          fnoc:composition ?start .
                }}
             ''', initNs=PrefixMap.NAMESPACES)

         return True if result else False
     
     def start_of_flow(self, f):
         """
         Retrieve the URI of the first block of the flow describing a FnO Function.

         :param f: rdflib.URIRef
            The URI of the FnO Function you want the flow start from.
        :return: rdflib.URIRef
            The Uri of the first composition in the flow.
         """
         result = [
             x['start']
             for x in self.query(f'''
                SELECT ?start WHERE {{
                    <{f}> a fno:Function ;
                          fnoc:composition ?start .
                }}
             ''', initNs=PrefixMap.NAMESPACES)
         ]

         if len(result) > 1:
             raise Exception(f"{f} has more then one defined starting points.")
         elif len(result) == 0:
             raise Exception(f"{f} has no flow defined.")
         return result[0]
     
     def is_composition(self, c: URIRef) -> bool:
         result = self.query(f'''
            ASK WHERE {{ <{c}> a fnoc:Composition . }}
         ''', initNs=PrefixMap.NAMESPACES)
         return True if result else False
     
     def is_if_composition(self, c: URIRef) -> bool:
         result = self.query(f'''
            ASK WHERE {{ <{c}> a fnoc:IfFlowComposition . }}
         ''', initNs=PrefixMap.NAMESPACES)
         return True if result else False
     
     def is_for_composition(self, c: URIRef) -> bool:
         result = self.query(f'''
            ASK WHERE {{ <{c}> a fnoc:ForFlowComposition . }}
         ''', initNs=PrefixMap.NAMESPACES)
         return True if result else False
     
     def followed_by(self, c: URIRef) -> URIRef:
         result = [x['next'] for x in self.query(f'''
            SELECT ?next WHERE {{
                <{c}> fnoc:followedBy ?next .
            }}''', initNs=PrefixMap.NAMESPACES)]
         return result[0] if len(result) == 1 else None
     
     def if_true(self, c: URIRef) -> URIRef:
         result = [x['next'] for x in self.query(f'''
            SELECT ?next WHERE {{
                <{c}> fnoc:ifTrue ?next .
            }}''', initNs=PrefixMap.NAMESPACES)]
         return result[0] if len(result) == 1 else None
     
     def if_false(self, c: URIRef) -> URIRef:
         result = [x['next'] for x in self.query(f'''
            SELECT ?next WHERE {{
                <{c}> fnoc:ifFalse ?next .
            }}''', initNs=PrefixMap.NAMESPACES)]
         return result[0] if len(result) == 1 else None
     
     def get_condition(self, c: URIRef):
         result = [(x['f'], x['par']) for x in self.query(f'''
            SELECT ?f ?par WHERE {{
                <{c}> fnoc:condition ?cond .
                ?cond fnoc:constituentFunction ?f ;
                      fnoc:functionOutput | fnoc:functionParameter ?par .
            }}''', initNs=PrefixMap.NAMESPACES)]
         return result[0] if len(result) == 1 else None
     
     def if_next(self, c: URIRef) -> URIRef:
         result = [x['next'] for x in self.query(f'''
            SELECT ?next WHERE {{
                <{c}> fnoc:ifNext ?next .
            }}''', initNs=PrefixMap.NAMESPACES)]
         return result[0] if len(result) == 1 else None
     
     def get_iterator(self, c: URIRef):
         result = [(x['f'], x['par']) for x in self.query(f'''
            SELECT ?f ?par WHERE {{
                <{c}> fnoc:iterator ?iter .
                ?iter fnoc:constituentFunction ?f ;
                      fnoc:functionOutput | fnoc:functionParameter ?par .
            }}''', initNs=PrefixMap.NAMESPACES)]
         return result[0] if len(result) == 1 else None
     
     def get_mappings(self, c):
          """
          Get all mappings inside a composition block.

          :param c: rdflib.URIRef
            The URI of the composition block.
        
          :return: 
            Set of tuples containing the mappings:
                    - The URI of the first function
                    - The URI of the parameter of the first function
                    - The URI of the second function
                    - The URI of the parameter of the second function
          """
          results = self.query(f'''
               SELECT ?f1 ?par1 ?f2 ?par2 WHERE {{
                    <{c}> fnoc:composedOf ?mapping .
                    ?mapping fnoc:mapFrom ?mapfrom ;
                             fnoc:mapTo ?mapto .
                    ?mapfrom fnoc:constituentFunction ?f1 ;
                             fnoc:functionParameter | fnoc:functionOutput ?par1 .
                    ?mapto fnoc:constituentFunction ?f2 ;
                           fnoc:functionParameter | fnoc:functionOutput ?par2 .
               }}
          ''', initNs=PrefixMap.NAMESPACES)

          # Return the distinct set of mappings
          return set([ (m['f1'], m['par1'], m['f2'], m['par2']) for m in results ])
     
     def get_term_mappings(self, c):
          """
          Get all term mappings inside a composition block.

          :param c: rdflib.URIRef
            The URI of the composition block.
        
          :return: 
            List of tuples containing the term mappings:
                    - The URI of the constant
                    - The datatype URI of the constant
                    - The URI of the function
                    - The parameter of the function
          """
          results = self.query(f'''
               SELECT ?con ?f ?par WHERE {{
                    <{c}> fnoc:composedOf ?mapping .
                    ?mapping fnoc:mapFromTerm ?con ;
                         fnoc:mapTo ?mapto .
                    ?mapto fnoc:constituentFunction ?f ;
                         fnoc:functionParameter | fnoc:functionOutput ?par .
               }}
          ''', initNs=PrefixMap.NAMESPACES)

          return [ (m['con'].value,
                    ImpMap.rdf_to_imp(self, m['con'].datatype),
                    m['f'], m['par']) 
                    for m in results ]
     
     def get_fromvar_mappings(self, c):
          """
          Get all from var mappings inside a composition block.

          :param c: rdflib.URIRef
            The URI of the composition block.
        
          :return: 
            List of tuples containing the from var mappings:
                    - The variable name
                    - The URI of the function
                    - The parameter of the function
          """
          results = self.query(f'''
               SELECT ?var ?f ?par WHERE {{
                    <{c}> fnoc:composedOf ?mapping .
                    ?mapping fnoc:mapFromVar ?var ;
                         fnoc:mapTo ?mapto .
                    ?mapto fnoc:constituentFunction ?f ;
                         fnoc:functionParameter | fnoc:functionOutput ?par .
               }}
          ''', initNs=PrefixMap.NAMESPACES)

          return [ (m['var'].value, m['f'], m['par']) for m in results ]
     
     def get_tovar_mappings(self, c):
          """
          Get all to var mappings inside a composition block.

          :param c: rdflib.URIRef
            The URI of the composition block.
        
          :return: 
            List of tuples containing the to var mappings:
                    - The URI of the function
                    - The parameter of the function
                    - The variable name
          """
          results = self.query(f'''
               SELECT ?var ?f ?par WHERE {{
                    <{c}> fnoc:composedOf ?mapping .
                    ?mapping fnoc:mapFrom ?mapfrom ;
                         fnoc:mapToVar ?var .
                    ?mapfrom fnoc:constituentFunction ?f ;
                         fnoc:functionParameter | fnoc:functionOutput ?par .
               }}
          ''', initNs=PrefixMap.NAMESPACES)

          return [ (m['f'], m['par'], m['var'].value) for m in results ]
     
     def get_strategy(self, f, f1, par1, f2, par2):
          """
          Retrieve the mapping strategy employed between two functions within the pipeline.

          Args:
               f (str): The function URI of the pipeline.
               f1 (str): The URI of the first constituent function.
               par1 (str): The parameter of the first constituent function.
               f2 (str): The URI of the second constituent function.
               par2 (str): The parameter of the second constituent function.

          Returns:
               list: A list of tuples representing the mapping strategy, each tuple containing:
                    - The index or property of the source function (fromindex)
                    - The index or property of the target function (toindex)
          """
          p = self.get_pipeline(f)
          return [
               (x['fromindex'].value if x['fromindex'] is not None else None, 
                x['toindex'].value if x['toindex'] is not None else None) 
                for x in self.query(f'''
                    SELECT ?fromindex ?toindex WHERE {{
                         <{p}> a fnoc:Composition ;
                                                  fnoc:composedOf ?mapping .
                         ?mapping fnoc:mapFrom ?mapfrom ;
                                  fnoc:mapTo ?mapto .
                         ?mapfrom fnoc:constituentFunction <{f1}> ;
                                  fnoc:functionParameter | fnoc:functionOutput <{par1}> .
                         ?mapto fnoc:constituentFunction <{f2}> ;
                                fnoc:functionParameter | fnoc:functionOutput <{par2}> .
                         OPTIONAL {{ ?mapfrom fnoc:index | fnoc:property ?fromindex . }}
                         OPTIONAL {{ ?mapto fnoc:index | fnoc:property ?toindex . }}
               }}
          ''', initNs=PrefixMap.NAMESPACES)
          ]
     
     def get_term_strategy(self, c, const, datatype, f, par):
          """
          Retrieve the strategy for mapping a term to a function within the pipeline.

          Args:
               c (str): The function call URI representing the pipeline.
               const (str): The constant value of the term.
               datatype (str): The datatype URI of the constant value.
               f (str): The URI of the function.
               par (str): The parameter of the function.

          Returns:
               list: A list of strategy values for mapping the term, representing the index or property.
          """
          p = self.get_pipeline(c)
          return [
               x['index'].value for x in self.query(f'''
               SELECT ?strategy ?index WHERE {{
                    <{p}> a fnoc:Composition ;
                                       fnoc:composedOf ?mapping .
                    ?mapping fnoc:mapFromTerm {Literal(const, datatype=datatype).n3()} ;
                             fnoc:mapTo ?mapto .
                    ?mapto fnoc:constituentFunction <{f}> ;
                           fnoc:functionParameter | fnoc:functionOutput <{par}> .
                    OPTIONAL {{ ?mapto fnoc:index | fnoc:property ?index . }}
               }}
          ''', initNs=PrefixMap.NAMESPACES)
          ]
     
     def get_implementation(self, f):
          """
          Retrieve the implementation details of a function.

          Args:
               f (str): The URI of the function.

          Returns:
               tuple: A tuple containing the URI of the mapping and the implementation URI.
                    If no implementation is found, returns (None, None).
          """
          try:
               f = self.check_call(f)

               result = [
                    (x['mapping'], x['imp'])
                    for x in self.query(f'''
                         SELECT ?mapping ?imp WHERE {{
                              ?mapping fno:function <{f}> ;
                                       fno:implementation ?imp .
                         }}
                    ''', initNs=PrefixMap.NAMESPACES) 
               ]
               return result[0] if len(result) > 0 else (None, None)
          except ParseException as e:
               print(f"Error while parsing query when fetching implementation for <{get_name(f)}>: <{e}>")
               return (None, None)
     
     def is_function_implementation(self, s):
          """
          Check if a given function is implemented in Python.

          Args:
               s (str): The URI of the function.

          Returns:
               bool: True if the function is implemented in Python, False otherwise.
          """
          return self.query(f'''ASK WHERE {{ <{s}> a fnoi:PythonFunction . }}''')
     
     def get_positional(self, f):
          """
          Get positional parameters of a function.

          Args:
               f (str): The URI of the function.

          Returns:
               list: A list of positional parameters.
          """
          try:
               f = self.check_call(f)
               positional = sorted([
                    (x['index'].value, x['param'])
                    for x in self.query(f'''
                         SELECT ?index ?param WHERE {{
                              ?mapping fno:function <{f}> ;
                                        a fno:Mapping .
                              ?mapping fno:parameterMapping ?posmapping .
                              ?posmapping fnom:functionParameter ?param ;
                                        fnom:implementationParameterPosition ?index .
                              ?param fno:predicate ?pred .
                              FILTER(?pred != <{to_uri(get_prefix(f), 'self')}>)
                         }}''', initNs=PrefixMap.NAMESPACES)
               ], key=lambda x: x[0])
               return [pos[1] for pos in positional]
          except ParseException as e:
               print(f"Error while parsing query when fetching positional parameters for <{get_name(f)}>: <{e}>")
               return []

     def get_keyword(self, f):
          """
          Get keyword parameters of a function.

          Args:
               f (str): The URI of the function.

          Returns:
               list: A list of keyword parameters.
          """
          try:
               f = self.check_call(f)
               return [
                    x['param']
                    for x in self.query(f'''
                         SELECT ?param WHERE {{
                              ?mapping fno:function <{f}> ;
                                        a fno:Mapping .
                              ?mapping fno:parameterMapping ?keymapping .
                              ?keymapping fnom:functionParameter ?param ;
                                        fnom:implementationProperty ?property .
                         }}''', initNs=PrefixMap.NAMESPACES)
               ]
          except ParseException as e:
               print(f"Error while parsing query when fetching keyword parameters for <{get_name(f)}>: <{e}>")
               return []

     def get_varpositional(self, f):
          """
          Get variable positional parameters of a function.

          Args:
               f (str): The URI of the function.

          Returns:
               str: The variable positional parameter.
          """
          try:
               f = self.check_call(f)
               result = [
                    x['param']
                    for x in self.query(f'''
                         SELECT ?property ?param WHERE {{
                              ?mapping fno:function <{f}> ;
                                        a fno:Mapping .
                              ?mapping fno:parameterMapping ?varmapping .
                              ?varmapping a fnom:VarPositionalParameterMapping ;
                                        fnom:functionParameter ?param .
                         }}''', initNs=PrefixMap.NAMESPACES)
               ]
               return result[0] if len(result) == 1 else None
          except ParseException as e:
               print(f"Error while parsing query when fetching variable positional parameters for <{get_name(f)}>: <{e}>")
               return None

     def is_varpositional(self, f, param):
          """
          Check if a parameter of a function is a variable positional parameter.

          Args:
               f (str): The URI of the function.
               param (str): The URI of the parameter.

          Returns:
               bool: True if the parameter is a variable positional parameter, False otherwise.
          """
          try:
               f = self.check_call(f)
               result = self.query(f'''
                              ASK WHERE {{
                                   ?mapping fno:function <{f}> ;
                                             a fno:Mapping .
                                   ?mapping fno:parameterMapping ?varmapping .
                                   ?varmapping a fnom:VarPositionalParameterMapping ;
                                             fnom:functionParameter <{param}> .
                              }}''', initNs=PrefixMap.NAMESPACES)
               return True if result else False
          except ParseException as e:
               print(f"Error while parsing query when fetching variable positional parameters for <{get_name(f)}>: <{e}>")
               return False

     def get_varkeyword(self, f):
          """
          Get variable keyword parameters of a function.

          Args:
               f (str): The URI of the function.

          Returns:
               str: The variable keyword parameter.
          """
          try:
               f = self.check_call(f)
               result = [
                    x['param']
                    for x in self.query(f'''
                         SELECT ?property ?param WHERE {{
                              ?mapping fno:function <{f}> ;
                                        a fno:Mapping .
                              ?mapping fno:parameterMapping ?varmapping .
                              ?varmapping a fnom:VarPropertyParameterMapping ;
                                        fnom:functionParameter ?param .
                         }}''', initNs=PrefixMap.NAMESPACES)
               ]
               return result[0] if len(result) == 1 else None
          except ParseException as e:
               print(f"Error while parsing query when fetching variable keyword parameters for <{get_name(f)}>: <{e}>")
               return None

     def is_varkeyword(self, f, param):
          """
          Check if a parameter of a function is a variable keyword parameter.

          Args:
               f (str): The URI of the function.
               param (str): The URI of the parameter.

          Returns:
               bool: True if the parameter is a variable keyword parameter, False otherwise.
          """
          try:
               f = self.check_call(f)
               result = self.query(f'''
                              ASK WHERE {{
                                   ?mapping fno:function <{f}> ;
                                             a fno:Mapping .
                                   ?mapping fno:parameterMapping ?varmapping .
                                   ?varmapping a fnom:VarPropertyParameterMapping ;
                                             fnom:functionParameter <{param}> .
                              }}''', initNs=PrefixMap.NAMESPACES)
               return True if result else False
          except ParseException as e:
               print(f"Error while parsing query when fetching variable keyword parameters for <{get_name(f)}>: <{e}>")
               return False
     
          
     def get_param_mapping(self, f, param):
          """
          Retrieve mapping information for a specified parameter of a function.

          Args:
               f (str): The URI of the function.
               param (str): The URI of the parameter for which mapping information is to be retrieved.

          Returns:
               tuple: A tuple containing the index and property mapping of the parameter.
                         If no mapping information is found, (None, None) is returned.

          Raises:
               ParseException: If there is an error while parsing the query.
          """
          try:
               f = self.check_call(f)
               
               result = [
                    (x['index'].value if x['index'] is not None else None,
                     x['property'].value if x['property'] is not None else None)
                    for x in self.query(f'''
                         SELECT ?index ?property WHERE {{
                              ?mapping fno:function <{f}> ;
                              OPTIONAL {{ 
                                   ?mapping fno:parameterMapping ?posmapping .
                                   ?posmapping fnom:functionParameter <{param}> ;
                                               fnom:implementationParameterPosition ?index . 
                              }}
                              OPTIONAL {{ 
                                   ?mapping fno:parameterMapping ?propmapping .
                                   ?propmapping fnom:functionParameter <{param}> ;
                                                fnom:implementationProperty ?property . 
                              }}
                         }}
                    ''', initNs=PrefixMap.NAMESPACES) 
               ]
               return result[0] if len(result) > 0 else (None, None)
          except ParseException as e:
               print(f"Error while parsing query when fetching imp mapping for <{get_name(f)}>: <{e}>")
               return
     
     def get_used_functions(self, c: URIRef):
        """
        Get all used functions inside a composition

        :param c: rdflib.URIRef
            URIRef of the composition you want the used functions from.

        :return: List[rdflib.URIRef]
            A list containing the URIs of all the functions used inside the composition.
        """
        results = self.query(f'''
            SELECT ?call ?func WHERE {{
                ?call fnoc:applies ?func .
                <{c}> fnoc:composedOf ?mapping .
                ?mapping ?map ?node .
                ?node fnoc:constituentFunction ?call .
            }}
            ''', initNs=PrefixMap.NAMESPACES) 

        return  { (x['call'], x['func']) for x in results }
     
     def get_function_description(self, name) -> "PipelineGraph":
          """
          Retrieve the description of a function, including its parameters, outputs, implementation, and other related information.

          Args:
               name (str): The URI of the function for which the description is to be retrieved.

          Returns:
               PipelineGraph: A PipelineGraph object containing the description of the function.

          Raises:
               ParseException: If there is an error while parsing the query.
          """
          # Get Full Function Description
          triples = [
               (name, x['p'], x['o'])
               for x in self.query(f'''
                    SELECT ?p ?o WHERE {{
                         <{name}> ?p ?o .
                    }}''', initNs=PrefixMap.NAMESPACES)
          ]

          # Get parameters
          triples.extend([
               (x['s'], x['p'], x['o'])
               for x in self.query(f'''
                    SELECT ?s ?p ?o WHERE {{
                         <{name}> fno:expects ?s .
                         ?s ?p ?o .
                    }}''', initNs=PrefixMap.NAMESPACES)
          ])

          # Get outputs
          triples.extend([
               (x['s'], x['p'], x['o'])
               for x in self.query(f'''
                    SELECT ?s ?p ?o WHERE {{
                         <{name}> fno:returns ?s .
                         ?s ?p ?o .
                    }}''', initNs=PrefixMap.NAMESPACES)
          ])

          # Get implementation mappings
          triples.extend([
               (x['s'], x['p'], x['o'])
               for x in self.query(f'''
                    SELECT ?s ?p ?o WHERE {{
                         ?s fno:function <{name}> .
                         ?s ?p ?o .
                    }}''', initNs=PrefixMap.NAMESPACES)
          ])
          triples.extend([
               (x['s'], x['p'], x['o'])
               for x in self.query(f'''
                    SELECT ?s ?p ?o WHERE {{
                         ?mapping fno:function <{name}> .
                         ?mapping ?type ?s .
                         ?s ?p ?o .
                    }}''', initNs=PrefixMap.NAMESPACES)
          ])

          # Get implementation
          triples.extend([
               (x['s'], x['p'], x['o'])
               for x in self.query(f'''
                    SELECT ?s ?p ?o WHERE {{
                         ?mapping fno:function <{name}> ;
                                  fno:implementation ?s .
                         ?s ?p ?o .
                    }}''', initNs=PrefixMap.NAMESPACES)
          ])

          # Get Parameter Descriptions
          for param in self.get_parameters(name):
               triples.extend([
                    (param, x['p'], x['o'])
                    for x in self.query(f'''
                         SELECT ?p ?o WHERE {{
                              <{param}> ?p ?o .
                         }}''', initNs=PrefixMap.NAMESPACES)
               ])

               # Get Parameter types
               triples.extend([
                    (x['s'], x['p'], x['o'])
                    for x in self.query(f'''
                         SELECT ?s ?p ?o WHERE {{
                              <{param}> fno:type ?s .
                         ?s ?p ?o .
                         }}''', initNs=PrefixMap.NAMESPACES)
               ])
          
          # Get Self Description
          param = self.get_self(name)
          if param:
               triples.extend([
                    (param, x['p'], x['o'])
                    for x in self.query(f'''
                         SELECT ?p ?o WHERE {{
                              <{param}> ?p ?o .
                         }}''', initNs=PrefixMap.NAMESPACES)
               ])

               # Get Self type
               triples.extend([
                    (x['s'], x['p'], x['o'])
                    for x in self.query(f'''
                         SELECT ?s ?p ?o WHERE {{
                             <{param}> fno:type ?s .
                         ?s ?p ?o .
                         }}''', initNs=PrefixMap.NAMESPACES)
               ])
          
          # Get Output Description
          out = self.get_output(name)
          if out:
               triples.extend([
                    (out, x['p'], x['o'])
                    for x in self.query(f'''
                         SELECT ?p ?o WHERE {{
                              <{out}> ?p ?o .
                         }}''', initNs=PrefixMap.NAMESPACES)
               ])

               # Get output type
               triples.extend([
                    (x['s'], x['p'], x['o'])
                    for x in self.query(f'''
                         SELECT ?s ?p ?o WHERE {{
                              <{out}> fno:type ?s .
                         ?s ?p ?o .
                         }}''', initNs=PrefixMap.NAMESPACES)
               ])
          
          # Get Self Output Description
          self_out = self.get_self_output(name)
          if self_out:
               triples.extend([
                    (self_out, x['p'], x['o'])
                    for x in self.query(f'''
                         SELECT ?p ?o WHERE {{
                              <{self_out}> ?p ?o .
                         }}''', initNs=PrefixMap.NAMESPACES)
               ])

               # Get output type
               triples.extend([
                    (x['s'], x['p'], x['o'])
                    for x in self.query(f'''
                         SELECT ?s ?p ?o WHERE {{
                              <{self_out}> fno:type ?s .
                         ?s ?p ?o .
                         }}''', initNs=PrefixMap.NAMESPACES)
               ])
          
          # Get all function calls
          triples.extend([
               (x['call'], PrefixMap.NAMESPACES['fnoc']['applies'], name)
               for x in self.query(f'''
                    SELECT ?call WHERE {{
                         ?call fnoc:applies <{name}> .
                    }}
               ''', initNs=PrefixMap.NAMESPACES)
          ])

          desc = PrefixMap.bind_namespaces(PipelineGraph())
          [ desc.add(x) for x in triples ]
          return desc