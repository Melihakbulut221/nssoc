#!/usr/bin/env python3
"""Hosted-only readback of an authentic failed equivalence attempt. No CAD or build."""
import argparse, hashlib, json, os, subprocess
from collections import Counter
from pathlib import Path
import cloud_magic_resistor_provenance_build as b

ROOT=b.ROOT
PREFIX="docs/evidence/cdr-resistor-provenance-build-failure-40973498818/"
SOURCE="15fc053d21ddeafd132ecac7bba3835a3a4d48d3"
RUN=40973498818
RELEASE=428497156
TAG="cloud-results-40973498818-1-cdr-resistor-provenance-build"
VARIANTS={"saved_current":"work/current/mim/precise/wire/rc03",
 "archived":"work/archived/rc03","rebuilt_baseline":"work/rebuilt_baseline/rc03",
 "trace_off":"work/trace_off/rc03","trace_on":"work/trace_on/rc03"}
NAMES=("pump_wires.ext","pump_wires.res.ext","baseline.spice","wires.spice")
TRACE="work/trace_on/resistor-physical-trace.jsonl"
PROOFS=("run.json","jobs.json","release.json","tag-ref.json",
 "assets/publication-inventory.json","assets/direct-publication-plan.json",
 "assets/cdr-resistor-provenance-build-40973498818-1.parts.json","assets/result.json")

def proof(root=ROOT):
    p={name:b.decode(b.frozen.regular(root,PREFIX+name).read_bytes())for name in PROOFS}
    run=p["run.json"]
    b.require(run["id"]==RUN and run["head_sha"]==SOURCE and run["run_attempt"]==1 and
      run["status"]=="completed"and run["conclusion"]=="failure","original failed run")
    expected={"source-controls":(123795793091,"success"),"preserve-source-job-log":(123796000013,"success"),
      "native-build":(123796054208,"failure"),"preserve-terminal-job-logs":(123797942197,"success")}
    jobs=p["jobs.json"]["jobs"]
    b.require({j["name"]:(j["id"],j["conclusion"])for j in jobs}==expected and
      all(j["run_id"]==RUN and j["head_sha"]==SOURCE and j["status"]=="completed"for j in jobs),
      "original complete jobs")
    b.require(p["assets/result.json"]["status"]=="FAIL_MAGIC_BUILD_OR_TRACE_EQUIVALENCE"and
      p["assets/result.json"]["error"]==dict(type="AssertionError",message="native record/order/value mismatch: archived"),
      "original failure not reclassified")
    return p

def live_binding(p,run,jobs,release,ref):
    old=p["run.json"]
    for key in ("id","head_sha","head_branch","event","run_attempt","status","conclusion","workflow_id"):
        b.require(run.get(key)==old[key],"diagnostic producer run: "+key)
    expected={j["id"]:j for j in p["jobs.json"]["jobs"]}
    b.require(len(jobs["jobs"])==len(expected),"diagnostic jobs count")
    for j in jobs["jobs"]:
        b.require(j.get("id")in expected,"diagnostic job id")
        a=expected[j["id"]]
        for key in ("name","run_id","head_sha","status","conclusion"):
            b.require(j.get(key)==a[key],"diagnostic job: "+key)
        b.require([(s["number"],s["name"],s["conclusion"])for s in j["steps"]]==
          [(s["number"],s["name"],s["conclusion"])for s in a["steps"]],"diagnostic exact terminal steps")
    assets=b.frozen.release_binding(release,ref,TAG,SOURCE)
    frozen=b.frozen.release_binding(p["release.json"],p["tag-ref.json"],TAG,SOURCE)
    b.require(release["id"]==RELEASE and set(assets)==set(frozen),"diagnostic release")
    for name,a in assets.items():
        z=frozen[name]
        b.require(all(a.get(k)==z[k]for k in ("id","size","digest")),"diagnostic asset: "+name)
    return {n:dict(id=a["id"],bytes=a["size"],sha256=a["digest"].removeprefix("sha256:"))for n,a in assets.items()}

