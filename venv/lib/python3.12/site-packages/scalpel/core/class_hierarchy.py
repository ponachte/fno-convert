"""
In this file, we implement  which can be used to describe nominal typing in Python language as specified by  [PEP484](https://peps.python.org/pep-0484/)
Note that Python adopts diamond class inheritance (multiple inheritance).
"""
from _scope_graph import ScopeGraph

def get_class_hierarchy(ast_tree):
    """
    ast_tree:  ast node
    returns:   a dictionary of class names mapping from child to its parent 
    """
    sg = ScopeGraph()
    sg.build(ast_tree)
    return sg.class_hierarchy_map
