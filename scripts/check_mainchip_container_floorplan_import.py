#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Cloud source controls for exact container imports and restoration dispatch."""
import ast,json,os,tempfile
from pathlib import Path
from types import SimpleNamespace
import mainchip_container_floorplan_import as adapter
ROOT=Path(__file__).resolve().parents[1]

def original_functions(path,names,scope):
    tree=ast.parse((ROOT/path).read_bytes())
    nodes=[node for node in tree.body if isinstance(node,ast.FunctionDef)and node.name in names]
    assert {node.name for node in nodes}==set(names)
    exec(compile(ast.Module(body=nodes,type_ignores=[]),path,"exec"),scope)
    return scope

def run():
    rows=[]
    def ok(name,fn):
        fn();assert name not in rows;rows.append(name)
    def eq(a,b):assert a==b,(a,b)
    def refuse(name,fn):
        def check():
            try:fn()
            except (AssertionError,ValueError,RuntimeError):return
            raise AssertionError("accepted "+name)
        ok(name,check)
    scope=original_functions("scripts/mainchip_original_clock_restoration_native.py",
      {"tcl_path","import_tcl"},{"Path":Path})
    original=scope["import_tcl"];old_path=scope["tcl_path"]
    for stem,(source,patch)in adapter.PAIRS.items():
        def check(stem=stem,source=source,patch=patch):
            host=Path("/home/runner/work/nssoc/nssoc/out/work/bulk-postdrt-antenna")
            expected=original(host/source,host/patch,host,stem).replace(str(host),str(adapter.WORK))
            actual=adapter.render_import(original,adapter.WORK/source,adapter.WORK/patch,adapter.WORK,stem)
            eq(actual,expected);eq(len(actual.splitlines()),6)
            eq(actual.count("read_def -floorplan_initialize "),2)
        ok("container preserves exact original "+stem+" Tcl",check)
    refuse("container leaves original host-only function unchanged",
      lambda:original(adapter.WORK/"fixed-base.odb",adapter.WORK/"fixed-patch.def",adapter.WORK,"fixed"))
    ok("container original function globals unchanged",lambda:eq(scope["tcl_path"],old_path))
    for name,value in (
      ("sibling","/work/out/work/bulk-postdrt-antenna-other/a"),
      ("traversal",str(adapter.WORK)+"/../a"),
      ("nested",str(adapter.WORK)+"/nested/a"),
      ("semicolon",str(adapter.WORK)+"/a;quit"),
      ("newline",str(adapter.WORK)+"/a\nquit"),
      ("brace",str(adapter.WORK)+"/a}"),
      ("substitution",str(adapter.WORK)+"/[quit]"),
      ("backslash",str(adapter.WORK)+"/a\\b")):
        refuse("container rejects "+name,lambda value=value:adapter.owned_path(value))
    refuse("container rejects wrong stage input",lambda:adapter.render_import(original,
      adapter.WORK/"restore-base.odb",adapter.WORK/"fixed-patch.def",adapter.WORK,"fixed"))
    refuse("container rejects unknown stage",lambda:adapter.render_import(original,
      adapter.WORK/"fixed-base.odb",adapter.WORK/"fixed-patch.def",adapter.WORK,"routed"))
    # A scoped proxy must not mutate the original module, including cleanup mode.
    fake_scope={"n":SimpleNamespace(import_tcl=original)}
    exec("def make_overlay(work,out):\n return n.import_tcl(work/'fixed-base.odb',work/'fixed-patch.def',work,'fixed')\ndef restore_plan(work,out,failure=False):\n return (n.import_tcl(work/'restore-base.odb',work/'restore-patch.def',work,'candidate'),failure)\n",fake_scope)
    fake=SimpleNamespace(make_overlay=fake_scope["make_overlay"],restore_plan=fake_scope["restore_plan"])
    original_n=fake_scope["n"]
    for name,failure in (("make_overlay",False),("restore_plan",False),("restore_plan",True)):
        def check(name=name,failure=failure):
            result=adapter.call_native(fake,name,adapter.WORK,adapter.DATA,failure=failure)
            text=result[0]if name=="restore_plan"else result
            assert text.startswith("read_db {"+str(adapter.WORK)+"/")
            if name=="restore_plan":eq(result[1],failure)
            assert fake_scope["n"]is original_n and original_n.import_tcl is original
        ok("container isolated producer "+name+" failure="+str(failure),check)
    refuse("container refuses unrelated native producer",lambda:adapter.call_native(fake,"snapshot",adapter.WORK,adapter.DATA))
    refuse("container refuses wrong output namespace",lambda:adapter.call_native(fake,"make_overlay",adapter.WORK,Path("/work/other")))
    # Execute the original phase function with an observed runner and real JSON files;
    # no OpenROAD/ODB output is fabricated or claimed by these lifecycle controls.
    with tempfile.TemporaryDirectory()as temp:
        root=Path(temp);seen=[]
        def require(value,label):assert value,label
        def pin(raw):return {"bytes":len(raw)}
        c=SimpleNamespace(decode=json.loads,secure_file=lambda base,name:root/name)
        p=SimpleNamespace(require=require,pin=pin,FLAGS={"timing_accepted":False})
        def legacy_command(kind,name,work):return ["legacy",kind,name,str(work)]
        scope2=original_functions("scripts/mainchip_bulk_postdrt_antenna_inner.py",{"execute_phase"},
          {"os":os,"p":p,"c":c,"WORK":adapter.WORK,"DATA":adapter.DATA,"phase_command":legacy_command})
        base=SimpleNamespace(execute_phase=scope2["execute_phase"],ENGINE="/pinned/openroad",
                             WORK=adapter.WORK,DATA=adapter.DATA)
        def invoke(name,complete=True,error=None):
            def runner(report,label,argv,seconds):
                seen.append((argv,seconds))
                (root/(name+"-terminal.json")).write_text(json.dumps(dict(
                  phase=name,complete=complete,error=error,terminal_errors=[],timing_accepted=False)))
            return adapter.execute_phase(base,{},"test","native",name,1200,
                runner=runner,script=adapter.SCRIPT,engine=base.ENGINE)
        for name in sorted(adapter.RESTORATION):
            def check(name=name):
                result=invoke(name)
                eq(result["complete"],True)
                eq(seen[-1],([base.ENGINE,"-no_init","-exit","-python",adapter.SCRIPT],1200))
                eq(os.environ["NSSOC_SAVED_DIODE_ROUTE_PHASE"],name)
            ok("container dispatches original checks for "+name,check)
        refuse("container rejects failed restoration terminal",lambda:invoke("restore-plan",complete=False))
        refuse("container rejects restoration primary error",lambda:invoke("failure-restore-plan",error="failed"))
        ok("container leaves original phase dispatcher unchanged",lambda:eq(scope2["phase_command"],legacy_command))
        def untouched():
            result=invoke("fixed-audit")
            eq(seen[-1][0],["legacy","native","fixed-audit",str(adapter.WORK)])
            eq(result["complete"],True)
        ok("container preserves every unrelated phase command",untouched)
    assert len(rows)==25 and len(set(rows))==25
    return rows
