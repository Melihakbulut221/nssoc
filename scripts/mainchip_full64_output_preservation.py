"""Preserve the exact additional route programs and bounded host status.
Original unexpected-file, symlink, capsule and output-byte refusals remain active.
"""
import json
EXACT_TCL={
 "bulk-postdrt-antenna/full-route-before.tcl","bulk-postdrt-antenna/full-route-after.tcl",
 "bulk-postdrt-antenna/route-before-stale-wire-clear.tcl","bulk-postdrt-antenna/route-after-stale-wire-clear.tcl"}
EXACT_DEF={"bulk-postdrt-antenna/original-clock-gate/before.def","bulk-postdrt-antenna/original-clock-gate/after.def"}
MAX_HOST=16*1024**2
def preserve_outputs(base,out,evidence,report):
 f,c=base.f,base.c
 result=dict(copied={},excluded_roots=[],complete=False,owned_outputs_retained=True,retained_output_path=str(out),artifact_required=True)
 report["output_preservation"]=result;before=len(report["terminal_errors"])
 def visit(directory):
  entries=c.attempt(report,"enumerate:"+str(directory.relative_to(out)),lambda:sorted(directory.iterdir()))
  if entries is None:return
  for path in entries:
   relative=path.relative_to(out);name=relative.as_posix()
   def one():
    f.require(not path.is_symlink(),"evidence symlink")
    if path.is_dir():
     if len(relative.parts)==1 and relative.parts[0]in("work","witness","supervision"):
      result["excluded_roots"].append(name);return
     visit(path);return
    f.require(path.is_file()and(base.derived_path(path)or name in EXACT_TCL|EXACT_DEF),"unexpected output")
    pin=f.file_digest(path);published=report.get("native_publication",{}).get("files",{})
    if name in EXACT_DEF:
     f.require(published.get(name)==pin,"clock DEF not permanently preserved")
     result.setdefault("complete_large_outputs_in_native_capsule",{})[name]=pin;return
    if name in EXACT_TCL:
     f.require(pin["bytes"]<=65536 and published.get(name)==pin,"exact route program not permanently preserved")
    host=name=="host-progress.json"
    if host:
     f.require(pin["bytes"]<=MAX_HOST,"host progress exceeds bounded derived limit")
     f.require(isinstance(json.loads(path.read_bytes()),dict),"host progress JSON object")
    if not host and(path.suffix==".lef"or pin["bytes"]>2*1024**2):
     f.require(published.get(name)==pin,"large output not permanently preserved")
     result.setdefault("complete_large_outputs_in_native_capsule",{})[name]=pin;return
    dest=evidence/"native"/relative;dest.parent.mkdir(parents=True,exist_ok=True)
    f.write_new(dest,path.read_bytes());f.require(f.file_digest(dest)==pin,"preserved output bytes")
    result["copied"][name]=pin
   c.attempt(report,"preserve:"+name,one)
 visit(out)
 result["complete"]=len(report["terminal_errors"])==before
 return result
