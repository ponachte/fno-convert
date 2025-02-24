from semantexe.util.python.rewrite import ASTRewriter

DD_DOCKERFILE = "docker_examples/data-driven/Dockerfile"
SIMPLE_DOCKERFILE = "docker_examples/simple/Dockerfile"
PY_FILE = "docker_examples/simple/run.py"

if __name__ == "__main__":
  
  rewriter = ASTRewriter(parse_arg=True)
  
  with open(PY_FILE, 'r') as file:
    source_code = file.read()
  updated, args = rewriter.rewrite(source_code)