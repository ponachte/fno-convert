from rdflib import RDF, URIRef, Literal

from ..graph import ExecutableGraph
from ..prefix import Prefix
from .fno import FnOBuilder

class DockerBuilder:
    
    @staticmethod
    def describe_dockerfile(g: ExecutableGraph, uri, file_path):   
        ### DOCKERONTO DOCKERFILE ###
        g.add((uri, RDF.type, Prefix.ns('do').Dockerfile))
        
        ### FNO FUNCTION ###
        output = FnOBuilder.describe_output(g, 
                                            uri=Prefix.do().ImageOutput, 
                                            type=Prefix.do().Image,
                                            pred="outputImage")
        FnOBuilder.describe_function(g, uri=uri, outputs=[output])
        
        ### FNO IMPLEMENTATION ###
        
        file_uri = URIRef(f"{uri}DockerfileImplementation")
        g.add((file_uri, RDF.type, Prefix.ns('fnoi').Dockerfile))
        g.add((file_uri, RDF.type, Prefix.ns('do').Dockerfile))
        g.add((file_uri, Prefix.ns('fnoi').file, URIRef(f"file://{file_path}")))
        
        ### FNO MAPPING ###
        
        FnOBuilder.describe_mapping(g, uri, file_uri, output=output)
        
        return uri
    
    @staticmethod
    def contains(g, image, entity):
        g.add((image, Prefix.do().contains, entity))
        
    @staticmethod
    def defaultInput(g, image, input):
        g.add((image, Prefix.do().defaultInput, Literal(input)))