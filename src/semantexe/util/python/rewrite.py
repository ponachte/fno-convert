import ast
import textwrap

class ASTRewriter:
    
    def __init__(self, file_path, parse_arg=False):
        try:
            with open(file_path, 'r') as file:
                source_code = file.read()

            # Parse the source code into an AST
            tree = ast.parse(source_code)
            
            # Walk through all the nodes in the AST
            for node in ast.walk(tree):
                # Look for assignments
                if isinstance(node, ast.Assign):
                    # Check if the value being assigned is a call
                    if isinstance(node.value, ast.Call):
                        # Check if the function being called is named "ArgumentParser"
                        func = node.value.func

                        if (
                            isinstance(func, ast.Name) and func.id == "ArgumentParser"
                        ) or (
                            isinstance(func, ast.Attribute) and func.attr == "ArgumentParser"
                        ):
                            # Get the name of the variable being assigned
                            for target in node.targets:
                                if isinstance(target, ast.Name):
                                    return target.id
                
            
        except Exception as e:
            print(f"Error processing file {file_path}: {e}")
            return None
    
    def rewrite_argparse(tree):
        try:
            # Walk through all the nodes in the AST
            for node in ast.walk(tree):
                # Look for assignments
                if isinstance(node, ast.Assign):
                    # Check if the value being assigned is a call
                    if isinstance(node.value, ast.Call):
                        # Check if the function being called is named "ArgumentParser"
                        func = node.value.func

                        if (
                            isinstance(func, ast.Name) and func.id == "ArgumentParser"
                        ) or (
                            isinstance(func, ast.Attribute) and func.attr == "ArgumentParser"
                        ):
                            # Get the name of the variable being assigned
                            for target in node.targets:
                                if isinstance(target, ast.Name):
                                    return target.id
        except SyntaxError:
            return None

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

def find_argparser_variable(source_code):
    """
    Finds the name of the variable holding the argparse.ArgumentParser instance.

    Parameters:
        source_code (str): The source code to analyze.

    Returns:
        str: The name of the variable, or None if not found.
    """
    try:
        # Parse the source code into an Abstract Syntax Tree (AST)
        tree = ast.parse(source_code)

        # Walk through all the nodes in the AST
        for node in ast.walk(tree):
            # Look for assignments
            if isinstance(node, ast.Assign):
                # Check if the value being assigned is a call
                if isinstance(node.value, ast.Call):
                    # Check if the function being called is named "ArgumentParser"
                    func = node.value.func

                    if (
                        isinstance(func, ast.Name) and func.id == "ArgumentParser"
                    ) or (
                        isinstance(func, ast.Attribute) and func.attr == "ArgumentParser"
                    ):
                        # Get the name of the variable being assigned
                        for target in node.targets:
                            if isinstance(target, ast.Name):
                                return target.id
    except SyntaxError:
        return None

    return None