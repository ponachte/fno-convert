from rdflib import Namespace, Graph, Literal
from pkg_resources import resource_filename
import inspect
import importlib
import sys
from typing import Any
from types import FunctionType, NoneType
from datetime import datetime, date, time
from decimal import Decimal

# Standard RDF prefixes
std_prefixes = {
    'rdf': "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    'rdfs': "http://www.w3.org/2000/01/rdf-schema#",
    'xsd': "http://www.w3.org/2001/XMLSchema#",
    'ex': "http://www.example.com#",
    'pf': "http://www.example.com/pythonfunctions#",
    'dcterms': "http://purl.org/dc/terms/",
    'doap': "http://usefulinc.com/ns/doap#",
    'fno': "https://w3id.org/function/ontology#",
    'fnoi': "https://w3id.org/function/vocabulary/implementation#",
    'fnom': "https://w3id.org/function/vocabulary/mapping#",
    'fnoc': "https://w3id.org/function/vocabulary/composition#",
    'fnof': "http://example.com/vocabulary/flow#",
    'ptype': "http://example.com/ptype#",
    'prov': "http://www.w3.org/ns/prov#",
    'cc': "http://creativecommons.org/ns#",
    'foaf': "http://xmlns.com/foaf/0.1/",
    'grel': "http://users.ugent.be/~bjdmeest/function/grel.ttl#",
    'void': "http://rdfs.org/ns/void#",
    'mls': "http://www.w3.org/ns/mls#",
    'mlflow': "http://www.example.com/mlflow#",
    'do': "http://linkedcontainers.org/vocab#",
}

# Dictionaries for storing RDF graphs
DICTIONARIES = {}
"""try:
    DICTIONARIES['grel'] = Graph().parse(std_prefixes['grel'], format='turtle')
except:
    print("No internet connection")"""

# RDF graph for Python function descriptions
PFDOC = Graph().parse('./src/semantify/fno_dict.ttl', format='turtle')


def load_function_from_source(file_path, function_name):
    """
    Load a function from a Python source file.

    Args:
        file_path (str): The path to the Python source file.
        function_name (str): The name of the function to load.

    Returns:
        function: The loaded function object.
    """
    module_name = file_path.split('/')[-1][:-len('.py')]
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None:
        raise ImportError(f"Cannot find module spec for {file_path}")
    
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)

    try:
        func = getattr(module, function_name)
        return func
    except AttributeError as e:
        return


def is_standard_literal_type(instance):
    """
    Check if the instance is of a type that RDFlib recognizes as a standard literal type.
    """
    standard_types = (str, int, bool, float, datetime, date, time, Decimal)
    return isinstance(instance, standard_types)


class PrefixMap:
    """
    Utility class for managing RDF namespace prefixes.
    """
    NAMESPACES = {k: Namespace(v) for k, v in std_prefixes.items()}

    @staticmethod
    def ns(prefix):
        """
        Get the namespace URI for a given prefix.

        Args:
            prefix (str): The namespace prefix.

        Returns:
            Namespace: The namespace URI.
        """
        return PrefixMap.NAMESPACES[prefix]

    @staticmethod
    def bind_namespaces(g):
        """
        Bind namespace prefixes to an RDF graph.

        Args:
            g (Graph): The RDF graph to bind namespaces to.

        Returns:
            Graph: The RDF graph with namespaces bound.
        """
        for k, v in PrefixMap.NAMESPACES.items():
            g.bind(k, v)
        return g
    
    @staticmethod
    def update_namespaces(prefix, url):
        """
        Update the namespace with a new prefix and URI.

        Args:
            prefix (str): The namespace prefix.
            url (str): The namespace URI.
        """
        PrefixMap.NAMESPACES.update({prefix: Namespace(url)})
    
    @staticmethod
    def set_base(uri):
        """
        Set the base URI for the default namespace.

        Args:
            uri (str): The base URI.
        """
        PrefixMap.NAMESPACES[''] = Namespace(uri)
    
    @staticmethod
    def base():
        """
        Get the base URI for the default namespace.

        Returns:
            str: The base URI.
        """
        return PrefixMap.ns('ex')
    
    @staticmethod
    def pf():
        """
        Get the base URI for the Python functions namespace.

        Returns:
            str: The base URI.
        """
        return PrefixMap.ns('pf')


