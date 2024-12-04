import ast
import textwrap

def get_main_source_code(file_path):
    try:
        with open(file_path, 'r') as file:
            source_code = file.read()

        # Parse the source code into an AST
        tree = ast.parse(source_code)
            
        # Look for the `if __name__ == "__main__"` block
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                # Check if the condition matches `__name__ == "__main__"`
                if (
                    isinstance(node.test, ast.Compare) and
                    isinstance(node.test.left, ast.Name) and
                    node.test.left.id == "__name__" and
                    isinstance(node.test.ops[0], ast.Eq) and
                    isinstance(node.test.comparators[0], ast.Constant) and
                    node.test.comparators[0].value == "__main__"
                ):
                    # Get the block of code inside this `if` statement
                    start_lineno = node.body[0].lineno
                    end_lineno = node.body[-1].end_lineno

                    # Extract the lines from the original source code
                    source_lines = source_code.splitlines()
                    source_block = "\n".join(source_lines[start_lineno - 1:end_lineno])
                
                # Remove the indentation of the block using textwrap.dedent
                return textwrap.dedent(source_block)
        return None  # Return None if no block is found
    except Exception as e:
        print(f"Error processing file {file_path}: {e}")
        return None