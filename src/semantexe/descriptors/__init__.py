import os

from .file import FileDescriptor
from ..graph import ExecutableGraph

class Descriptor:
    
    @staticmethod    
    def describe(g: ExecutableGraph, value, dir=None):
        if os.path.isfile(value):
            try:
                value = FileDescriptor.describe(g, value)
            except ValueError as e:
                print(f"Error while describing {value}: {e}")
        elif dir is not None: 
            value = Descriptor.describe(g, os.path.join(dir, value))

        return value