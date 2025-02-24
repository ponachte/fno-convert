from .executeable import Composition, Function, AppliedFunction
from .store import MappingType
from ..graph import ExecutableGraph
from ..prefix import Prefix

import importlib
import importlib.util
import sys

from datetime import datetime
from typing import Any
from types import NoneType

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

class PythonExecutor:
    
    @staticmethod
    def python_object(g: ExecutableGraph, uri):
        if uri is None:
            return Any
        
        if uri.split('#')[-1] == 'NoneType':
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
                <{uri}> a ?type ;
                      rdfs:label ?label ;
                OPTIONAL {{ <{uri}> fnoi:module ?module . }}
                OPTIONAL {{ <{uri}> fnoi:package ?package . }}
                OPTIONAL {{ <{uri}> fnoi:file ?file . }}
                OPTIONAL {{ <{uri}> fnoi:methodOf ?self_class . }}
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
                    self_obj = PythonExecutor.python_object(g, self_class)
                    if hasattr(self_obj, label):
                        return getattr(self_obj, label)
        except Exception as e:
            print(f"Error while trying to get implementation from {uri.split('#')[-1]}: {e}")
            return Any
            
        return Any
    
    @staticmethod
    def execute(g: ExecutableGraph, exe):
        if isinstance(exe, Composition):
            if g.represents_python(exe.uri):
                # Try to get python implementations for all functions
                return PythonExecutor.execute_comp(g, exe)
        elif isinstance(exe, Function):
            return PythonExecutor.execute_fun(exe)
        elif isinstance(exe, AppliedFunction):
            return PythonExecutor.execute_applied(exe)
    
    @staticmethod
    def execute_comp(comp: Composition):
        # Execute each function and follow the control flow until no new function can be selected
        call = comp.start
        while call is not None:
            # Get the FnO Function Executeable
            fun = comp.functions[call]
            # Fetch inputs from mappings
            comp.ingest(fun)
            # Execute
            PythonExecutor.execute(fun)
            # Signify execution to relevant mappings
            if call in comp.priorities:
                for mapping in comp.priorities[call]:
                    mapping.set_priority(call)
            # Get the URI of the next executeable
            call = fun.next_executable()
        
        # If this composition represents the internal flow of a function, set the output
        if comp.rep:
            comp.ingest(comp.scope)
    
    @staticmethod
    def execute_fun(fun: Function):
        if fun.comp:
            PythonExecutor.execute_comp(fun)
        else:            
            # If there is a fun input, use the function object from that terminal's uri value
            if fun.self_input is not None:
                fun.f_object = getattr(fun.self_input.value, fun.name, None)
            
            # Only execute when there is a function object
            if fun.f_object is not None:
                args = []
                vargs = []
                keyargs = {}
                vkeyargs = {}

                for param in fun.inputs():
                    mapping = param.param_mapping
                    if not param.value_set:
                        if mapping.has_default:
                            param.set(mapping.default)
                        else:
                            raise Exception(f"Parameter {param.name} not set.")
                    value = param.get()

                    if mapping.get_type() == MappingType.VARPOSITIONAL:
                        vargs = value
                    elif mapping.get_type() == MappingType.VARKEYWORD:
                        if isinstance(value, dict):
                            vkeyargs = value
                    elif mapping.get_type() == MappingType.KEYWORD:
                        keyargs[mapping.get_property()] = value
                    elif mapping.get_type() == MappingType.POSITIONAL:
                        args.append((mapping.get_property(), value))
                
                # correctly sort the positional arguments
                args = [ x[1] for x in sorted(args, key=lambda x: x[0])]

                # Remove the fun parameter as we already have the method object
                if fun.self_input is not None:
                    if 'fun' in keyargs:
                        del keyargs['fun']
                    else:
                        args = args[1:]
                
                try:
                    fun.startedAt = datetime.now()
                    ret = fun.f_object(*args, *vargs, **keyargs, **vkeyargs)
                    fun.endedAt = datetime.now()
                    
                    fun.output.set(ret)
                    if fun.self_output is not None:
                        fun.self_output.set(fun.self_input.get())
                except StopIteration as e:
                    raise e
                except Exception as e:
                    print(f"Error while executing {fun.name} with")
                    print(f"\targs: {args}")
                    print(f"\tvargs: {vargs}")
                    print(f"\tkeyargs: {",".join([f"{key}={arg}" for key, arg in keyargs.items()])}")
                    print(f"\tvkeyargs: {",".join([f"{key}={arg}" for key, arg in vkeyargs.items()])}")
                    raise e
    
    @staticmethod
    def execute_applied(fun: AppliedFunction):
        if fun.iterate is not None:
            try:
                PythonExecutor.execute_fun(fun)
                fun._next = fun.iterate
            except StopIteration:
                fun._next = fun.next
        elif fun.iftrue is not None:
            PythonExecutor.execute_fun(fun)
            fun._next = fun.iftrue if fun.output.value else fun.iffalse
        else:
            PythonExecutor.execute_fun(fun)
            fun._next = fun.next