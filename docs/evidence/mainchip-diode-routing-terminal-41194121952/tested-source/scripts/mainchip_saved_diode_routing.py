#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Scoped native guide overlay and one detailed-route continuation."""
import copy,json,sys
import mainchip_bulk_postdrt_antenna as p
import mainchip_saved_diode_reconstruction as reconstruction
PROOF="docs/evidence/mainchip-diode-reconstruction-terminal-41190910993/"
DONOR_PROOF="docs/evidence/mainchip-bulk-namespace-real-repair-terminal-41172959321/"
CANDIDATE=dict(bytes=213798975,sha256="2675b9465e7e220931b608ecc0aeec4f171355f3b19259024e04c4e0fb079c34")
ARCHIVE=dict(bytes=152057346,sha256="7f56ea96c6ddeff3f1f6bf58e065ecea7f2f9b9ceb20e7fdd088a2058b480e29")
RECONSTRUCTION_SELECTED={
 "bulk-postdrt-inner-result.json","bulk-postdrt-antenna/reconstruction-plan.json",
 "bulk-postdrt-antenna/reconstruction-result.json","bulk-postdrt-antenna/reconstruction-original-admission.json",
 "bulk-postdrt-antenna/reconstruction-original-snapshot.json","bulk-postdrt-antenna/reconstruction-candidate-snapshot.json",
 "work/bulk-postdrt-antenna/reconstruction-original.def","work/bulk-postdrt-antenna/reconstruction-candidate.def",
 "work/bulk-postdrt-antenna/reconstruction.odb"}
DONOR_SELECTED={"work/bulk-postdrt-antenna/insertion-after-shim.odb","bulk-postdrt-antenna/baseline-antenna-violations.json"}
PHASES=("bootstrap","guide-overlay","guide-reload-audit","power-contact-audit","make-overlay","fixed-import","fixed-audit","route",
 "restore-plan","restore-import","restored-audit","final-check","final-audit","verdict")
PREPARATION={"bootstrap","guide-overlay","guide-reload-audit","power-contact-audit","make-overlay","verdict"}

def validate_guide(row):
    p.exact(sorted(row),sorted({"box","layer","via_layer","congested","jumper","connected_to_term","properties"}),"complete guide fields")
    for key in("layer","via_layer"):p.require(isinstance(row[key],str)and bool(row[key]),"native guide layer")
    box=row["box"]
    p.require(isinstance(box,list)and len(box)==4 and all(type(x)is int for x in box)
      and box[0]<=box[2]and box[1]<=box[3],"ordered integer guide rectangle")
    for key in("congested","jumper","connected_to_term"):p.require(type(row[key])is bool,"native guide flag")
    p.exact(row["properties"],[],"unsupported nonempty guide properties")
    return row

def guide_overlay(before,donor,owners,protected):
    p.require(len(owners)==len(set(owners)) and set(owners)<=set(before),"known unique guide owners")
    p.require(not(set(owners)&set(protected)),"no protected guide mutation")
    p.exact(sorted(donor),sorted(owners),"exact donor guide owner set")
    for name,rows in before.items():
        p.require(isinstance(name,str)and bool(name)and isinstance(rows,list),"guide net record")
        for row in rows:validate_guide(row)
    for name,rows in donor.items():
        p.require(isinstance(rows,list)and bool(rows),"nonempty owned donor guides")
        for row in rows:validate_guide(row)
    result=dict(before);result.update(donor)
    changed=sorted(name for name in owners if before[name]!=donor[name])
    return result,dict(owners=sorted(owners),changed_owners=changed,untouched_nets=len(before)-len(owners),
      protected_guide_records_preserved=True,order_and_multiplicity_preserved=True,all_flags_preserved=True,**p.FLAGS)

