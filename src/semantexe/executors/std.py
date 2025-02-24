from abc import ABC, abstractmethod

from ..graph import ExecutableGraph
from .executeable import Function, AppliedFunction

class Executor(ABC):
    
    def __init__(self, g: ExecutableGraph):
        self.g = g
    
    def execute(self, fun: Function, *args, **kwargs):
        if not self.accepts(fun):
            raise Exception(f"Unable to accept ...")
        
        if not fun.comp:
            return self.execute_function(fun)
        
        try:
            return fun.comp.execute(self)
        except Exception as e:
            pass
        
        try:
            return self.alt_mapping(fun)
        except Exception as e:
            pass
        
        try:
            return self.alt_executor(fun)
        except Exception as e:
            pass
    
    @abstractmethod
    def accepts(self, fun: Function):
        pass     
    
    @abstractmethod
    def alt_executor(self, g: ExecutableGraph, fun: Function):
        pass
    
    @abstractmethod
    def alt_mapping(self, g: ExecutableGraph, fun: Function):
        pass
    
    @abstractmethod
    def execute_function(self, fun: Function):
        pass
    
    @abstractmethod
    def execute_applied(self, fun: AppliedFunction):
        pass