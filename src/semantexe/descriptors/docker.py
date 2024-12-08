from dockerfile_parse import DockerfileParser
from rdflib import URIRef

import ast, os

from ..map import PrefixMap
from ..graph import ExecutableGraph
from ..builders.fno import FnOBuilder
from ..builders.docker import DockerBuilder
from ..descriptors.file import DirectoryDescriptor
from ..descriptors import Descriptor
from ..util.std_kg import STD_KG
from ..util.mapping import Mapping, MappingNode

INPUT_IMAGE = PrefixMap.do()["imageInputParam"]
OUTPUT_IMAGE = PrefixMap.do()["imageOutputParam"]

# TODO multiple build stages

class DockerDescriptor:
    
    def __init__(self, g: ExecutableGraph) -> None:
        self.parser = DockerfileParser()
        self.g = g
    
    def from_file(self, path, file_uri):
        
        ### DOCKERFILE ###
        
        DockerBuilder.describe_dockerfile(self.g, file_uri, path)
        
        ### URI ###
        
        comp_uri = URIRef(f"{file_uri}Composition")
        
        self.parser.dockerfile_path = path
        
        self.dir = os.path.dirname(path)
        self.workdir = ''
        
        self.prev_instruction = None
        self.mappings = []
        
        for inst in self.parser.structure:
            self.handle_inst(inst)
        
        FnOBuilder.describe_composition(self.g, comp_uri, self.mappings, represents=file_uri)
        
        # Indicate start
        FnOBuilder.start(self.g, comp_uri, self.start)
            
        return comp_uri
    
    def handle_mapping(self, mapfrom, mapto):
        self.mappings.append(Mapping(mapfrom, mapto))
    
    def handle_order(self, call):
        if self.prev_instruction == None:
            # Instruction is the sart of the composition
            self.start = call
        else:
            # Use the image output is image input
            output = MappingNode().set_function_out(self.prev_instruction, OUTPUT_IMAGE)
            input = MappingNode().set_function_par(call, INPUT_IMAGE)
            self.handle_mapping(output, input)
            # Explicit execution order
            FnOBuilder.link(self.g, self.prev_instruction, "next", call)
        self.prev_instruction = call
    
    def get_call(self, inst):
        inst_uri = PrefixMap.do()[inst]
        if inst not in self.g.f_counter:
            self.g.f_counter[inst] = 1
            self.g += STD_KG[inst_uri]
        else:
            self.g.f_counter[inst] += 1
        
        call_uri = PrefixMap.base()[f"{inst}_{self.g.f_counter[inst]}"]
        FnOBuilder.apply(self.g, call_uri, inst_uri)
        
        return call_uri
    
    def handle_inst(self, inst):
        if inst['instruction'] == 'FROM':
            self.handle_from(inst['value'])
        elif inst['instruction'] == 'ENTRYPOINT':
            self.handle_entrypoint(inst['value'])
        elif inst['instruction'] == 'RUN':
            self.handle_run(inst['value'])
        elif inst['instruction'] == 'COPY':
            self.handle_copy(inst['value'])
        elif inst['instruction'] == 'WORKDIR':
            self.handle_workdir(inst['value'])
    
    def handle_from(self, value):
        inst = 'from'
        call_uri = self.get_call(inst)
        
        # Set input parameter
        image = MappingNode().set_constant(value)
        input = MappingNode().set_function_par(call_uri, INPUT_IMAGE)
        self.handle_mapping(image, input)
        
        self.handle_order(call_uri)
    
    def handle_entrypoint(self, values):
        inst = 'entrypoint'
        call_uri = self.get_call(inst)
        
        # Convert input parameter to list
        values = ast.literal_eval(values)
        
        # Set entrypoint command
        cmd = MappingNode().set_constant(values[0])
        entrypoint_cmd = MappingNode().set_function_par(call_uri, PrefixMap.do()['entrypointInputCommand'])
        self.handle_mapping(cmd, entrypoint_cmd)
        
        # Set entrypoint command parameters
        if len(values) > 1:
            entrypoint_cmd_params = MappingNode().set_function_par(call_uri, PrefixMap.do()['entrypointInputParamList'])
            for i, value in enumerate(values[1:]):
                value = Descriptor.describe(self.g, value, dir=self.dir)
                param = MappingNode().set_constant(value)
                entrypoint_cmd_params.set_strategy("toList", i)
                self.handle_mapping(param, entrypoint_cmd_params)
        
        self.handle_order(call_uri)
    
    def handle_run(self, value):
        inst = 'run'
        call_uri = self.get_call(inst)
        
        # Set run command
        cmd = MappingNode().set_constant(value)
        run_cmd = MappingNode().set_function_par(call_uri, PrefixMap.do()['runInputCommand'])
        self.handle_mapping(cmd, run_cmd)
        
        self.handle_order(call_uri)
    
    def handle_copy(self, value):
        inst = 'copy'
        call_uri = self.get_call(inst)
        
        # Convert input parameter to list
        value = value.split(' ')
        
        # Describe all files inside the src directory
        # TODO Implementation must be in dest_dir
        src_dir = os.path.join(self.dir, value[0])
        DirectoryDescriptor.describe(self.g, src_dir)
        
        # Set src parameter
        src = MappingNode().set_constant(value[0])
        src_input = MappingNode().set_function_par(call_uri, PrefixMap.do()['copySrc'])
        self.handle_mapping(src, src_input)
        
        # Set dest parameter
        dest = MappingNode().set_constant(value[1])
        dest_input = MappingNode().set_function_par(call_uri, PrefixMap.do()['copyDest'])
        self.handle_mapping(dest, dest_input)
        
        self.handle_order(call_uri)
    
    def handle_workdir(self, value):
        inst = 'workdir'
        call_uri = self.get_call(inst)
        
        # Set src parameter
        dir = MappingNode().set_constant(value)
        dir_input = MappingNode().set_function_par(call_uri, PrefixMap.do()['workdirInput'])
        self.handle_mapping(dir, dir_input)
        
        # Set workdir
        self.workdir = '' if value != '.' else value
        
        self.handle_order(call_uri)