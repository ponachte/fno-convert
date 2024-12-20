import os, traceback

from ..graph import ExecutableGraph
from .file import FileDescriptor

class Descriptor:
    
    @staticmethod    
    def describe(g: ExecutableGraph, value, dir=None):
        if os.path.isfile(value):
            try:
                value = FileDescriptor.describe(g, value)
            except ValueError as e:
                print(f"Error while describing {value}: {e}")
                print(traceback.format_exc())
        elif dir is not None: 
            value = Descriptor.describe(g, os.path.join(dir, value))

        return value