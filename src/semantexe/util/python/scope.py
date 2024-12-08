from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple, Optional


@dataclass
class ScopeState:
    scope: Optional[Any] = None
    path: Optional[str] = None
    block: Optional[Any] = None
    start: Optional[Any] = None
    assigned: Dict = field(default_factory=dict)
    used_by: Dict = field(default_factory=dict)
    default_map: Dict = field(default_factory=dict)
    var_types: Dict = field(default_factory=dict)
    returns: List = field(default_factory=list)
    mappings: List = field(default_factory=list)
    iterators: Dict = field(default_factory=dict)
    conditions: Dict = field(default_factory=dict)
    prev_function: Tuple = (None, None)