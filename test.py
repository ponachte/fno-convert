import traceback
import json

from semantexe.descriptors import ResourceDescriptor
from semantexe.graph import ExecutableGraph
from semantexe.executors.docker import DockerfileExecutor
from semantexe.executors.executeable import Function
from semantexe.elk import elk_layout

DD_DOCKERFILE = "docker_examples/data-driven/Dockerfile"
DD_PY_FILE = "docker_examples/data-driven/job/run.py"
SIMPLE_DOCKERFILE = "docker_examples/simple/Dockerfile"
SIMPLE_PY_FILE = "docker_examples/simple/run.py"

if __name__ == "__main__":
  # try to describe resource as an FnO Function
  from python_examples.example_functions import binarycount
  g = ExecutableGraph()
  descriptor = ResourceDescriptor(g)
  print("Describing resource...")
  fun_uri = descriptor.describe(binarycount)
  g.serialize("graphs/python/binarycount.ttl", format="turtle")
  print("Done!")
  
  # try to create executable model
  fun = None
  for mapping, imp_uri in g.fun_to_imp(fun_uri):
    try:
      print(f"Found implementation {fun_uri} for {imp_uri}. Trying to create executable model...")
      fun = Function(g, fun_uri, mapping, imp_uri)
    except Exception as e:
      print(f"[ERROR] Error while creating executable model of {fun_uri}")
      print(traceback.format_exc())
  
  # save as a json elk model
  json_elk = {
    "id": "root",
    "layoutOptions": {
      "algorithm": "layered",
      "elk.direction": "RIGHT",
      "edgeRouting": "ORTHOGONAL",
      "hierarchyHandling": "SEPERATE_CHILDREN",
      "elk.spacing.edgeNode": 30, 
      "elk.spacing.nodeNode": 10,
      "elk.layered.feedbackEdges": True
    },
    "children": [fun.json_elk()]
  }
  
  json_elk = elk_layout(json_elk)
  
  if json_elk:
    with open("elk.json", "w") as f:
      json.dump(json_elk, f, indent=2)
  
  # print("Executing FnO Function with DockerfileExecutor...")
  # executor = DockerfileExecutor(g, fun_uri)
  # pg = executor.execute(tag="simple")
  # pg.serialize("graphs/prov/docker/simple.ttl", format="turtle")
  # print("Done!") 