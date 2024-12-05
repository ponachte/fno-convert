from py2rdf.describe.comp_descriptor import CompositionDescriptor
from py2rdf.execute.executeable import Composition
from py2rdf.graph import PipelineGraph
import ast, astpretty, importlib, rdflib

if __name__ == "__main__":
  g = PipelineGraph().parse('graphs/for_loop.ttl')
  print(g.serialize(format="turtle"))
  exe = Composition(g, rdflib.URIRef("http://www.example.com#for_loopComposition"))
  exe.execute()