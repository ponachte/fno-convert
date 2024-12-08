import os, hashlib

from ..graph import ExecutableGraph
from ..map import PrefixMap

from rdflib import RDF, URIRef


class DockerBuilder:
    
    @staticmethod
    def file_uri(file_path):
        dir = os.path.dirname(file_path)
        dir_name = os.path.basename(dir)
        unique_hash = hashlib.sha256(file_path.encode()).hexdigest()[:8]
        return PrefixMap.ns('docker')[f"{dir_name}{unique_hash}"]
    
    @staticmethod
    def describe_dockerfile(g: ExecutableGraph, uri, file_path):
        ### DOCKERONTO DOCKERFILE ###
        g.add((uri, RDF.type, PrefixMap.ns('do').Dockerfile))
        
        ### FNO IMPLEMENTATION ###
        g.add((uri, RDF.type, PrefixMap.ns('fnoi').Dockerfile))
        g.add((uri, PrefixMap.ns('fnoi').file, URIRef(f"file://{file_path}")))
        
        return uri
        
        