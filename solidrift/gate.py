"""Cache only exact immutable coordinate/index tuples, never backend results."""
from functools import lru_cache
from .guard import check_exact as raw_check
@lru_cache(maxsize=256)
def _cached(vertices, faces):
    return raw_check(vertices, faces)
def check_exact(vertices, faces):
    return _cached(tuple(tuple(p) for p in vertices), tuple(tuple(f) for f in faces))
