#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Explicit container-path Tcl renderer for the unchanged, pinned native phases."""
import os
from pathlib import Path
import mainchip_fixed_engine_route_prefix_contract as c
ROOTS=(Path("/work/out/work"),Path("/work/routing-inputs/global"))
def canonical_tcl_path(value):
    p=Path(value)
    c.require(p.is_absolute() and ".." not in p.parts,"absolute canonical Tcl path")
    c.require(p==p.resolve() and not any(q.is_symlink()for q in (p,*p.parents)),"Tcl path alias")
    c.require(any(p==root or root in p.parents for root in ROOTS),"unapproved native Tcl root")
    c.require(all(ch not in str(p)for ch in "{}\n\r\\"),"unsafe Tcl path character")
    return "{"+str(p)+"}"
def execute_native(native):
    original=native.n.tcl_path
    native.n.tcl_path=canonical_tcl_path
    try:
        return native.main()
    finally:
        native.n.tcl_path=original
def main():
    c.require(c.method(Path("/work/source"))["native_prefix_authorized"]is True,"prefix authorization")
    c.require(os.environ.get("NSSOC_TWO_SIGNAL_PHASE")in c.PASS_STATUSES,"only native prefix phases")
    c.require(os.environ.get("NSSOC_TWO_SIGNAL_OUT")==c.CANONICAL_OUT,"canonical native output")
    c.require(not any(k in os.environ for k in ("GH_TOKEN","GITHUB_TOKEN","NNSOC_DRT_INTERNAL_WITNESS_DIR")),"native environment scope")
    import mainchip_two_signal_repair_native as native
    c.require(Path(native.__file__).resolve()==Path("/work/source/scripts/mainchip_two_signal_repair_native.py")
        and Path(native.n.__file__).resolve()==Path("/work/source/scripts/mainchip_original_clock_restoration_native.py"),"original native module identity")
    return execute_native(native)
if __name__=="__main__":main()
