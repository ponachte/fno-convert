from semantify.descriptors.docker import DockerDescriptor
from semantify.descriptors.python import PythonDescriptor

DD_DOCKERFILE = "/home/ponachte/projects/protego-data-driven-activity-recognition/phone_model/Dockerfile"

if __name__ == "__main__":
  
  descriptor = DockerDescriptor()
  # g, s = descriptor.from_file('examples/for_loop.py')
  g, s = descriptor.from_file(DD_DOCKERFILE)
  print(g.serialize(format='turtle'))
  