def records_diagnosis(directories):
    rows={name:b.native_records(path)for name,path in directories.items()}
    b.require(list(rows)==list(VARIANTS),"exact five variants")
    reference=rows["saved_current"];diagnosis={}
    def digest(values):return hashlib.sha256(b"\n".join(values)+b"\n").hexdigest()
    for name,values in rows.items():
        categories={}
        for category,current in values.items():
            original=reference[category]
            mismatches=[i for i in range(max(len(original),len(current)))
              if i>=len(original)or i>=len(current)or original[i]!=current[i]]
            examples=[dict(index=i,reference=original[i].decode("utf-8","backslashreplace")if i<len(original)else None,
              observed=current[i].decode("utf-8","backslashreplace")if i<len(current)else None)for i in mismatches[:5]]
            left=Counter(original);right=Counter(current)
            categories[category]=dict(reference_count=len(original),observed_count=len(current),
              reference_ordered_sha256=digest(original),observed_ordered_sha256=digest(current),
              reference_multiset_sha256=digest(sorted(original)),observed_multiset_sha256=digest(sorted(current)),
              ordered_equal=original==current,multiset_equal=left==right,
              mismatch_count=len(mismatches),first_five_ordered_mismatches=examples,
              reference_only_count=sum((left-right).values()),observed_only_count=sum((right-left).values()),
              reference_only_examples=[dict(row=x.decode("utf-8","backslashreplace"),multiplicity=n)
                for x,n in sorted((left-right).items())[:5]],
              observed_only_examples=[dict(row=x.decode("utf-8","backslashreplace"),multiplicity=n)
                for x,n in sorted((right-left).items())[:5]])
        diagnosis[name]=dict(categories=categories,raw_files={n:b.pin(directories[name]/n)for n in NAMES})
    try:strict=b.compare_outputs(directories)
    except BaseException as exc:strict=dict(accepted=False,error=dict(type=type(exc).__name__,message=str(exc)))
    else:strict=dict(accepted=True,report=strict)
    return dict(status="READ_ONLY_DIFFERENCE_OBSERVATION_NOT_EQUIVALENCE_ACCEPTANCE",
      original_strict_comparator=strict,variants=diagnosis,numerical_normalization_applied=False,
      multiset_is_diagnostic_only=True,**b.FLAGS)

def perform(ctx,reserved,controls_raw,expected,out,root=ROOT,api_call=b.frozen.api,fetch=b.frozen.download):
    _,_,_,admission=b.preflight(ctx,reserved,controls_raw,expected,root,api_call)
    b.write(out/"admission.json",b.encode(admission));b.write(out/"source-controls.json",controls_raw)
    p=proof(root)
    assets=live_binding(p,api_call("actions/runs/"+str(RUN)),
      api_call("actions/runs/"+str(RUN)+"/jobs?per_page=100"),
      api_call("releases/"+str(RELEASE)),api_call("git/ref/tags/"+TAG))
    parts=p["assets/cdr-resistor-provenance-build-40973498818-1.parts.json"]
    inventory=dict(p["assets/publication-inventory.json"])
    for name in ("publication-inventory.json","direct-publication-plan.json"):
        inventory[name]=b.pin(b.frozen.regular(root,PREFIX+"assets/"+name))
    b.require(len(inventory)==14485,"complete failed archive inventory")
    wanted=[prefix+"/"+name for prefix in VARIANTS.values()for name in NAMES]+[TRACE]
    b.require(len(set(wanted))==21 and set(wanted)<=set(inventory),"exact selected diagnostics")
    work=out/"work";work.mkdir()
    archive,transport=b.frozen.acquire(dict(assets=assets),parts,work,fetch)
    b.write(out/"transport.json",b.encode(transport))
    selected=work/"selected"
    census=b.frozen.select_archive(archive,{n:v["sha256"]for n,v in inventory.items()},
      wanted,parts["source_directory"],selected)
    b.require(all(census["full_members"][n]==v for n,v in inventory.items()),"full exact member size/hash")
    b.write(out/"full-census.json",b.encode(census));archive.unlink()
    directories={n:selected/prefix for n,prefix in VARIANTS.items()}
    result=records_diagnosis(directories)
    native=b.native_records(directories["trace_on"])["pump_wires.res.ext:resist"]
    try:trace=b.validate_trace(selected/TRACE,len(native),native)
    except BaseException as exc:trace=dict(accepted=False,error=dict(type=type(exc).__name__,message=str(exc)))
    else:trace=dict(accepted=True,report=trace)
    b.write(out/"difference-diagnosis.json",b.encode(result))
    b.write(out/"trace-observation.json",b.encode(trace))
    b.source_guard(expected,root)
    return dict(status="COMPLETE_READ_ONLY_FAILED_CAPSULE_DIAGNOSIS",current_context=ctx,
      original_run=RUN,original_source=SOURCE,original_conclusion="failure",full_archive_members=len(inventory),
      selected_members=21,native_build_executed=False,native_extraction_executed=False,
      strict_comparator=result["original_strict_comparator"],trace_observation=trace,**b.FLAGS)

def main():
    p=argparse.ArgumentParser();p.add_argument("--pins-sha256",required=True)
    p.add_argument("--reservation",type=Path,required=True);p.add_argument("--controls",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True);a=p.parse_args()
    ctx=b.context(os.environ)
    b.require(subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()==ctx["source"],"checkout source")
    b.run(ctx,b.decode(a.reservation.read_bytes()),a.controls.read_bytes(),a.pins_sha256,a.output.resolve(),perform)
if __name__=="__main__":main()
