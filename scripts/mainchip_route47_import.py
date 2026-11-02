"""Reuse the frozen two-import Tcl program with strictly owned container paths."""
import re
from pathlib import Path
from types import FunctionType

WORK = Path("/work/out/work/bulk-postdrt-antenna")
STEMS = frozenset(("narrow47-fixed", "narrow47-reversed", "narrow47-restored"))

def owned_path(value):
    path = Path(value)
    if path.parent != WORK or path != path.resolve() or not re.fullmatch(r"[A-Za-z0-9_.-]+", path.name):
        raise ValueError("noncanonical or nonowned route47 Tcl path")
    return "{" + str(path) + "}"

def import_program(original, source, patch, out, stem):
    if not isinstance(original, FunctionType) or stem not in STEMS or Path(out) != WORK:
        raise ValueError("exact frozen import and owned output required")
    if Path(source) != WORK / (stem + "-base.odb") or Path(patch) != WORK / (stem + "-patch.def"):
        raise ValueError("exact class-import source and patch required")
    owned_path(source)
    owned_path(patch)
    # Keep the original function bytecode, defaults and closure. Only the path
    # encoder changes; never modify the frozen module or its global namespace.
    namespace = dict(original.__globals__, tcl_path=owned_path)
    adapted = FunctionType(original.__code__, namespace, original.__name__, original.__defaults__, original.__closure__)
    return adapted(source, patch, out, stem)
