import traceback

from semantexe.descriptors import ResourceDescriptor
from semantexe.graph import ExecutableGraph
from semantexe.executors.docker import DockerfileExecutor
from semantexe.executors.executeable import Function

DD_DOCKERFILE = "docker_examples/data-driven/Dockerfile"
DD_PY_FILE = "docker_examples/data-driven/job/run.py"
SIMPLE_DOCKERFILE = "docker_examples/simple/Dockerfile"
SIMPLE_PY_FILE = "docker_examples/simple/run.py"

if __name__ == "__main__":
  
  g = ExecutableGraph()
  descriptor = ResourceDescriptor(g)
  print("Describing resource...")
  fun_uri = descriptor.describe(SIMPLE_DOCKERFILE)
  g.serialize("graphs/docker/simple.ttl", format="turtle")
  print("Done!")
  
  print("Executing FnO Function with DockerfileExecutor...")
  executor = DockerfileExecutor(g, fun_uri)
  pg = executor.execute(tag="simple")
  pg.serialize("graphs/prov/docker/simple.ttl", format="turtle")
  print("Done!")
  
  # try to create executable model
  """fun = None
  for mapping, imp_uri in g.fun_to_imp(fun_uri):
      try:
          print(f"Found implementation {fun_uri} for {imp_uri}. Trying to create executable model...")
          fun = Function(g, fun_uri, mapping, imp_uri)
      except Exception as e:
          print(f"[ERROR] Error while creating executable model of {fun_uri}")
          print(traceback.format_exc())
  if fun:
    print("success! Let's execute...")
    executor = DockerfileExecutor(g, fun)
    executor.execute(tag="simple")
    executor.pg.serialize("graphs/prov/docker/simple.ttl", format="turtle")"""