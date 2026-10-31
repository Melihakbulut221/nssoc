#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Actual current-chip name roundtrip. Disposable test objects; no physical repair."""
import json,os,sys
from pathlib import Path
sys.path.insert(0,"/work/tail-source/scripts")
import mainchip_bulk_postdrt_antenna as p
import mainchip_bulk_postdrt_antenna_native as n
import mainchip_fixed_engine_route_tail_contract as c
from mainchip_witness_engine_build import fingerprint

def fixture_tcl(source,environment,original,work,case):
    p.require(case in("success","primary_error"),"fixed namespace qualification case")
    prefix=n.setting_prefix(source,environment,original)
    rendered=n.repair_tcl(source,environment,original,work)
    p.require(rendered.startswith(prefix)and rendered.count("repair_antennas sg13g2_antennanp")==1
      and "detailed_route "not in rendered,"exact production renderer")
    body=rendered[len(prefix):]
    before=r'''
set block [ord::get_db_block]
set first [$block findInst ANTENNA_1]
set second [$block findInst ANTENNA_2]
if {$first eq "NULL" || $second eq "NULL"} {error "current originals absent"}
if {[$first rename ANTENNA_2]} {error "native duplicate rename unexpectedly accepted"}
if {[$first getName] ne "ANTENNA_1" || [$second getName] ne "ANTENNA_2"} {error "native refusal changed original names"}
set fixture_instances {}
set fixture_callback_calls 0
set actual_physical_repair_calls 0
# Remove the genuine public command in this disposable process. Its replacement
# creates three unconnected test instances and never calls the repair engine.
rename repair_antennas {}
proc repair_antennas {args} {
  global block fixture_instances fixture_callback_calls expect_primary
  incr fixture_callback_calls
  if {$args ne {sg13g2_antennanp -iterations 1 -ratio_margin 10 -diode_only}} {error "changed production repair argv"}
  foreach inst [$block getInsts] {
    if {[regexp {^ANTENNA_[1-9][0-9]*$} [$inst getName]]} {error "original canonical name was not isolated"}
  }
  set template [$block findInst NSSOC_BULK_OLD_ANTENNA_1573]
  if {$template eq "NULL"} {error "isolated native template missing"}
  set master [$template getMaster]
  if {[$master getName] ne "sg13g2_antennanp"} {error "native diode master changed"}
  for {set index 1} {$index <= 3} {incr index} {
    set inst [odb::dbInst_create $block $master "ANTENNA_$index"]
    if {$inst eq "NULL"} {error "disposable test diode creation failed"}
    lappend fixture_instances $inst
    $inst setPlacementStatus PLACED
  }
  # Also exercise the production placement restoration against actual API.
  $template setPlacementStatus FIRM
  if {$expect_primary} {error NSSOC_EXPECTED_NAMESPACE_PRIMARY}
  return 3
}
'''
    before+="set expect_primary "+str(int(case=="primary_error"))+"\n"
    text=prefix+before+"\nset fixture_code [catch {\n"+body+"\n} fixture_result fixture_options]\n"
    text+=r'''
set qualification_errors {}
if {$fixture_callback_calls != 1} {lappend qualification_errors "fixture callback count"}
if {$actual_physical_repair_calls != 0} {lappend qualification_errors "physical repair invoked"}
if {$expect_primary} {
  if {$fixture_code != 1 || $fixture_result ne "NSSOC_EXPECTED_NAMESPACE_PRIMARY"} {
    lappend qualification_errors "expected primary error not preserved"
  }
} elseif {$fixture_code != 0} {
  lappend qualification_errors "unexpected renderer error: $fixture_result"
}
if {[llength $quarantined_names] != 9143 || [llength $new_name_changes] != 3 ||
    [dict size $original_names] != 153129 || [llength $cleanup_errors] != 0} {
  lappend qualification_errors "incomplete production name restoration: $cleanup_errors"
}
foreach inst $fixture_instances {
  if {[catch {
    if {![regexp {^NSSOC_BULK_NEW_ANTENNA_[1-3]$} [$inst getName]]} {
      error "new test diode name not restored"
    }
    foreach iterm [$inst getITerms] {
      if {[$iterm getNet] ne "NULL"} {error "disposable fixture unexpectedly connected"}
    }
    odb::dbInst_destroy $inst
  } error]} {lappend qualification_errors $error}
}
if {[llength [$block getInsts]] != 153129} {lappend qualification_errors "remaining test objects"}
foreach inst [$block getInsts] {
  set name [$inst getName]
  if {[string first NSSOC_BULK_OLD_ $name] == 0 || [string first NSSOC_BULK_NEW_ $name] == 0} {
    lappend qualification_errors "reserved fixture name remains"
  }
}
'''
    for cmd,name in(("write_def","namespace-"+case+"-roundtrip.def"),("write_db","namespace-"+case+"-roundtrip.odb")):
        text+="if {[catch {"+cmd+" "+n.q(work/name)+"} error]} {lappend qualification_errors $error}\n"
    text+='puts "NSSOC_NAMESPACE_FIXTURE_RESULT '+case+' $fixture_code $fixture_result"\n'
    text+='puts "NSSOC_NAMESPACE_FIXTURE_ERRORS $qualification_errors"\n'
    text+='if {[llength $qualification_errors]} {error "native namespace qualification failed: $qualification_errors"}\n'
    text+="set receipt [open "+n.q(work/("namespace-"+case+"-native.json"))+" w]\n"
    text+='puts $receipt [format {{\"case\":\"'+case+'\",\"status\":\"PASS_NATIVE_NAME_ROUNDTRIP_ONLY\",\"original_instances\":153129,\"quarantined_originals\":9143,\"disposable_created\":3,\"disposable_destroyed\":3,\"original_duplicate_rename_refused\":true,\"fixture_callback_calls\":%d,\"expected_primary\":%d,\"observed_renderer_code\":%d,\"actual_physical_repair_calls\":0,\"route_calls\":0,\"physical_acceptance\":false,\"timing_accepted\":false,\"full_phy_accepted\":false}} $fixture_callback_calls $expect_primary $fixture_code]\nclose $receipt\n'
    return text

