import os
from rdflib import RDF, URIRef, Literal

from ..graph import ExecutableGraph
from ..prefix import Prefix
from .fno import FnOBuilder

class DockerBuilder:
    
    @staticmethod
    def describe_dockerfile(g: ExecutableGraph, rel_path, fun_uri, file_uri):
        abs_path = os.path.abspath(f"./{rel_path}")
        dir_name = os.path.dirname(rel_path)
           
        ### DOCKERONTO DOCKERFILE ###
        g.add((fun_uri, RDF.type, Prefix.ns('do').Dockerfile))
        
        ### FNO FUNCTION ###
        output = FnOBuilder.describe_output(g, 
                                            uri=Prefix.do().ImageOutput, 
                                            type=Prefix.do().Image,
                                            pred="outputImage")
        FnOBuilder.describe_function(g, uri=fun_uri, name=f"{dir_name}Dockerfile", outputs=[output])
        
        ### FNO IMPLEMENTATION ###
        
        g.add((file_uri, RDF.type, Prefix.ns('fnoi').Dockerfile))
        g.add((file_uri, RDF.type, Prefix.ns('do').Dockerfile))
        g.add((file_uri, Prefix.ns('fnoi').file, URIRef(f"file://{abs_path}")))
        
        ### FNO MAPPING ###
        
        return FnOBuilder.describe_mapping(g, fun_uri, file_uri, output=output)

    
    @staticmethod
    def includes(g, image, entity):
        g.add((image, Prefix.do().includes, entity))
        
    @staticmethod
    def defaultInput(g, image, input):
        g.add((image, Prefix.do().defaultInput, Literal(input)))