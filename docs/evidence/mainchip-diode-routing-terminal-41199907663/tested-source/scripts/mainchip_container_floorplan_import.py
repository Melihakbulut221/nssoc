#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Bind the unchanged floorplan import to this continuation's container paths."""
import os
from pathlib import Path
from types import FunctionType,SimpleNamespace

WORK=Path("/work/out/work/bulk-postdrt-antenna")
DATA=Path("/work/out/bulk-postdrt-antenna")
SCRIPT="/work/tail-source/scripts/mainchip_saved_diode_routing_native.py"
RESTORATION={"restore-plan","failure-restore-plan"}
PAIRS={"fixed":("fixed-base.odb","fixed-patch.def"),
       "candidate":("restore-base.odb","restore-patch.def")}

def clone(fn,**bindings):
    """Copy globals for this call; never patch a frozen module or its function."""
    assert isinstance(fn,FunctionType) and set(bindings)<=set(fn.__globals__)
    copied=FunctionType(fn.__code__,{**fn.__globals__,**bindings},fn.__name__,
                        fn.__defaults__,fn.__closure__)
    copied.__kwdefaults__=fn.__kwdefaults__
    return copied

def owned_path(value):
    raw=str(value)
    assert raw.startswith(str(WORK)+"/"),"outside exact continuation work directory"
    assert not any(c in raw for c in "{}[]$;\n\r\\\x00"),"unsafe Tcl path"
    assert not any(part in (".","..","")for part in raw.split("/")[1:]),"noncanonical path"
    path=Path(raw)
    assert path.parent==WORK and path.resolve()==path,"unowned nested or symlink path"
    return "{"+raw+"}"

def render_import(original,source,patch,out,stem):
    assert stem in PAIRS and Path(out)==WORK,"owned import stage"
    assert (str(source),str(patch))==tuple(str(WORK/name)for name in PAIRS[stem]),"exact stage inputs"
    # The commands, their order and the repeated floorplan import remain original.
    return clone(original,tcl_path=owned_path)(source,patch,out,stem)

def call_native(native,name,work,out,*,failure=False):
    assert name in ("make_overlay","restore_plan"),"only floorplan Tcl producers"
    assert work==WORK and out==DATA and type(failure)is bool,"exact owned outputs"
    assert name=="restore_plan"or failure is False,"failure belongs to restoration"
    fn=getattr(native,name);original=fn.__globals__["n"]
    proxy=SimpleNamespace(**vars(original))
    proxy.import_tcl=lambda source,patch,out,stem:render_import(original.import_tcl,source,patch,out,stem)
    bound=clone(fn,n=proxy)
    return bound(work,out,failure=failure)if name=="restore_plan"else bound(work,out)

def execute_phase(base,report,label,kind,name,seconds,*,runner,script,engine):
    """Keep original terminal/return-code checks for success and failure cleanup."""
    if kind!="native"or name not in RESTORATION:
        return base.execute_phase(report,label,kind,name,seconds,runner=runner)
    assert script==SCRIPT and engine==base.ENGINE,"exact admitted native dispatcher"
    assert base.WORK==WORK and base.DATA==DATA,"exact restoration namespace"
    os.environ["NSSOC_SAVED_DIODE_ROUTE_PHASE"]=name
    def command(command_kind,command_name,work):
        assert (command_kind,command_name,work)==("native",name,WORK),"exact restoration command"
        return [engine,"-no_init","-exit","-python",script]
    return clone(base.execute_phase,phase_command=command)(
        report,label,kind,name,seconds,runner=runner)
