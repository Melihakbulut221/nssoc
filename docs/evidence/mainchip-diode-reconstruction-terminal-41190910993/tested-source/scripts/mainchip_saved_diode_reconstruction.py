#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Construct only verified diode rows; original physical admission is unchanged."""
import copy
import mainchip_bulk_postdrt_antenna as p
PINS="docs/evidence/mainchip-bulk-namespace-real-repair-terminal-41172959321/capsule-metadata/candidate-outputs.json"
DIAGNOSIS="docs/evidence/mainchip-saved-repair-audit-terminal-41189662022/readable-records/native/bulk-postdrt-antenna/saved-audit-result.json"
SELECTED={"bulk-postdrt-antenna/baseline-snapshot.json",
 "bulk-postdrt-antenna/insertion-before-pg-snapshot.json",
 "bulk-postdrt-antenna/baseline-antenna-violations.json","bulk-postdrt-inner-result.json"}
PHASES=("saved-plan","original-snapshot","construct","candidate-snapshot","admit")
ORIENTATIONS={"R0","R90","R180","R270","MX","MY","MXR90","MYR90"}

def normalized_diode(row,template,nets,protected):
    p.exact(row["master"],template["master"],"exact saved diode master")
    p.require(row["master"][1]==p.DIODE and row["master_type"]=="CORE_ANTENNACELL","diode type")
    p.require(row["status"]=="PLACED" and row["orientation"]in ORIENTATIONS,"placed diode orientation")
    for key in("origin","location"):
        p.require(isinstance(row[key],list) and len(row[key])==2
          and all(type(x)is int for x in row[key]),"integer diode "+key)
    p.exact(sorted(row["pins"]),sorted(template["pins"]),"exact diode terminal set")
    result=copy.deepcopy(row)
    for terminal,pin in row["pins"].items():
        reference=template["pins"][terminal]
        p.exact({k:pin[k]for k in("sigtype","io")},{k:reference[k]for k in("sigtype","io")},"pin type")
        if terminal=="A":
            p.require(pin["sigtype"]=="SIGNAL"and pin["io"]=="INPUT","A type")
            p.require(pin["net"]in nets and pin["net"]not in protected,"known unprotected signal")
            p.require(nets[pin["net"]]["identity"]["sigtype"]=="SIGNAL","ordinary A signal")
        else:
            p.require(pin["sigtype"]in("POWER","GROUND"),"only template PG pins")
            p.require(reference["net"]in nets and reference["net"]not in protected,"known template PG")
            p.require(nets[reference["net"]]["identity"]["sigtype"]==pin["sigtype"],"PG net type")
            p.require(pin["net"]is None or pin["net"]==reference["net"],"saved wrong PG connection")
            result["pins"][terminal]=copy.deepcopy(reference)
    p.require("A"in result["pins"],"one signal attachment")
    return result

def make_plan(before,after,diagnosis):
    p.same_base(before,after)
    for key in("protected","clock_record_pins","diode_template"):
        p.exact(after[key],before[key],"original saved "+key)
    p.require(len(before["instances"])==153129 and len(before["nets"])==143820
      and len(before["protected"])==1691,"complete actual original census")
    p.require(diagnosis["status"]=="COMPLETE_SAVED_BULK_REPAIR_DIAGNOSIS"
      and diagnosis["original_failed_run"]==41172959321
      and diagnosis["native_observations_reused_from"]==41187928413,"actual diagnosis lineage")
    p.exact(diagnosis["master"],dict(legacy_wrapper_equal_count=0,observed_added_count=1351,
      stable_same_master_count=1351,template_repeated_wrapper_equal=False),"actual native master result")
    p.require(all(diagnosis[k]is False for k in p.FLAGS),"no inherited physical acceptance")
    added=sorted(set(after["instances"])-set(before["instances"]))
    p.require(len(added)==1351 and all(x.startswith("NSSOC_BULK_NEW_ANTENNA_")for x in added),"exact new diode scope")
    rows={name:normalized_diode(after["instances"][name],before["diode_template"],before["nets"],before["protected"])for name in added}
    attachments={row["pins"]["A"]["net"]for row in rows.values()}
    changed={name for name in before["nets"]if before["nets"][name]!=after["nets"][name]}
    p.require(len(attachments)==608 and changed==attachments,"only actual diode-bearing nets changed")
    return dict(schema="saved-diode-reconstruction-plan-v1",rows=rows,
      protected=before["protected"],template=before["diode_template"],attachments=sorted(attachments),
      source_failed_run=41172959321,diagnosis_run=41189662022,
      original_instance_count=153129,original_net_count=143820,
      preserve_all_original_wire_bytes=True,no_candidate_promoted=True,**p.FLAGS)
