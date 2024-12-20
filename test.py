import traceback

from semantexe.descriptors import Descriptor
from semantexe.graph import ExecutableGraph
from semantexe.executors.docker import DockerfileExecutor
from semantexe.executors.executeable import Function

DD_DOCKERFILE = "docker_examples/data-driven/Dockerfile"
SIMPLE_DOCKERFILE = "docker_examples/simple/Dockerfile"
PY_FILE = "docker_examples/simple/run.py"

if __name__ == "__main__":
  
  g = ExecutableGraph()
  descriptor = Descriptor()
  fun_uri = descriptor.describe(g, SIMPLE_DOCKERFILE)
  g.serialize("graphs/docker/simple.ttl", format="turtle")
  
  # try to create executable model
  fun = None
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
    executor.pg.serialize("graphs/prov/docker/simple.ttl", format="turtle")