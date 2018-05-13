from typing import Callable, Any, Type
from powerline.segments import Segment


def requires_segment_info(func: Type[Segment]) -> Callable[[Any], Any]: ...
