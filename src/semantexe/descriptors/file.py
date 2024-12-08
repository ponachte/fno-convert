from ..graph import ExecutableGraph
from ..builders.docker import DockerBuilder
from ..builders.python import PythonBuilder

from pathlib import Path
from rdflib import URIRef

def get_all_filepaths(directory):
    dir_path = Path(directory)
    # Use rglob('*') to recursively find all files in all subdirectories
    return [str(file) for file in dir_path.rglob('*') if file.is_file()]

class DirectoryDescriptor:
    
    @staticmethod
    def describe(g: ExecutableGraph, directory):
        descriptions = []
        for file_path in get_all_filepaths(directory):
            try:
                descriptions.append(FileDescriptor.describe(g, file_path))
            except ValueError as e:
                descriptions.append(file_path)
        return descriptions
        
class FileDescriptor:
    
    @staticmethod    
    def describe(g: ExecutableGraph, file_path):
        # Python file
        if file_path.endswith(".py"):
            uri = PythonBuilder.file_uri(file_path)
            if not g.exists(uri):
                from .python import PythonDescriptor
                PythonDescriptor(g).from_file(file_path, uri)
            return uri
        # Dockerfile
        elif file_path.endswith("Dockerfile"):
            uri = DockerBuilder.file_uri(file_path)
            if not g.exists(uri):
                from .docker import DockerDescriptor
                DockerDescriptor(g).from_file(file_path, uri)
            return uri
        # Other file type
        return URIRef(f"file://{file_path}")