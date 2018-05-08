from typing import Callable, Any, Type
from segments.tmux.git import GitSegment

def requires_segment_info(func: Type[GitSegment]) -> Callable[[Any], Any]: ...
