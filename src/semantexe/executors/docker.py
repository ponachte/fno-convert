import traceback
from ..graph import ExecutableGraph
from ..prefix import Prefix
from ..builders import DockerBuilder, ProvBuilder, FnOBuilder
from ..mappers import FileMapper, DockerMapper
from ..descriptors import FileDescriptor
from .executeable import Function, AppliedFunction

import os, subprocess, docker

from pathlib import Path
from rdflib import URIRef

def docker_build(dirpath, tag):
    
    # Prepare the docker build command
        build_command = ['docker', 'build', '-q', '--provenance=true', '--sbom=true', dirpath]
        
        if tag:
            build_command.extend(['-t', tag])

        try:
            # Run the docker build command and capture the output
            result = subprocess.run(
                build_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
                text=True
            )
            
            # return the image id
            return result.stdout
        
        except subprocess.CalledProcessError as e:
            print(f"Error during Docker build: {e.stderr}")
            raise

class DockerfileExecutor:
    
    def __init__(self, g: ExecutableGraph, fun: Function):
        self.g = g
        self.exe_counter = 0
        self.fun = fun
    
    def execute(self, *args, **kwargs):
        if self.g.is_dockerfile(self.fun.imp):
            self.build(tag=kwargs['tag'])
        # TODO execute other docker implementations
    
    def build(self, tag):
        self.pg = ExecutableGraph()
        
        # Describe execution
        self.exe_counter += 1
        exe = Prefix.base()[f"Execution{self.exe_counter}"]
        ProvBuilder.activity(self.pg, exe)
        
        # Get the Dockerfile metadata
        filepath = self.g.get_file(self.fun.imp)
        self.dir = os.path.dirname(filepath)
        
        # Initiate metadata
        self.workdir = ''
        self.entrypoint_cmd = None
        self.entrypoint_params = []
        
        # Build the image and get its id
        image_id = docker_build(self.dir, tag)
        
        # Start docker client to inspect image
        client = docker.client.from_env()
        image = client.images.get(tag)
        
        # describe the image URI instance
        self.image_uri = DockerMapper.describe_dockerimage(self.pg, image)
        
        # Execute
        self.execute_function(self.fun)
        
        ### PROVENANCE ###
        # Dockerfile execution
        ProvBuilder.entity(self.pg, self.fun.fun_uri)
        ProvBuilder.execution(self.pg, exe, self.fun.fun_uri, self.fun.imp, [], self.image_uri)
        ProvBuilder.derivedFrom(self.pg, self.image_uri, self.fun.imp)
        
        # Default execute provenance
        if self.entrypoint_cmd in ["python", "python3"]:
            # Look for the correct python implementation
            # TODO Look for an implementation with a usable mapping
            try:
                # Now just take the first implementation
                file = os.path.join(self.workdir, self.entrypoint_params[0])
                imp, mapping, fun = self.pg.imp_from_file(file)[0]
                ProvBuilder.alternateOf(self.pg, self.image_uri, imp)
            except IndexError as e:
                print(f"[ERROR] No Python implementation found for {file}")
        
            if len(self.entrypoint_params) > 1:
                default_input = ' '.join(self.entrypoint_params[1:])
                DockerBuilder.defaultInput(self.pg, self.image_uri, default_input)
                
        return self.pg                
    
    def execute_applied(self, fun: AppliedFunction):
        # Dockerfiles do not have control flow
        self.execute_function(fun)
        fun._next = fun.next
    
    def execute_function(self, fun: Function):
        if fun.comp:
            fun.comp.execute(self)
        if fun.fun_uri == Prefix.do()["copy"]:
            self.execute_copy(fun)
        elif fun.fun_uri == Prefix.do()["workdir"]:
            self.execute_workdir(fun)
        elif fun.fun_uri == Prefix.do()["entrypoint"]:
            self.execute_entrypoint(fun)
        elif fun.fun_uri == Prefix.do()["cmd"]:
            self.execute_cmd(fun)

    def execute_copy(self, fun: Function):
        # Describe all files inside the src directory
        src_dir = fun[Prefix.do().copySrc].value.replace('.', self.dir)
        dest_dir = fun[Prefix.do().copyDest].value.replace('.', self.workdir)
        
        dir_path = Path(src_dir)
        # recursively find all files in all subdirectories
        copied_uris = set()
        for file in dir_path.rglob('*'):
            if file.is_file():
                file = str(file)
                # Do not describe the Dockerfile again
                if not file.endswith("Dockerfile"):
                    FileDescriptor.describe(self.pg, file)
                    for uri in [ uri for uri in self.pg.functions() if uri not in copied_uris]:
                        copied_uris.add(uri)
                        # Get the original implementation **Just one imp expected**
                        for mapping, imp in self.pg.fun_to_imp(uri):
                            # Copy the implementation
                            imp_copy = FileMapper.move_file(self.pg, mapping, imp, src_dir, dest_dir)
                            if imp_copy:
                                # Provenance
                                ProvBuilder.alternateOf(self.pg, imp_copy, imp)
                                DockerBuilder.contains(self.pg, self.image_uri, imp_copy)

    def execute_workdir(self, fun: Function):
        # Set workdir
        value = fun[Prefix.do().workdirInput].value
        self.workdir = '' if value == '.' else value
    
    def execute_entrypoint(self, fun: Function):
        self.entrypoint_cmd = fun[Prefix.do().entrypointInputCommand].get()
        self.entrypoint_params = fun[Prefix.do().entrypointInputParamList].to_list()
    
    def execute_cmd(self, fun: Function):
        value = fun[Prefix.do().cmdInputParamList].to_list()
        if self.entrypoint_cmd:
            self.entrypoint_params.extend(value)
        else:
            self.entrypoint_cmd = value[0]
            if len(value) > 1:
                self.entrypoint_params.extend(value[1:])