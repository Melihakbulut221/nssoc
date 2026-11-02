"""Actual-capture qualification refusals and unchanged original full64 execution."""
import ast,copy,json
from pathlib import Path
from mainchip_guide_route_qualification import validate,need
ROOT=Path(__file__).resolve().parents[1]
def read(name):return json.loads((ROOT/name).read_bytes())
config=read("scripts/mainchip-guide-engine-qualified-inputs.json")
built=read("scripts/mainchip-guide-engine-built-inputs.json")
fixture=read("docs/evidence/mainchip-guide-engine-qualification-fixture.json")
def check(c=config,b=built,f=fixture):
 return validate(c,b,f["inner"],f["result"],f["engine_acquisition"],f["runtime"])
proof=check()
need(fixture["host"]["native_result"]==fixture["inner"]and not fixture["host"]["terminal_errors"]and fixture["host"]["output_preservation"]["complete"],"actual captured host success")
changes=[
 ("wrong_producer",lambda c,b,f:c["producer"].update(run=1)),
 ("wrong_engine",lambda c,b,f:b["binary"].update(sha256="0"*64)),
 ("incomplete_result",lambda c,b,f:f["inner"].update(status="IN_PROGRESS")),
 ("terminal_error",lambda c,b,f:f["inner"]["terminal_errors"].append({"error":"injected"})),
 ("route_called",lambda c,b,f:f["inner"].update(current_route_calls=1)),
 ("repair_called",lambda c,b,f:f["inner"].update(current_repair_calls=1)),
 ("missing_phase",lambda c,b,f:f["inner"]["phases"].pop()),
 ("failed_phase",lambda c,b,f:f["inner"]["phases"][0].update(status="failed")),
 ("failed_command",lambda c,b,f:f["inner"]["commands"][2].update(returncode=1)),
 ("changed_net_census",lambda c,b,f:f["result"]["snapshot"].update(nets=143819)),
 ("changed_clock_census",lambda c,b,f:f["result"]["snapshot"].update(protected_clock_records=1690)),
 ("changed_snapshot",lambda c,b,f:f["result"]["snapshot"]["snapshot"].update(sha256="0"*64)),
 ("changed_DEF",lambda c,b,f:f["result"]["snapshot"]["DEF"].update(sha256="0"*64)),
 ("changed_ODB",lambda c,b,f:f["result"]["roundtrip"]["rewritten"].update(sha256="0"*64)),
 ("changed_DRC",lambda c,b,f:f["result"]["drc"].update(marker_count=0)),
 ("changed_antenna",lambda c,b,f:f["result"]["antenna"].update(net_count=0)),
 ("missing_runtime",lambda c,b,f:f["runtime"].pop(next(iter(f["runtime"])))),
 ("wrong_engine_acquisition",lambda c,b,f:f["engine_acquisition"]["selected"]["openroad"].update(sha256="0"*64)),
 ("unverified_archive",lambda c,b,f:f["engine_acquisition"].update(complete_archive_authenticated=False)),
 ("claimed_signoff",lambda c,b,f:c.update(physical_acceptance=True)),
 ("resource_policy",lambda c,b,f:f["inner"]["cgroup_terminal"].update(**{"memory.max":"0"})),
 ("native_OOM",lambda c,b,f:f["inner"]["cgroup_terminal"].update(**{"memory.events":"oom 1\noom_kill 1\noom_group_kill 0"})),
]
refused=[]
for name,mutate in changes:
 c,b,f=map(copy.deepcopy,(config,built,fixture));mutate(c,b,f)
 try:check(c,b,f)
 except ValueError:refused.append(name)
 else:raise AssertionError("accepted broken actual qualification: "+name)
need(len(refused)==22,"all actual-capture qualification refusals")
def source(n):return(ROOT/"scripts"/n).read_text()
def fn(s,n):return next(x for x in ast.parse(s).body if isinstance(x,ast.FunctionDef)and x.name==n)
old=source("mainchip_snapshot_reload_inner.py");new=source("mainchip_guide_full64_inner.py")
need(ast.dump(fn(old,"execute"),include_attributes=False)==ast.dump(fn(new,"execute"),include_attributes=False),"all actual original phase bodies and router invocation unchanged")
def phases(s):
 return ast.literal_eval(next(n.value for n in ast.parse(s).body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=="PHASES"for t in n.targets)))
need(phases(old)==phases(new)==("prepare","freeze-import","freeze-audit","reverse-import","reverse-audit-clear","route","route-restore","restore-import","route-audit","final-check","measure"),"original complete route phase schedule")
for name in("usage","resources","runtime","terminal"):
 def nested(s):return next(x for x in ast.walk(fn(s,"main"))if isinstance(x,ast.FunctionDef)and x.name==name)
 need(ast.dump(nested(old),include_attributes=False)==ast.dump(nested(new),include_attributes=False),"original native resource/runtime function "+name)
oldh=source("cloud_mainchip_snapshot_reload.py");newh=source("cloud_mainchip_guide_full64_route.py")
for name in("sha","fp","api","write","own_sources","acquire_snapshot"):
 need(ast.dump(fn(oldh,name),include_attributes=False)==ast.dump(fn(newh,name),include_attributes=False),"unchanged original host operation "+name)
for fragment in('ENGINE="/work/guide-engine/openroad"','fingerprint(Path(ORIGINAL_ENGINE))==c.ENGINE',
 'qualification.load_and_validate("/work/guide-qualification",QUALIFIED,CONFIG)',
 "base.stop_supervision(report,sup,beat)","base.supervised_run(rep,label,argv,seconds,sup)"):
 need(fragment in new,"explicit engine and original lifecycle binding")
need("c.ENGINE="not in new and "base.ENGINE="not in new,"original immutable engine contract retained")
out=ROOT/"guide-full64-controls";out.mkdir()
(out/"result.json").write_text(json.dumps(dict(status="PASS_ACTUAL_QUALIFICATION_BOUND_FULL64_SOURCE_CONTROLS",
 actual_captured_qualification=proof,qualification_refusals=refused,original11_phase_bodies_unchanged=True,
 source_controls_only=True,native_executed=False,physical_acceptance=False,timing_accepted=False,full_phy_accepted=False),sort_keys=True,indent=2)+"\n")
print("PASS actual-chip qualification binding,22 refusals,original11 phase bodies and full64 execution preserved")
