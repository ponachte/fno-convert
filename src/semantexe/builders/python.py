import os, hashlib

from ..graph import ExecutableGraph
from ..map import PrefixMap

from rdflib import RDF, URIRef


class PythonBuilder:
    
    @staticmethod
    def file_uri(file_path):
        file_name, _ = os.path.splitext(os.path.basename(file_path))
        unique_hash = hashlib.sha256(file_path.encode()).hexdigest()[:8]
        return PrefixMap.ns('python')[f"{file_name}{unique_hash}"]
    
    @staticmethod
    def describe_pythonfile(g: ExecutableGraph, uri, file_path):
        
        ### FNO IMPLEMENTATION ###
        g.add((uri, RDF.type, PrefixMap.ns('fnoi').PythonFile))
        g.add((uri, PrefixMap.ns('fnoi').file, URIRef(f"file://{file_path}")))
        
        return uri