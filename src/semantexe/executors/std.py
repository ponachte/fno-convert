from abc import ABC, abstractmethod
import traceback, os

from ..graph import ExecutableGraph
from .executeable import Function, AppliedFunction

class Executor(ABC):
    
    def __init__(self, g: ExecutableGraph):
        self.g = g
        self.depth = 0
    
    def execute(self, fun: Function, *args, **kwargs):
        # Consider all available mappings
        if fun.imp is None:
            for mapping, imp in self.g.fun_to_imp(fun.fun_uri):
                if self.accepts(mapping, imp):
                    fun.map = mapping
                    fun.imp = imp
        
                    try:
                        return self.execute_with_mapping(fun, args, kwargs)
                    except Exception as e:
                        print(f"Error when executing Mapping {fun.map} with executor {self.__class__.__name__}: {e}")
                        traceback.print_exc()
        # Consider available mappings for implementation
        elif fun.map is None:
            for mapping in self.g.mappings(fun.fun_uri, fun.imp):
                if self.accepts(mapping, fun.imp):
                    fun.map = mapping
        
                    try:
                        return self.execute_with_mapping(fun, args, kwargs)
                    except Exception as e:
                        print(f"Error when executing Mapping {fun.map} with executor {self.__class__.__name__}: {e}")
                        traceback.print_exc()
        # Execute with given mapping and implementation
        else:
            try:
                return self.execute_with_mapping(fun, args, kwargs)
            except Exception as e:
                print(f"Error when executing Mapping {fun.map} with executor {self.__class__.__name__}: {e}")
                traceback.print_exc()
                        
        print(f"Trying alternative executor for {fun.fun_uri}")
        return self.alt_executor(fun)
    
    def execute_with_mapping(self, fun: Function, *args, **kwargs):
        if self.accepts(fun.map, fun.imp):
            # Change workdir if toplevel function
            if self.depth == 0:
                file = self.g.get_file(fun.imp)
                file_dir = os.path.dirname(file)
                current_wd = os.getcwd()
                os.chdir(file_dir)
            
            self.map(fun)

            self.depth += 1
            out = self.execute_function(fun, *args, **kwargs)
            self.depth -= 1
            
            # Change back to the previous workdir
            if self.depth == 0:
                os.chdir(current_wd)
                
            return out
    
    @abstractmethod
    def accepts(self, mapping, imp):
        pass
    
    @abstractmethod
    def map(self, fun: Function):
        pass
    
    @abstractmethod
    def execute_function(self, fun: Function, *args, **kwargs):
        pass
    
    @abstractmethod
    def execute_applied(self, fun: AppliedFunction):
        pass     
    
    @abstractmethod
    def alt_executor(self, fun: Function):
        pass