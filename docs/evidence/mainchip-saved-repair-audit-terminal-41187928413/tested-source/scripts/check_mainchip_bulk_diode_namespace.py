#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted tests of the actual namespace Tcl renderer, with explicit fake DB I/O."""
import json,subprocess
from pathlib import Path
import mainchip_bulk_postdrt_antenna as p
import check_mainchip_bulk_postdrt_antenna as prior

STUB=r'''
rename BLOCK BASE_BLOCK
rename U {}
rename repair_antennas {}
set instances {}
set names {}
set places {}
set next_object 0
set rename_attempts {}
set repair_calls 0
set rename_fault_used 0
set initial_names {}
proc create_instance {name} {
  global instances names places next_object
  foreach object $instances {
    if {[dict get $names $object] eq $name} {error "duplicate dbInst create: $name"}
  }
  set object "OBJECT_[incr next_object]"
  lappend instances $object
  dict set names $object $name
  dict set places $object PLACED
  interp alias {} $object {} instance $object
  return $object
}
proc BLOCK {method args} {
  global instances
  if {$method eq "getInsts"} {return $instances}
  return [BASE_BLOCK $method {*}$args]
}
proc instance {object method args} {
  global instances names places rename_attempts fault rename_fault_used events
  switch -- $method {
    getName {return [dict get $names $object]}
    getPlacementStatus {return [dict get $places $object]}
    setPlacementStatus {
      lappend events "placement:$object:[lindex $args 0]"
      if {$fault eq "placement" && $object eq "OBJECT_1"} {error placement-refused}
      dict set places $object [lindex $args 0]
    }
    rename {
      set old [dict get $names $object];set new [lindex $args 0]
      lappend rename_attempts [list $object $old $new]
      set stage ""
      if {[string first NSSOC_BULK_OLD_ $new] == 0} {set stage isolate}
      if {[string first NSSOC_BULK_NEW_ $new] == 0} {set stage new}
      if {[string first NSSOC_BULK_OLD_ $old] == 0 && [string first ANTENNA_ $new] == 0} {set stage restore}
      if {!$rename_fault_used && ($fault eq "$stage-false" || $fault eq "$stage-throw" || $fault eq "$stage-noop" || $fault eq "$stage-after")} {
        # Fail the second old rename, so the first must still be restored.
        if {$stage ne "isolate" || $object eq "OBJECT_2"} {
          set rename_fault_used 1
          if {$fault eq "$stage-false"} {return 0}
          if {$fault eq "$stage-noop"} {return 1}
          if {$fault eq "$stage-after"} {dict set names $object $new;error rename-after-mutation}
          error rename-before-mutation
        }
      }
      foreach other $instances {
        if {$other ne $object && [dict get $names $other] eq $new} {return 0}
      }
      dict set names $object $new
      return 1
    }
    default {error "unexpected namespace instance method: $method"}
  }
}
proc repair_antennas {args} {
  global names instances places repair_calls fault fail_primary clk events
  incr repair_calls
  if {$args ne {sg13g2_antennanp -iterations 1 -ratio_margin 10 -diode_only}} {error "changed repair argv"}
  if {$clk ne "ROUTED"} {error "metadata not prepared"}
  foreach object $instances {
    if {[regexp {^ANTENNA_[1-9][0-9]*$} [dict get $names $object]]} {error "old canonical diode not isolated"}
    dict set places $object FIRM
  }
  # Exact pinned legacy behavior: skip initial occupied prefix, then increment
  # without checking later names. create_instance rejects real collisions.
  set index 1
  while {[lsearch -exact [dict values $names] "ANTENNA_$index"] >= 0} {incr index}
  for {set n 0} {$n < 3} {incr n} {
    create_instance "ANTENNA_$index"
    incr index
  }
  if {$fault eq "unexpected-new"} {create_instance UNEXPECTED_NEW_INSTANCE}
  lappend events repair
  if {$fail_primary} {error repair-primary}
  return 3
}
foreach name $seed_names {
  set object [create_instance $name]
  dict set initial_names $object $name
}
if {$fault eq "duplicate-preflight"} {
  dict set names OBJECT_2 [dict get $names OBJECT_1]
}
'''

