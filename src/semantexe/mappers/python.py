import inspect, importlib, importlib.util, sys, hashlib

from typing import Any
from types import NoneType, FunctionType
from rdflib import Literal, URIRef
from datetime import datetime, date, time
from decimal import Decimal

from ..prefix import Prefix
from ..builders import PythonBuilder
from ..graph import ExecutableGraph

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


class PythonMapper:
    
    @staticmethod
    def uri(name, m_name=None, p_name=None, f_name=None):
        combined = ''.join(str(item) for item in [m_name, p_name, f_name] if item)
        unique_hash = hashlib.sha256(combined.encode()).hexdigest()[:8]
        return Prefix.ns('python')[f"{name}{unique_hash}"]
    
    @staticmethod
    def imp_to_rdf(g: ExecutableGraph, imp, imp_name=None, self=None, static=None):
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
    
        m_name = p_name = f_name = doc = None
        
        ### IMPLEMENTATION METADATA ###
        
        # Module & package
        if hasattr(imp, "__module__"):
            m_name = Literal(imp.__module__)
            if '.' in imp.__module__:
                p_name = imp.__module__.split('.')[0]
        
        # File
        try:
            module_file = inspect.getfile(imp)

            # Do not add the file of externally installed modules
            if 'site-packages' not in module_file:
                f_name = module_file
        except TypeError as e:
            pass
        
        # Docstring
        if hasattr(imp, '__doc__'):
            doc = imp.__doc__
        
        ### DESCRIBE IMPLEMENTATION ###
        
        imp_uri = PythonMapper.uri(imp_name, m_name, p_name, f_name)
        PythonBuilder.describe_imp(g, imp_uri, imp_name, m_name, p_name, f_name, doc)

        # Determine implementation type

        if inspect.isclass(imp) or imp is Any:
            PythonBuilder.describe_class(g, imp_uri)
        elif self is not None:
            PythonBuilder.describe_method(g, imp_uri, self, static)
        else:
            PythonBuilder.describe_function(g, imp_uri)

        return imp_uri
    
    @staticmethod
    def rdf_to_imp(g: ExecutableGraph, s):
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
            }}''', initNs=Prefix.NAMESPACES)]
        
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
                    self_obj = PythonMapper.rdf_to_imp(g, self_class)
                    if hasattr(self_obj, label):
                        return getattr(self_obj, label)
        except Exception as e:
            print(f"Error while trying to get implementation from {s.split('#')[-1]}: {e}")
            return Any
            
        return Any
    
    @staticmethod
    def inst_to_rdf(g: ExecutableGraph, inst):
        """
        Convert a Python literal or instance to RDF.

        Args:
            inst: The Python literal or instance.

        Returns:
            tuple: A tuple containing the RDF literal and the type description graph.
        """
        if isinstance(inst, URIRef):
            return inst, None
        if is_standard_literal_type(inst):
            return Literal(inst)
        if type(inst) is type or isinstance(inst, FunctionType):
            inst_type = PythonMapper.imp_to_rdf(g, inst)
        else:
            inst_type = PythonMapper.imp_to_rdf(g, type(inst))
        return Literal(inst, datatype=inst_type)
    
    @staticmethod
    def any(g: ExecutableGraph):
        """
        Get the RDF representation of the 'Any' type.

        Returns:
            tuple: A tuple containing the URI of the 'Any' type and the RDF graph.
        """
        return PythonMapper.imp_to_rdf(g, inspect._empty)