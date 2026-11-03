"""Require the actual successful full-chip qualification before new-engine routing."""
import json
from pathlib import Path
from mainchip_guide_engine_acquisition import need
SELECTED=("bulk-postdrt-snapshot-inner-result.json","bulk-postdrt-antenna/guide-engine-result.json",
 "bulk-postdrt-antenna/guide-engine-roundtrip.json","bulk-postdrt-guide-engine-acquisition.json","bulk-postdrt-runtime-observed.json")
PRODUCER=dict(run=41695305770,source="5518d9fa75b505848e2c6a5c7d1b4a0ca9c011af",
 release=433078096,tag="cloud-results-41695305770-1-mainchip-bulk-postdrt-antenna",attempt=1)
BINARY=dict(bytes=108948904,sha256="e12b1c70296c119c31ed5b1a7f739904d06b3c86cd703eebee25dbcc9c357431")
def validate(config,built,inner,result,acquisition,runtime):
 need(config["schema"]=="mainchip-guide-engine-actual-chip-qualification-v1"and config["producer"]==PRODUCER,"actual successful qualification provenance")
 need(tuple(config["selected"])==SELECTED,"complete selected qualification evidence")
 need(config["engine"]==built["binary"]==BINARY,"exact qualified engine binary")
 need(config["native_chip_roundtrip_qualified"]is True and config["native_routing_qualified"]is False and config["routing_memory_reduction_measured"]is False,"no prior routing claim")
 need(inner["status"]=="PASS_GUIDE_ENGINE_ACTUAL_CHIP_QUALIFICATION"and not inner["terminal_errors"],"actual native terminal success")
 need(inner["guide_engine_observation_complete"]is True and inner["snapshot_reload_qualified"]is True,"actual chip observations complete")
 need(inner["current_audit_calls"]==3 and all(inner[k]==0 for k in("current_route_calls","current_repair_calls","current_reconstruction_calls","current_class_import_phases")),"no-route qualification scope")
 need([(p["phase"],p["status"])for p in inner["phases"]]==[("roundtrip","complete"),("final-check","complete"),("measure","complete")],"all actual phases complete")
 labels=["bulk-postdrt-version","bulk-postdrt-ldd","guide-engine-roundtrip","guide-engine-full-drc-antenna","guide-engine-measure"]
 need([c["label"]for c in inner["commands"]]==labels and all(c["returncode"]==0 for c in inner["commands"]),"all actual native commands successful")
 need(inner["guide_engine_result"]==result==config["expected_result"],"entire actual measured result binding")
 need(result["status"]=="PASS_ACTUAL_CHIP_ENGINE_ROUNDTRIP_AND_FULL_CHECKS"and result["native_chip_roundtrip_qualified"]is True,"actual result qualification")
 scope=config["reference_scope"]
 need(scope["nets"]==143820 and scope["instances"]==154480 and scope["protected_clock_records"]==1691,"complete original scope")
 need(result["snapshot"]==result["roundtrip"]["before"]==result["roundtrip"]["after"]==scope,"whole snapshot/DEF equality before after checks")
 need(result["roundtrip"]["candidate"]==result["roundtrip"]["rewritten"]==config["reference_odb"],"actual ODB byte equality")
 need(result["drc"]["marker_count"]==92 and result["antenna"]["net_count"]==21 and len(result["antenna"]["violations"])==27,"unchanged measured full DRT and antenna, not signoff")
 need(runtime==built["runtime_dependencies"]and len(runtime)==104,"all actual dependency fingerprints")
 need(acquisition["producer"]==built["producer"]and acquisition["selected"]["openroad"]==BINARY and acquisition["complete_archive_authenticated"]is True,"actual engine archive binding")
 for report in(config,inner,result,result["roundtrip"]):
  need(all(report[k]is False for k in("physical_acceptance","timing_accepted","full_phy_accepted")),"no premature physical timing or PHY acceptance")
 for name in("cgroup_initial","cgroup_terminal"):
  g=inner[name]
  need(g["memory.max"]=="12884901888"and g["memory.swap.max"]=="0"and g["pids.max"]=="4096"and g["cpu.max"]=="200000 100000","actual fixed resource policy")
  events=dict(x.split()for x in g["memory.events"].splitlines())
  need(all(events[k]=="0"for k in("oom","oom_kill","oom_group_kill")),"no native OOM")
 return dict(status="PASS_BOUND_ACTUAL_CHIP_QUALIFICATION_FOR_ROUTE_EXPERIMENT",producer=PRODUCER,binary=BINARY,
  nets=143820,instances=154480,protected_clocks=1691,physical_acceptance=False,timing_accepted=False,full_phy_accepted=False)
def load_and_validate(root,config,built):
 root=Path(root)
 read=lambda name:json.loads((root/name).read_bytes())
 inner=read(SELECTED[0]);result=read(SELECTED[1])
 need(read(SELECTED[2])==result["roundtrip"],"independent roundtrip record")
 return validate(config,built,inner,result,read(SELECTED[3]),read(SELECTED[4]))