def controls():
    renderer=prior.native_functions()
    work=Path("/work/unit")
    body=renderer["repair_tcl"](work/"input.odb",work/"env.tcl",work/"original.tcl",work)
    p.require(body.count("repair_antennas sg13g2_antennanp")==1 and "detailed_route "not in body,"one production repair only")
    cases=[
      ("gapped-success",None,False,False,False,False),
      ("dense-success",None,False,False,False,False),
      ("no-canonical-success",None,False,False,False,False),
      ("repair-error",None,True,False,False,False),
      ("old-prefix-refusal","reserved-old",False,False,False,False),
      ("new-prefix-refusal","reserved-new",False,False,False,False),
      ("duplicate-refusal","duplicate-preflight",False,False,False,False),
    ]
    for stage in ("isolate","new","restore"):
        for kind in ("false","throw","noop","after"):
            cases.append((stage+"-"+kind,stage+"-"+kind,False,False,False,False))
    cases.extend([
      ("primary-and-restore","restore-false",True,False,False,False),
      ("placement-refusal","placement",False,False,False,False),
      ("metadata-refusal",None,False,True,False,False),
      ("def-refusal",None,False,False,True,False),
      ("db-refusal",None,False,False,False,True),
      ("unexpected-new-refusal","unexpected-new",False,False,False,False),
    ])
    rows=[]
    for label,fault,primary,metadata,fail_def,fail_db in cases:
        seeds=["ANTENNA_1","ANTENNA_3","ANTENNA_4","ANTENNA_01","u[1]/$escaped"]
        if label=="dense-success":seeds[:3]=["ANTENNA_1","ANTENNA_2","ANTENNA_3"]
        if label=="no-canonical-success":seeds=["DATA_1","DATA_2","ANTENNA_01","ANTENNA_0","u[1]/$escaped"]
        if fault=="reserved-old":seeds.append("NSSOC_BULK_OLD_EXISTING")
        if fault=="reserved-new":seeds.append("NSSOC_BULK_NEW_EXISTING")
        header="\n".join("set "+k+" "+str(int(v))for k,v in dict(fail_primary=primary,fail_cleanup=metadata,fail_def=fail_def,fail_db=fail_db).items())+"\n"
        header+="set fault {"+(fault or "")+"}\nset seed_names [list "+" ".join("{"+x+"}"for x in seeds)+"]\n"
        script=header+prior.TCL_STUB+STUB+"\nset rc [catch {\n"+body+"\n} result options]\n"
        script+=r'''
set original_errors {}
dict for {object old} $initial_names {
  if {[dict get $names $object] ne $old} {lappend original_errors [list $object $old [dict get $names $object]]}
}
set new_errors {}
set new_count 0
foreach object $instances {
  if {[dict exists $initial_names $object]} {continue}
  incr new_count
  if {![regexp {^NSSOC_BULK_NEW_ANTENNA_[1-9][0-9]*$} [dict get $names $object]]} {lappend new_errors $object}
}
puts "NS_RC=$rc"
puts "NS_RESULT=$result"
puts "NS_REPAIR_CALLS=$repair_calls"
puts "NS_ORIGINAL_ERRORS=[llength $original_errors]"
puts "NS_NEW_ERRORS=[llength $new_errors]"
puts "NS_NEW_COUNT=$new_count"
puts "NS_METADATA=$clk"
puts "NS_NAMES=$names"
puts "NS_PLACEMENTS=$places"
puts "NS_RENAMES=$rename_attempts"
puts "NS_EVENTS=$events"
puts "NS_CLEANUP_ERRORS=$cleanup_errors"
'''
        run=subprocess.run(["tclsh"],input=script.encode(),stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=10)
        text=run.stdout.decode("utf-8","strict");stderr=run.stderr.decode("utf-8","strict")
        p.require(run.returncode==0 and not stderr,"complete namespace Tcl fixture process: "+label+": "+stderr)
        parsed=dict(line.split("=",1)for line in text.splitlines()if line.startswith("NS_"))
        p.require("NS_CLEANUP_ERRORS"in parsed,"complete namespace result")
        failed=bool(fault or primary or metadata or fail_def or fail_db)
        p.require(parsed["NS_RC"]==str(int(failed)),"namespace outcome: "+label+": "+text)
        before_call=fault in("reserved-old","reserved-new","duplicate-preflight")or(fault or "").startswith("isolate-")
        p.require(parsed["NS_REPAIR_CALLS"]==str(int(not before_call)),"no repair on failed preflight/isolation")
        if primary:p.require(parsed["NS_RESULT"]=="repair-primary","original primary exception survives cleanup")
        p.require("def:/work/unit/insertion-after-shim.def"in parsed["NS_EVENTS"]and "db:/work/unit/insertion-after-shim.odb"in parsed["NS_EVENTS"],"independent output preservation")
        p.require("placement:OBJECT_1:PLACED"in parsed["NS_EVENTS"]and "placement:OBJECT_2:PLACED"in parsed["NS_EVENTS"],"all independent original placement restores")
        if not metadata:p.require(parsed["NS_METADATA"]=="FIXED","original fixed metadata restored")
        # No cleanup failure is hidden as success. Genuine failures may retain
        # partial names, which are preserved and rejected rather than accepted.
        if not fault or fault in("reserved-old","reserved-new","placement","unexpected-new")or(fault or "").startswith("isolate-"):
            p.require(parsed["NS_ORIGINAL_ERRORS"]=="0","all original names restored: "+label)
        if fault=="duplicate-preflight":p.require(parsed["NS_ORIGINAL_ERRORS"]=="1","fixture's original duplicate disclosed")
        if not before_call and (not fault or fault in("placement",)or(fault or "").startswith("restore-")):
            p.require(parsed["NS_NEW_ERRORS"]=="0"and parsed["NS_NEW_COUNT"]=="3","all new canonical names moved out")
        if not failed:
            p.require(not parsed["NS_CLEANUP_ERRORS"],"no successful cleanup errors")
            p.require(parsed["NS_ORIGINAL_ERRORS"]=="0"and parsed["NS_NEW_ERRORS"]=="0","successful namespace roundtrip")
        rows.append(dict(label=label,fault=fault,source_renderer_executed=True,synthetic_OpenDB_API=True,native_CAD_executed=False,
          stdout=text,stderr=stderr,returncode=run.returncode,observations=parsed))
    p.require(len(rows)==25,"complete namespace fixture census")
    return dict(status="PASS_BULK_DIODE_NAMESPACE_SOURCE_CONTROLS",count=len(rows),rows=rows,
      actual_native_rename_API_qualified=False,actual_current_chip_name_roundtrip_qualified=False,**p.FLAGS)
