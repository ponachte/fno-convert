from rdflib import Graph, Namespace
from py2rdf.graph import PipelineGraph, get_name
from py2rdf.map import PrefixMap

def function_activity_type(datajourney, fun):
    results = datajourney.query(f"""
        SELECT DISTINCT ?type WHERE {{
            ?out dj:{fun} ?in ;
                rdfs:label ?label ;
                ns1:inActivity ?ac .
            ?ac a ?type
        }}
    """)
    
    return [ result['type'] for result in results ]

datajourney = Graph()
datajourney.parse('notebooks/random-forest/djo-graph.ttl', format="turtle")

DJ = Namespace("http://purl.org/dj/")
datajourney.bind("dj", DJ)
DJO = Namespace("http://purl.org/datajourneys/")
datajourney.bind("ns1", DJO)

fno = PrefixMap.bind_namespaces(PipelineGraph())
fno.parse('notebooks/random-forest/fno-graph.ttl', format='turtle')

activities = [ x['ac'] for x in datajourney.query(f"""
                SELECT DISTINCT ?ac WHERE {{
                    ?dn ns1:inActivity ?ac .
                }}""")]

for activity in activities:
    label, activity_type = [ (x['label'], x['type']) for x in datajourney.query(f"""
                                SELECT ?label ?type WHERE {{
                                    <{activity}> a ?type ;
                                        rdfs:label ?label .
                            }}""")][0]
    print(f"{activity} ({label}) --> {activity_type}")