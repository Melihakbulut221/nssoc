#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted actual-body microfixture and authentic recovered-case comparison.
No full OpenROAD build, native DB, geometry, routing, or runtime repair qualification.
"""
import argparse,copy,hashlib,json,os,shutil,subprocess,sys,tempfile,traceback
from pathlib import Path
from unittest.mock import patch
import mainchip_fixed_neardrc_repair as p

SUPPORT='#include <algorithm>\n#include <iostream>\n#include <map>\n#include <memory>\n#include <set>\n#include <stdexcept>\n#include <string>\n#include <vector>\nnamespace support {\nvoid check(bool ok, const std::string& message) {\n  if (!ok) throw std::runtime_error(message);\n}\nstruct frNet { bool fixed; bool isFixed() const { return fixed; } };\nstruct drConnFig { int id; explicit drConnFig(int v) : id(v) {} };\nstruct drNet {\n  frNet parent;\n  std::vector<std::unique_ptr<drConnFig>> figs;\n  int clear_calls=0, ripup_calls=0;\n  bool ripup=false;\n  drNet(bool f, int count, int start) : parent{f} {\n    for (int i=0;i<count;++i) figs.emplace_back(std::make_unique<drConnFig>(start+i));\n  }\n  frNet* getFrNet() { return &parent; }\n  auto& getRouteConnFigs() { return figs; }\n  void clearRouteConnFigs() { ++clear_calls; figs.clear(); }\n  void setRipup() { ++ripup_calls; ripup=true; }\n};\nstruct Marker {\n  int layer; std::vector<drNet*> hits;\n  int getLayerNum() const { return layer; }\n};\nstruct Layer { int width; int getWidth() const { return width; } };\nstruct Tech {\n  Layer layer{0};\n  Layer* getLayer(int n) { layer.width=20+4*n;return &layer; }\n};\nstruct RegionQuery {\n  std::map<int,int> removed;\n  void remove(drConnFig* fig) { ++removed[fig->id]; }\n};\nstruct WorkerBase {\n  std::vector<Marker> markers_; Tech tech; RegionQuery query; int queries=0;\n  Tech* getTech() { return &tech; }\n  RegionQuery& getWorkerRegionQuery() { return query; }\n  void getRipUpNetsFromMarker(Marker* m,std::set<drNet*>& nets,int bloat) {\n    check(bloat==2*(20+4*m->layer),"actual width/bloat call differs");\n    ++queries;\n    for(auto* net:m->hits) nets.insert(net);\n  }\n};\n}\nnamespace original {\nusing namespace support;\nstruct FlexDRWorker:WorkerBase { void initRipUpNetsFromMarkers(); };\nORIGINAL_BODY\n}\nnamespace repaired {\nusing namespace support;\nstruct FlexDRWorker:WorkerBase { void initRipUpNetsFromMarkers(); };\nREPAIRED_BODY\n}\nstruct Scenario {\n  std::string name;\n  std::vector<bool> fixed;\n  std::vector<int> counts;\n  std::vector<std::vector<int>> markers;\n};\nstruct Result { int fixed_mutations=0,mutable_mutations=0,removed=0; };\ntemplate<class Worker>\nResult exercise(const Scenario& s,bool guarded) {\n  using namespace support;\n  Worker worker;\n  std::vector<std::unique_ptr<drNet>> nets;\n  std::set<int> touched;\n  for(size_t i=0;i<s.fixed.size();++i)\n    nets.emplace_back(std::make_unique<drNet>(s.fixed[i],s.counts[i],100*int(i)));\n  for(size_t i=0;i<s.markers.size();++i) {\n    Marker marker{int(i+1),{}};\n    for(int j:s.markers[i]) {marker.hits.push_back(nets.at(j).get());touched.insert(j);}\n    worker.markers_.push_back(marker);\n  }\n  worker.initRipUpNetsFromMarkers();\n  check(worker.queries==int(s.markers.size()),"actual marker loop incomplete");\n  std::map<int,int> expected_removals;\n  Result result;\n  for(size_t i=0;i<nets.size();++i) {\n    auto& n=*nets[i];\n    bool mutate=touched.count(int(i)) && (!guarded || !s.fixed[i]);\n    check(n.clear_calls==(mutate?1:0) && n.ripup_calls==(mutate?1:0)\n      && n.ripup==mutate,"clear/ripup preservation or dedup failed");\n    check(n.figs.size()==size_t(mutate?0:s.counts[i]),"route figure preservation failed");\n    if(mutate) {\n      if(s.fixed[i]) ++result.fixed_mutations; else ++result.mutable_mutations;\n      for(int j=0;j<s.counts[i];++j) ++expected_removals[100*int(i)+j];\n    } else {\n      for(size_t j=0;j<n.figs.size();++j)\n        check(n.figs[j]->id==100*int(i)+int(j),"untouched figure identity differs");\n    }\n  }\n  check(worker.query.removed==expected_removals,"region query removal differs");\n  for(auto [id,count]:worker.query.removed) { (void)id;result.removed+=count; }\n  return result;\n}\nint main() {\n  try {\n    std::vector<Scenario> cases{\n      {"fixed_only",{true},{3},{{0}}},\n      {"mixed",{true,false,true},{2,3,1},{{0,1}}},\n      {"multiple_markers",{true,false,false},{2,1,2},{{0,1},{0,2},{2}}},\n      {"dedup",{true,false},{1,2},{{0,0,1,1},{0,1}}},\n      {"mutable_only",{false,false},{3,2},{{0},{1}}},\n      {"routing_empty",{true,false},{0,0},{{0,1},{0,1}}}\n    };\n    for(const auto& scenario:cases) {\n      auto old=exercise<original::FlexDRWorker>(scenario,false);\n      auto now=exercise<repaired::FlexDRWorker>(scenario,true);\n      support::check(now.fixed_mutations==0,"fixed mutation survived");\n      support::check(old.mutable_mutations==now.mutable_mutations,"mutable behavior changed");\n      if(scenario.name!="mutable_only")\n        support::check(old.fixed_mutations>0,"old actual body did not reproduce fixed mutation");\n      std::cout<<"{\\"case\\":\\""<<scenario.name<<"\\",\\"original_fixed_mutations\\":"\n        <<old.fixed_mutations<<",\\"repaired_fixed_mutations\\":"<<now.fixed_mutations\n        <<",\\"mutable_mutations\\":"<<now.mutable_mutations\n        <<",\\"original_removed_figures\\":"<<old.removed\n        <<",\\"repaired_removed_figures\\":"<<now.removed<<"}\\n";\n    }\n    return 0;\n  } catch(const std::exception& e) {std::cerr<<e.what()<<"\\n";return 1;}\n}\n'

def encoded(value):
    return (json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+"\n").encode()

def refuse(label,call,rows):
    try:call()
    except (AssertionError,RuntimeError,ValueError,KeyError)as exc:
        rows.append(dict(name=label,error=type(exc).__name__,message=str(exc)))
    else:raise AssertionError("accepted mutation: "+label)

def change(value,path,replacement):
    result=copy.deepcopy(value);item=result
    for key in path[:-1]:item=item[key]
    old=item[path[-1]]
    assert encoded(old)!=encoded(replacement),"no-op refusal fixture"
    item[path[-1]]=replacement
    return result

def source_controls(out):
    method=p.source_guard()
    raw=p.c.secure_file(p.ROOT,p.SNAPSHOT).read_bytes()
    fixed=p.derive(raw);original=p.original_function(raw);candidate=p.original_function(fixed)
    assert fixed.replace(p.AFTER,p.BEFORE)==raw
    assert candidate.replace(p.AFTER,p.BEFORE)==original
    rows=[]
    for label,bad in (("changed snapshot",raw+b"\n"),("truncated snapshot",raw[:-1]),
      ("duplicate block",raw+p.BEFORE),("already repaired",fixed)):
        refuse(label,lambda bad=bad:p.derive(bad),rows)
    refuse("unprotected function body",lambda:p.original_function(original),rows)
    entry=dict(bytes=len(raw),sha256=p.digest(raw))
    for label,bad in (("proof size",dict(entry,bytes=len(raw)+1)),
      ("proof digest",dict(entry,sha256="0"*64)),("boolean size",dict(entry,bytes=True))):
        refuse(label,lambda bad=bad:p.record_bytes(label,raw,bad),rows)
    # Real guard against a complete protected fixture copy: hardlinks preserve all
    # original bytes; only the fixture method or newly replaced snapshot is changed.
    with tempfile.TemporaryDirectory(prefix="fixed-neardrc-source-",dir=out)as tmp:
        root=Path(tmp)
        for name in set(method["protected"])|{p.METHOD}:
            target=root/name;target.parent.mkdir(parents=True,exist_ok=True)
            os.link(p.c.secure_file(p.ROOT,name),target)
        with patch.object(p,"ROOT",root):
            assert p.source_guard()==method
            disabled=copy.deepcopy(method);disabled["source_controls_authorized"]=False
            target=root/p.METHOD;target.unlink();target.write_bytes(encoded(disabled))
            assert p.source_guard()==disabled
            refuse("disabled source execution",p.source_context,rows)
            enabled=copy.deepcopy(method);enabled["source_controls_authorized"]=True
            target=root/p.METHOD;target.unlink();target.write_bytes(encoded(enabled))
            assert p.source_context()==enabled
            for flag in p.FALSE:
                bad=copy.deepcopy(method);bad[flag]=True
                target=root/p.METHOD;target.unlink();target.write_bytes(encoded(bad))
                refuse("authority "+flag,p.source_guard,rows)
            for flag in ("source_controls_authorized",p.FALSE[0]):
                bad=copy.deepcopy(method);bad[flag]=1
                target=root/p.METHOD;target.unlink();target.write_bytes(encoded(bad))
                refuse("typed authority "+flag,p.source_guard,rows)
            target=root/p.METHOD;target.unlink();target.write_bytes(encoded(method))
            target=root/p.SNAPSHOT;target.unlink();target.write_bytes(raw+b"\n")
            refuse("real source hash corruption",p.source_guard,rows)
    report=dict(status="PASS_EXACT_SOURCE_REPAIR_CONTROLS",original_sha256=p.digest(raw),
      repaired_sha256=p.digest(fixed),original_function=dict(bytes=len(original),sha256=p.digest(original)),
      repaired_function=dict(bytes=len(candidate),sha256=p.digest(candidate)),
      reverse_byte_exact=True,refusals=rows,full_engine_build=False)
    (out/"source-controls.json").write_bytes(encoded(report))
    return report,original,candidate

def run_command(out,label,argv,timeout):
    try:
        completed=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout,check=False)
    except subprocess.TimeoutExpired as exc:
        stdout=exc.stdout or b"";stderr=exc.stderr or b""
        (out/(label+".stdout")).write_bytes(stdout)
        (out/(label+".stderr")).write_bytes(stderr)
        (out/(label+".command.json")).write_bytes(encoded(dict(argv=argv,timeout_seconds=timeout,
          timed_out=True,returncode=None,stdout=dict(bytes=len(stdout),sha256=p.digest(stdout)),
          stderr=dict(bytes=len(stderr),sha256=p.digest(stderr)))))
        raise
    (out/(label+".stdout")).write_bytes(completed.stdout)
    (out/(label+".stderr")).write_bytes(completed.stderr)
    record=dict(argv=argv,returncode=completed.returncode,timeout_seconds=timeout,timed_out=False,
      stdout=dict(bytes=len(completed.stdout),sha256=p.digest(completed.stdout)),
      stderr=dict(bytes=len(completed.stderr),sha256=p.digest(completed.stderr)))
    (out/(label+".command.json")).write_bytes(encoded(record))
    assert completed.returncode==0,(label,record)
    return completed

def compiled_controls(out,original,candidate):
    # Synthetic collaborators are explicit. The function bodies between them are
    # extracted intact from the exact protected original and single-block derivative.
    text=SUPPORT.replace("ORIGINAL_BODY",original.decode()).replace("REPAIRED_BODY",candidate.decode())
    assert text.count(original.decode())==1 and text.count(candidate.decode())==1
    cpp=out/"actual-function-harness.cpp";cpp.write_text(text,encoding="utf-8")
    compiler=shutil.which("g++");assert compiler,"hosted g++ is required"
    version=run_command(out,"compiler-version",[compiler,"--version"],30)
    exe=out/"actual-function-harness"
    compile_result=run_command(out,"compile",[compiler,"-std=c++20","-O2","-Wall","-Wextra","-Werror",
      str(cpp),"-o",str(exe)],120)
    result=run_command(out,"harness",[str(exe)],30)
    cases=[json.loads(line)for line in result.stdout.splitlines()]
    assert [r["case"]for r in cases]==["fixed_only","mixed","multiple_markers","dedup","mutable_only","routing_empty"]
    assert all(r["repaired_fixed_mutations"]==0 for r in cases)
    assert all(r["original_fixed_mutations"]>0 for r in cases if r["case"]!="mutable_only")
    report=dict(status="PASS_ACTUAL_CPP_BODY_SYNTHETIC_API_CONTROLS",cases=cases,
      original_fixed_mutation_reproduced=True,synthetic_collaborators=True,
      function_bodies_byte_exact=True,harness=dict(bytes=len(cpp.read_bytes()),sha256=p.digest(cpp.read_bytes())),
      compiler=dict(path=compiler,sha256=p.digest(Path(compiler).read_bytes()),version=version.stdout.decode()),
      full_engine_compiled=False,actual_database_loaded=False,routing_qualified=False,
      runtime_root_cause_established=False)
    (out/"compiled-controls.json").write_bytes(encoded(report))
    return report

def comparison_controls(out):
    value=p.read_saved();positive=p.saved_comparison(value);comparison=positive["comparison"]
    assert comparison["status"]=="PASS_OBSERVER_OFF_ON_OUTPUT_EQUIVALENCE_ONLY"
    assert comparison["observed_equivalence"]is True
    assert all(positive[k]is False for k in ("physical_acceptance","timing_accepted","full_phy_accepted","runtime_root_cause_established"))
    rows=[]
    paths=[
      ("audit source",["run","head_sha"],p.ROUTE_SOURCE),
      ("audit run",["run","id"],p.ROUTE_RUN),
      ("terminal failure",["run","conclusion"],"failure"),
      ("attempt",["run","run_attempt"],2),
      ("job id",["jobs","jobs",0,"id"],0),
      ("job failed",["jobs","jobs",0,"conclusion"],"failure"),
      ("job step",["jobs","jobs",0,"steps",0,"conclusion"],"failure"),
      ("historical failure erased",["receipt","historical_run_still_failed"],False),
      ("new host restamped",["on","recovery-host-context.json","source"],p.ROUTE_SOURCE),
      ("frozen case restamped",["on","case-result.json","source"],p.AUDIT_SOURCE),
      ("frozen request restamped",["on","frozen-native-request.json","run_id"],p.AUDIT_RUN),
      ("original skipped passed",["on","host-result.json","original_audits_succeeded"],True),
      ("cleanup failed",["on","host-result.json","terminal_errors"],[{"error":"synthetic"}]),
      ("container running",["on","host-result.json","container_terminal","State","Running"],True),
      ("command timeout",["on","case-result.json","commands",0,"requested_timeout_seconds"],1199),
      ("command body failed",["on","case-result.json","commands",0,"returncode"],1),
      ("frozen inventory missing",["on","case-result.json","frozen_input","files"],745),
      ("clock gate",["on","case-result.json","phase_results","drc-audit","original1691_clock_gate_passed"],False),
      ("clock census",["on","case-result.json","phase_results","drc-audit","original_gate","result","clock_or_fixed_nets"],1690),
      ("non-target changed",["on","case-result.json","phase_results","route-audit","routing_delta","other_records_byte_exact"],False),
      ("physical acceptance",["on","host-result.json","physical_acceptance"],True),
      ("wrong release",["on","release.json","id"],0),
      ("wrong tag",["on","tag.json","object","sha"],p.ROUTE_SOURCE),
      ("new outputs restamped",["on","outputs.json","source"],p.ROUTE_SOURCE),
      ("original gate",["on","case-result.json","phase_results","drc-audit","accepted"],True),
      ("wrong ELF",["on","case-result.json","engine","sha256"],"0"*64),
    ]
    for label,path,replacement in paths:
        bad=change(value,path,replacement)
        refuse(label,lambda bad=bad:p.saved_comparison(bad),rows)
    for filename in ("case-result.json","audit-recovery-evidence.tar.gz.part000"):
        idx=next(i for i,a in enumerate(value["on"]["release.json"]["assets"])if a["name"]==filename)
        for field,replacement in (("digest","sha256:"+"0"*64),("size",1)):
            bad=change(value,["on","release.json","assets",idx,field],replacement)
            refuse(filename+" "+field,lambda bad=bad:p.saved_comparison(bad),rows)
    # Direct unchanged comparator predicates, separated from the new provenance gate.
    off=value["off"]["case-result.json"];on=value["on"]["case-result.json"]
    mismatch=[]
    for field in ("geometry_files","complete_drc"):
        bad=copy.deepcopy(on)
        if field=="geometry_files":
            name=sorted(bad[field])[0];bad[field][name]["sha256"]="0"*64
        else:bad[field]["marker_count"]+=1
        assert encoded(bad)!=encoded(on)
        result=p.c.compare_cases(off,bad)
        assert result["status"]=="FAIL_OBSERVER_OFF_ON_OUTPUT_EQUIVALENCE"
        assert result["observed_equivalence"]is False
        mismatch.append(dict(field=field,result=result))
    report=dict(status="PASS_AUTHENTIC_RECOVERED_CASE_COMPARISON_CONTROLS",
      actual_comparison=positive,refusals=rows,mismatch_refusals=mismatch,
      original_reports_unmodified=True,no_new_routing=True)
    (out/"comparison-controls.json").write_bytes(encoded(report))
    return report

def main():
    parser=argparse.ArgumentParser();parser.add_argument("--output",type=Path,required=True);args=parser.parse_args()
    p.source_context()
    out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    report=dict(status="RUNNING",physical_acceptance=False,timing_accepted=False,full_phy_accepted=False,
      runtime_root_cause_established=False,new_native_execution=False,
      current_source=os.environ["GITHUB_SHA"],current_run=int(os.environ["GITHUB_RUN_ID"]),current_attempt=1)
    primary=None
    try:
        source,old,new=source_controls(out);report["source"]=source
        report["compiled"]=compiled_controls(out,old,new)
        report["comparison"]=comparison_controls(out)
        report["status"]="PASS_FIXED_NEARDRC_SOURCE_CONTROLS"
    except BaseException as exc:
        primary=exc;report.update(status="FAIL_FIXED_NEARDRC_SOURCE_CONTROLS",error=repr(exc),traceback=traceback.format_exc())
    finally:
        try:
            raw=encoded(report);target=out/"result.json";temporary=out/"result.json.tmp"
            temporary.write_bytes(raw);os.replace(temporary,target)
        except BaseException as save:
            if primary is None:primary=save
            try:print(json.dumps(dict(unsaved_result=report,save_error=repr(save)),allow_nan=False),flush=True)
            except BaseException:pass
    if primary is not None:raise primary
    print(json.dumps(dict(status=report["status"],cases=len(report["compiled"]["cases"]),
      source_refusals=len(report["source"]["refusals"]),comparison_refusals=len(report["comparison"]["refusals"]),
      mismatch_refusals=len(report["comparison"]["mismatch_refusals"])),sort_keys=True))

if __name__=="__main__":main()