def validate_saved_native(inner,native_result,host_failure):
    accepted=reconstruction.accept_native_result(inner)
    p.exact(accepted["saved_diode_reconstruction_result"],native_result,"actual saved reconstruction result")
    p.exact(native_result["candidate"],CANDIDATE,"exact admitted candidate")
    p.require(host_failure["status"]=="FAIL_SAVED_DIODE_RECONSTRUCTION_CLOUD_EXPERIMENT"
      and host_failure["error"]["error"]=="KeyError('saved_audit_result')"
      and host_failure["terminal_errors"]==[],"known prior host-only failure retained")
    return dict(native_engine_passed=True,prior_workflow_remains_failure=True,candidate=CANDIDATE,
      reconstruction_run=41190910993,repair_producer_run=41172959321,**p.FLAGS)

def run_phases(actions,restore,preserve,writer):
    """Original exception wins; restoration and preservation remain independent."""
    p.exact(list(actions),list(PHASES),"exact routing phase order")
    states={name:"not_started"for name in PHASES};errors=[];primary=None;cleanup={}
    try:
        for name in PHASES:
            states[name]="started";writer("route-cycle-progress.json",dict(phases=states.copy(),**p.FLAGS))
            try:
                value=actions[name]()
                p.require(isinstance(value,dict)and value.get("complete")is True,"complete phase "+name)
                states[name]="complete"
            except BaseException:
                states[name]="failed";raise
    except BaseException as exc:primary=exc
    finally:
        for name,fn in(("restore-drt-classes",lambda:restore(states)),("preserve-available-output",preserve)):
            try:
                value=fn();p.require(isinstance(value,dict)and value.get("complete")is True,"complete "+name);cleanup[name]=value
            except BaseException as exc:errors.append(dict(operation=name,error=repr(exc)))
        result=dict(phases=states.copy(),cleanup=cleanup,complete=primary is None and not errors,
          primary_error=None if primary is None else repr(primary),terminal_errors=errors.copy(),**p.FLAGS)
        try:writer("route-cycle-terminal.json",result)
        except BaseException as exc:errors.append(dict(operation="terminal-record",error=repr(exc)))
        if primary is not None or errors:
            sys.stderr.write(p.encode(dict(primary_error=None if primary is None else repr(primary),terminal_errors=errors,phases=states)).decode())
    if primary is not None:raise primary
    if errors:raise RuntimeError("routing finalization failed: "+repr(errors))
    return result

def accept_native_result(inner):
    p.require(inner["status"]=="COMPLETE_SAVED_DIODE_ROUTING_ENGINE"and inner["terminal_errors"]==[]
      and inner["native_complete"]is True,"complete actual routing engine")
    p.require(inner["route_cycle"]["complete"]is True and inner["route_cycle"]["terminal_errors"]==[]
      and all(inner["route_cycle"]["phases"][x]=="complete"for x in PHASES),"complete actual routing cycle")
    expected=["bulk-postdrt-version","bulk-postdrt-ldd"]+["bulk-postdrt-route-continuation-"+x if x in PREPARATION else "bulk-postdrt-"+x for x in PHASES]
    p.exact([x["label"]for x in inner["commands"]],expected,"exact real routing commands")
    p.require(all(x["returncode"]==0 for x in inner["commands"]),"all actual routing commands succeeded")
    result=inner["saved_diode_routing_result"]
    p.require(result["status"]=="COMPLETE_SAVED_DIODE_ROUTING_QUALIFICATION"
      and result["bounded_cycle_qualified"]is True and result["current_repair_antennas_calls"]==0
      and result["current_reconstruction_calls"]==0 and result["current_route_calls"]==1
      and result["direct_diode_pg_contact_passed"]is True,"actual routing verdict")
    p.require(all(inner[k]is False and result[k]is False for k in p.FLAGS),"no final acceptance claim")
    pin=result["candidate"]
    p.require(type(pin["bytes"])is int and pin["bytes"]>0 and isinstance(pin["sha256"],str)
      and len(pin["sha256"])==64 and all(x in "0123456789abcdef"for x in pin["sha256"]),"actual candidate identity")
    return dict(saved_diode_routing_complete=True,saved_diode_routing_result=result)