class ImpMap:
    """
    Utility class for mapping Python function implementations to RDF.
    """
    
    @staticmethod
    def imp_to_rdf(imp, imp_name=None, self=None, static=None):
        """
        Convert a Python function implementation to RDF.

        Args:
            imp (function): The Python function or method.
            imp_name (str, optional): The name of the implementation.
            self (URI, optional): The type of the self parameter.
            static (bool, optional): Indicates if the method is static.

        Returns:
            tuple: A tuple containing the URI of the implementation and the RDF graph.
        """
        # TODO handle multiple param annotations
        if imp is inspect._empty or isinstance(imp, str):
            imp = Any
        elif imp is None:
            imp = type(None)
        
        if imp_name is None:
            imp_name = getattr(imp, '__name__', getattr(type(imp), '__name__', str(imp)))

        # Create a new graph
        g = PrefixMap.bind_namespaces(Graph())

        # Add class type and metadata

        if inspect.isclass(imp) or imp is Any:
            imp_uri = PrefixMap.base()[f"{imp_name}PythonClass"]
            g.add((imp_uri, PrefixMap.ns('rdf').type, PrefixMap.ns('fnoi').PythonClass))
        else:
            imp_uri = PrefixMap.base()[f"{imp_name}PythonImplementation"]
            # Make a distinction between a function and a method
            if self is not None:
                g.add((imp_uri, PrefixMap.ns('rdf').type, PrefixMap.ns('fnoi').PythonMethod))

                # Add the type of the self parameter
                g.add((imp_uri, PrefixMap.ns('fnoi').methodOf, self))
                g.add((imp_uri, PrefixMap.ns('fnoi').static, Literal(static)))
            else:
                g.add((imp_uri, PrefixMap.ns('rdf').type, PrefixMap.ns('fnoi').PythonFunction))


        g.add((imp_uri, PrefixMap.ns('rdfs').label, Literal(getattr(imp, '__name__', str(imp)))))
        g.add((imp_uri, PrefixMap.ns('rdf').type, PrefixMap.ns('prov').Agent))
        if hasattr(imp, "__module__"):
            g.add((imp_uri, PrefixMap.ns('fnoi').module, Literal(imp.__module__)))
            if '.' in imp.__module__:
                g.add((imp_uri, PrefixMap.ns('fnoi').package, Literal(imp.__module__.split('.')[0]))) 
        if hasattr(imp, '__doc__'):
            g.add((imp_uri, PrefixMap.ns('dcterms').description, Literal(imp.__doc__)))

        # Capture the module file path if possible
        try:
            module_file = inspect.getfile(imp)

            # Do not add the file of externally installed modules
            if 'site-packages' not in module_file:
                g.add((imp_uri, PrefixMap.ns('fnoi').file, Literal(module_file)))
        except TypeError as e:
            pass

        return imp_uri, g
    
    @staticmethod
    def rdf_to_imp(g: Graph, s):
        """
        Convert RDF representing a function implementation to a Python function or method.

        Args:
            g (Graph): The RDF graph containing the implementation.
            s (str): The URI of the implementation.

        Returns:
            function: The Python function or method.
        """
        if s is None:
            return Any
        
        if s.split('#')[-1] == 'NoneType':
            return NoneType
                
        result = [
            (x['label'].value, 
             x['module'].value if x['module'] is not None else None, 
             x['package'].value if x['package'] is not None else None,
             x['file'].value if x['file'] is not None else None,
             x['self_class'])
            for x in g.query(f'''
            SELECT ?type ?label ?module ?package ?file ?self_class WHERE {{
                VALUES ?type {{ fnoi:PythonClass fnoi:PythonFunction fnoi:PythonMethod }}
                <{s}> a ?type ;
                      rdfs:label ?label ;
                OPTIONAL {{ <{s}> fnoi:module ?module . }}
                OPTIONAL {{ <{s}> fnoi:package ?package . }}
                OPTIONAL {{ <{s}> fnoi:file ?file . }}
                OPTIONAL {{ <{s}> fnoi:methodOf ?self_class . }}
            }}''', initNs=PrefixMap.NAMESPACES)]
        
        try:
            if result:
                label, module, package, file, self_class = result[0]
                if file is not None:
                    return load_function_from_source(file, label)
                if module is not None:
                    if module == "builtins" and hasattr(__builtins__, label):
                        return getattr(__builtins__, label)   
                    module_obj = importlib.import_module(module, package)
                    if hasattr(module_obj, label):
                        return getattr(module_obj, label)
                elif self_class is not None:
                    self_obj = ImpMap.rdf_to_imp(g, self_class)
                    if hasattr(self_obj, label):
                        return getattr(self_obj, label)
        except Exception as e:
            print(f"Error while trying to get implementation from {s.split('#')[-1]}: {e}")
            return Any
            
        return Any
    
    @staticmethod
    def any():
        """
        Get the RDF representation of the 'Any' type.

        Returns:
            tuple: A tuple containing the URI of the 'Any' type and the RDF graph.
        """
        return ImpMap.imp_to_rdf(inspect._empty)


