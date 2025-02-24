import hashlib

from rdflib import Literal, RDF, URIRef
from docker.models.images import Image

from ..builders import FnOBuilder
from ..prefix import Prefix
from ..graph import ExecutableGraph

class DockerMapper:
    
    @staticmethod
    def dockerfile_uri(name, path):
        unique_hash = hashlib.sha256(path.encode()).hexdigest()[:8]
        return Prefix.ns('docker')[f"{name}{unique_hash}"]
    
    @staticmethod
    def describe_dockerimage(g: ExecutableGraph, image: Image):
        uri = Prefix.ns('docker')[image.short_id.removeprefix('sha256:')]
        g.add((uri, RDF.type, Prefix.ns('do').Image))
        g.add((uri, RDF.type, Prefix.ns('fnoi').DockerImage))
        
        # Image metadata
        # TODO Dockerpedia annotater, now simply state labels and the dockerfile
        for tag in image.tags:
            g.add((uri, Prefix.ns('rdfs').label, Literal(tag)))
        
        return uri