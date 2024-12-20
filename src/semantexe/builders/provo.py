from ..graph import ExecutableGraph
from ..prefix import Prefix
from rdflib import RDF, BNode

class ProvBuilder:
    
    @staticmethod
    def entity(g, uri):
        g.add((uri, RDF.type, Prefix.prov().Entity))
    
    @staticmethod
    def activity(g, uri):
        g.add((uri, RDF.type, Prefix.prov().Activity))
    
    @staticmethod
    def agent(g, uri):
        g.add((uri, RDF.type, Prefix.prov().Agent))
        
    @staticmethod
    def alternateOf(g, alt, src):
        g.add((alt, Prefix.prov().alternateOf, src))
        
    @staticmethod
    def derivedFrom(g, der, src):
        g.add((der, Prefix.prov().derivedFrom, src))
    
    @staticmethod
    def execution(g: ExecutableGraph, exe, fun, imp, used, generated):
        
        # Set PROV-O types
        ProvBuilder.activity(g, exe)
        ProvBuilder.entity(g, fun)
        ProvBuilder.agent(g, imp)
        
        # Set used
        g.add((exe, Prefix.prov().used, fun))
        for u in used:
            ProvBuilder.entity(used)
            g.add((exe, Prefix.prov().used, u))
        
        # Associate implementation
        association = BNode()
        triples = [
            (exe, Prefix.prov().wasAssociatedWith, imp),
            (association, RDF.type, Prefix.prov().Association),
            (exe, Prefix.prov().qualifiedAssociation, association),
            (association, Prefix.prov().agent, imp),
            (association, Prefix.prov().hadRole, Prefix.base().implementation),
            (association, Prefix.prov().hadPlan, fun)
        ]
        [ g.add(x) for x in triples ]
    
        # Set generated
        g.add((generated, Prefix.prov().wasGeneratedBy, exe))     