class InstMap:
    """
    Utility class for mapping Python literals and instances to RDF.
    """
    
    @staticmethod
    def inst_to_rdf(inst):
        """
        Convert a Python literal or instance to RDF.

        Args:
            inst: The Python literal or instance.

        Returns:
            tuple: A tuple containing the RDF literal and the type description graph.
        """
        if is_standard_literal_type(inst):
            return Literal(inst), None
        if type(inst) is type or isinstance(inst, FunctionType):
            inst_type, type_desc = ImpMap.imp_to_rdf(inst)
        else:
            inst_type, type_desc = ImpMap.imp_to_rdf(type(inst))
        return Literal(inst, datatype=inst_type), type_desc


class FnODescriptionMap:
    """
    Utility class for managing and accessing RDF dictionaries of function descriptions.
    """
    
    @staticmethod
    def add_dict(prefix, url, format):
        """
        Add an RDF dictionary of function descriptions.

        Args:
            prefix (str): The namespace prefix for the dictionary.
            url (str): The URL of the RDF dictionary.
            format (str): The format of the RDF data.
        """
        PrefixMap.update_namespaces(prefix, url)
        DICTIONARIES.update({prefix: Graph().parse(url, format=format)})

    @staticmethod
    def get_std(name):
        """
        Get a standard function description from the standard function document.

        Args:
            name (str): The name of the function.

        Returns:
            tuple: A tuple containing the URI of the function and the RDF graph.
        """
        if FnODescriptionMap.check_dict(name, 'pf', PFDOC):
            return PrefixMap.ns('pf')[name], PFDOC

    @staticmethod
    def get_description(name: str):
        """
        Get a function description from the RDF dictionary.

        Args:
            name (str): The name of the function.

        Returns:
            tuple: A tuple containing the URI of the function and the RDF graph.
        """
        for prefix, graph in DICTIONARIES.items():
            if FnODescriptionMap.check_dict(name, prefix, graph):
                return PrefixMap.ns(prefix)[name], graph
        return None

    @staticmethod
    def check_dict(name: str, prefix, graph: Graph) -> bool:
        """
        Check if a function description exists in the RDF dictionary.

        Args:
            name (str): The name of the function.
            prefix (str): The namespace prefix for the dictionary.
            graph (Graph): The RDF graph containing the dictionary.

        Returns:
            bool: True if the function description exists, False otherwise.
        """
        if graph.query(f'''ASK WHERE {{ {prefix}:{name} a fno:Function . }}''', initNs=PrefixMap.NAMESPACES):
            return True
        return False