def phase(args):
    if args.phase=="prepare":
        baseline=n.snapshot(args.input,args.work/"namespace-baseline.def")
        p.require(len(baseline["instances"])==153129 and len(baseline["protected"])==1691,"complete current original census")
        raw=p.encode(baseline);(args.out/"namespace-baseline-snapshot.json").write_bytes(raw)
        metadata=dict(snapshot=p.pin(raw),def_pin=fingerprint(args.work/"namespace-baseline.def"),
          original_instances=153129,original_clocks_and_fixed=1691,input=p.INPUT,**p.FLAGS)
        del raw,baseline
        n.save(args.out/"namespace-baseline-metadata.json",metadata)
        for case in("success","primary_error"):
            directory=args.work/case;directory.mkdir()
            (args.work/("namespace-"+case+".tcl")).write_text(
              fixture_tcl(args.input,args.environment,args.original_tcl,directory,case))
        return dict(complete=True,prepared_cases=["success","primary_error"],**p.FLAGS)
    p.require(args.phase in("audit_success","audit_primary_error"),"namespace audit phase")
    case=args.phase.removeprefix("audit_");directory=args.work/case
    receipt=json.loads(c.secure_file(directory,"namespace-"+case+"-native.json").read_bytes())
    p.require(receipt["status"]=="PASS_NATIVE_NAME_ROUNDTRIP_ONLY"and receipt["case"]==case
      and receipt["original_instances"]==153129 and receipt["quarantined_originals"]==9143
      and receipt["disposable_created"]==receipt["disposable_destroyed"]==3
      and receipt["original_duplicate_rename_refused"]is True and receipt["fixture_callback_calls"]==1
      and receipt["actual_physical_repair_calls"]==receipt["route_calls"]==0
      and receipt["expected_primary"]==receipt["observed_renderer_code"]==int(case=="primary_error"),"actual Tcl qualification receipt")
    p.require(all(receipt[k]is False for k in p.FLAGS),"no physical acceptance from fixture")
    expected=json.loads(c.secure_file(args.out,"namespace-baseline-metadata.json").read_bytes())
    p.exact(fingerprint(directory/("namespace-"+case+"-roundtrip.def")),expected["def_pin"],"full actual Tcl DEF roundtrip")
    snapshot=n.snapshot(directory/("namespace-"+case+"-roundtrip.odb"),directory/"namespace-audit.def")
    raw=p.encode(snapshot);(args.out/("namespace-"+case+"-snapshot.json")).write_bytes(raw)
    actual=p.pin(raw);del raw,snapshot
    p.exact(actual,expected["snapshot"],"all original snapshot names, placements, pins, masters, nets, wire operands, material and1691clock records")
    p.exact(fingerprint(directory/"namespace-audit.def"),expected["def_pin"],"full independent reloaded DEF")
    result=dict(status="PASS_ACTUAL_NATIVE_NAMESPACE_ROUNDTRIP",case=case,
      input=p.INPUT,original_instances=153129,original_clocks_and_fixed=1691,
      expected_snapshot=expected["snapshot"],observed_snapshot=actual,def_pin=expected["def_pin"],
      original_duplicate_rename_refused=True,actual_native_rename_API_qualified=True,
      current_chip_name_roundtrip_qualified=True,disposable_fixture_DB_not_candidate=True,
      source_renderer_unchanged=True,actual_physical_repair_calls=0,route_calls=0,receipt=receipt,**p.FLAGS)
    n.save(args.out/("namespace-"+case+"-result.json"),result)
    return result

def main():
    from types import SimpleNamespace
    args=SimpleNamespace(phase=os.environ["NSSOC_NAMESPACE_PHASE"])
    for name in("input","environment","original_tcl","work","out"):
        setattr(args,name,Path(os.environ["NSSOC_BULK_"+name.upper()]))
    p.require(args.phase in("prepare","audit_success","audit_primary_error"),"qualification phase")
    p.require(args.work==Path("/work/out/work/bulk-postdrt-antenna")and
      args.out==Path("/work/out/bulk-postdrt-antenna"),"owned namespace paths")
    p.require(not any(k in os.environ for k in("GH_TOKEN","GITHUB_TOKEN")),"credential-free native")
    p.source_guard();p.exact(fingerprint(args.input),p.INPUT,"immutable input")
    args.out.mkdir(parents=True,exist_ok=True)
    p.run_phase("namespace-"+args.phase,lambda:phase(args),
      lambda:p.exact(fingerprint(args.input),p.INPUT,"current input unchanged"),
      lambda name,value:n.save(args.out/name,value))
if __name__=="__main__":main()
