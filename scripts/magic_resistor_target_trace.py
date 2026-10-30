#!/usr/bin/env python3
"""Hosted complete trace observation only. No CAD, numerical solve or physical ownership claim."""
import argparse,collections,hashlib,os,subprocess
from decimal import Decimal
from pathlib import Path
import cloud_magic_resistor_provenance_build as b
ROOT=b.ROOT
CONFIG="scripts/magic-resistor-target-trace-inputs.json"
FLAGS=dict(b.FLAGS)
FIELDS=("rr_value_milliohms_hex","rr_tt","rr_width_raw","rr_cl_raw","resist_scale",
        "material_name_hex","is_contact","sheet_resist_raw","via_resist_raw")

def load_pinned(root,spec):
    raw=b.frozen.regular(root,spec["path"]).read_bytes()
    b.require(dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())==
      {k:spec[k]for k in ("bytes","sha256")},"target proof bytes: "+spec["path"])
    return b.decode(raw)

def proof(root=ROOT):
    c=b.decode(b.frozen.regular(root,CONFIG).read_bytes())
    b.require(c["schema"]=="magic-target-trace-v1"and c["scope"]==FLAGS,"target input scope")
    p={n.removeprefix(c["prefix"]):load_pinned(root,dict(path=n,**v))for n,v in c["proof_files"].items()}
    receipt=load_pinned(root,c["receipt"]);r=p["run.json"]
    b.require((r["id"],r["head_sha"],r["status"],r["conclusion"],r["run_attempt"])==
      (c["run"],c["source"],"completed","success",1),"qualified producer run")
    b.require(len(p["jobs.json"]["jobs"])==4 and all(j["conclusion"]=="success"and
      j["status"]=="completed"and j["head_sha"]==c["source"]and j["run_id"]==c["run"]
      for j in p["jobs.json"]["jobs"]),"qualified four producer jobs")
    b.require(receipt["run_id"]==c["run"]and receipt["source"]==c["source"]and
      receipt["scope"]==FLAGS and receipt["trace"]==p["assets/trace-summary.json"],"qualified trace receipt")
    b.require(c["trace"]==dict(id=690355038,**p["assets/trace-summary.json"]["trace"]),"complete original trace")
    s=load_pinned(root,c["qualified_sources"])
    old=b.decode(b.frozen.regular(root,b.CONFIG).read_bytes())["source_producer"]["candidate"]
    for n,v in s.items():
        b.require(hashlib.sha256(v["text"].encode()).hexdigest()==v["sha256"]==old[n],"actual reduction source")
    inc=load_pinned(root,c["incidence"])
    b.require(inc["status"]=="CURRENT_RC_CONTACT_INCIDENCE_READBACK_ONLY"and
      inc["full_current_counts"]==dict(C=15566,R=24356,anchors=978,components=113,devices=500),"current500 incidence")
    dc={k:load_pinned(root,v)for k,v in c["dc"].items()}
    for k,t in c["targets"].items():
        x=inc["targets"][k]
        b.require((x["component"],x["native_net"],x["native_cluster"])==(t["component"],t["net"],int(k)),"current exact target")
        b.require(dc[k]["original_target"]==x and dc[k]["DC_analysis_only"]is True and
          dc[k]["geometric_bridge_attribution_proven"]is False,"authentic DC target")
    return c,p,inc,dc

def live_binding(c,p,run,jobs,release,ref):
    for k in ("id","head_sha","head_branch","event","run_attempt","status","conclusion","workflow_id"):
        b.require(run.get(k)==p["run.json"][k],"trace producer run: "+k)
    expected={j["id"]:j for j in p["jobs.json"]["jobs"]}
    b.require(len(jobs["jobs"])==len(expected),"trace producer jobs count")
    for j in jobs["jobs"]:
        b.require(j["id"]in expected,"trace producer job id");old=expected[j["id"]]
        for k in ("name","run_id","head_sha","status","conclusion"):
            b.require(j.get(k)==old[k],"trace producer job: "+k)
        b.require([(s["number"],s["name"],s["conclusion"])for s in j["steps"]]==
          [(s["number"],s["name"],s["conclusion"])for s in old["steps"]],"trace producer steps")
    assets=b.frozen.release_binding(release,ref,c["tag"],c["source"])
    old=b.frozen.release_binding(p["release.json"],p["tag-ref.json"],c["tag"],c["source"])
    b.require(release["id"]==c["release"]and set(assets)==set(old),"trace producer asset set")
    for n,v in assets.items():
        b.require(all(v.get(k)==old[n][k]for k in ("id","size","digest")),"trace producer asset: "+n)
    a=assets["resistor-physical-trace.jsonl"]
    b.require(dict(id=a["id"],bytes=a["size"],sha256=a["digest"].removeprefix("sha256:"))==c["trace"],"actual trace direct asset")
    return dict(run=c["run"],source=c["source"],release=c["release"],trace=c["trace"],assets=len(assets))

def name(value):
    b.require(isinstance(value,str),"emitted native name")
    return bytes.fromhex(value).decode("utf-8")

def emitted_line(r):
    return 'resist "'+name(r["node1"]["name_hex"])+'" "'+name(r["node2"]["name_hex"])+'" '+r["ext_value_token"]

def signature(r):
    return dict(fields={k:r.get(k)for k in FIELDS},
      endpoints=[dict(address=r[n]["address"],xy=r[n]["xy"])for n in ("node1","node2")])

def edge_key(a,z,token):
    v=Decimal(token);b.require(v.is_finite()and v>=0,"finite exact resistor value")
    return tuple(sorted((a,z)))+(v,)

def analyze_epoch(records,target,dc):
    """Retain all observations; a residual field or address is never a reduction DAG."""
    begins=[r for r in records if r["event"]=="net_begin"]
    b.require(len(begins)==1,"one complete target epoch");epoch=begins[0]["epoch"]
    b.require(all(r["epoch"]==epoch for r in records),"single target epoch identity")
    b.require(sum(r["event"]=="net_end"for r in records)==1,"target construction complete")
    before=[r for r in records if r["event"]=="snapshot_resistor"and r["phase"]=="before_simplify"]
    after=[r for r in records if r["event"]=="snapshot_resistor"and r["phase"]=="after_simplify"]
    for phase,rows in (("before_simplify",before),("after_simplify",after)):
        starts=[r for r in records if r["event"]=="snapshot_begin"and r["phase"]==phase]
        ends=[r for r in records if r["event"]=="snapshot_end"and r["phase"]==phase]
        b.require(len(starts)==len(ends)==1 and ends[0]["count"]==len(rows)>0,"complete target snapshot")
        b.require([r["index"]for r in rows]==list(range(len(rows)))and
          starts[0]["seq"]<rows[0]["seq"]<=rows[-1]["seq"]<ends[0]["seq"],"target snapshot order")
    emissions=[r for r in records if r["event"]=="emitted_resistor"]
    expected=[r["raw"]for r in target["native_primitive_records"]if r["tokens"][0]=="resist"]
    b.require([emitted_line(r)for r in emissions]==expected,"all target native endpoint/value/order")
    b.require(len(before)==len(after)==len(emissions),"target full snapshot/output cardinality")
    byphase=[]
    for rows in (before,after,emissions):
        m={r["resistor_address"]:r for r in rows}
        b.require(len(m)==len(rows),"duplicate address in simultaneous snapshot");byphase.append(m)
    ctor=collections.defaultdict(list)
    for r in records:
        if r["event"]in ("create_tile","create_contact"):ctor[r["resistor_address"]].append(r)
    canonical=collections.defaultdict(list)
    for r in target["canonical_incidence"]:
        if r["kind"]=="R":canonical[edge_key(r["a"],r["b"],r["token"])].append(r)
    b.require(sum(map(len,canonical.values()))==len(emissions),"complete current SPICE edges")
    pairs=dc["pair_unit_injections"];expected_names={r["name"]for rows in canonical.values()for r in rows}
    for pair in pairs:
        b.require({r["name"]for r in pair["edge_responses"]}==expected_names and
          len(pair["edge_responses"])==len(expected_names),"complete existing DC edge responses")
    edges=[]
    for r in emissions:
        addr=r["resistor_address"];a=name(r["node1"]["name_hex"]);z=name(r["node2"]["name_hex"])
        match=canonical[edge_key(a,z,r["ext_value_token"])]
        b.require(bool(match),"emitted edge missing in current SPICE")
        candidates=ctor.get(addr,[]);evidence=[]
        for creation in candidates:
            evidence.append(dict(seq=creation["seq"],event=creation["event"],
              same_observed_signature=signature(creation)==signature(r),
              creation=creation,identity_continuity_proved=False))
        old=byphase[0].get(addr);new=byphase[1].get(addr)
        edges.append(dict(emitted=r,canonical_candidates=match,
          dc_responses=[dict(positive_contact=q["positive_contact"],negative_contact=q["negative_contact"],
            effective_resistance_ohm=q["effective_resistance_ohm"],
            edges=[v for v in q["edge_responses"]if v["name"]in {m["name"]for m in match}])for q in pairs],
          before_simplify=old,after_simplify=new,
          snapshot_signature_unchanged=old is not None and new is not None and signature(old)==signature(new),
          emission_signature_unchanged=new is not None and signature(new)==signature(r),
          constructor_address_observations=evidence,address_reuse_ambiguous=len(candidates)>1,
          no_constructor_observed=not candidates,physical_ownership_proved=False))
    b.require(collections.Counter(edge_key(name(r["node1"]["name_hex"]),name(r["node2"]["name_hex"]),
      r["ext_value_token"])for r in emissions)==collections.Counter({k:len(v)for k,v in canonical.items()}),
      "complete emitted/SPICE multiplicity")
    return dict(schema=1,epoch=epoch,net_begin=begins[0],component=target["component"],
      native_net=target["native_net"],native_cluster=target["native_cluster"],contacts=target["contacts"],all_edges=edges,
      counts=dict(events=len(records),constructors=sum(map(len,ctor.values())),emitted=len(emissions),
        unchanged_snapshot=sum(x["snapshot_signature_unchanged"]for x in edges),
        unchanged_emission=sum(x["emission_signature_unchanged"]for x in edges),
        repeated_constructor_address=sum(x["address_reuse_ambiguous"]for x in edges),
        missing_constructor=sum(x["no_constructor_observed"]for x in edges),
        changed_from_every_observed_constructor=sum(bool(x["constructor_address_observations"])and
          not any(v["same_observed_signature"]for v in x["constructor_address_observations"])for x in edges)),
      findings=["Construction-time ResDoneWithNode performs series/parallel/triangle transformations independently of simplify off.",
        "Matching residual rr_tt/width/cl or reused addresses does not prove reduced physical footprint.",
        "Constructor rectangles and contacts describe creation observations only.",
        "Existing DC responses are joined without rerunning the solve; no transient attribution."],**FLAGS)

def select_epochs(path,targets,out):
    owners={n["native"]:k for k,t in targets.items()for n in t["nodes"]}
    b.require(len(owners)==sum(len(t["nodes"])for t in targets.values()),"disjoint current native names")
    assignment={}
    with path.open("rb")as f:
        for raw in f:
            r=b.decode(raw)
            if r["event"]!="emitted_resistor":continue
            a=name(r["node1"]["name_hex"]);z=name(r["node2"]["name_hex"])
            keys={owners[n]for n in (a,z)if n in owners}
            if not keys:continue
            b.require(len(keys)==1 and a in owners and z in owners,"complete same-target edge")
            k=next(iter(keys));e=r["epoch"]
            b.require(e not in assignment or assignment[e]==k,"mixed trace target epoch");assignment[e]=k
    b.require(len(assignment)==len(targets)and set(assignment.values())==set(targets),"unique complete target epochs")
    result={k:[]for k in targets}
    with path.open("rb")as f:
        for raw in f:
            r=b.decode(raw)
            if r.get("epoch")in assignment:result[assignment[r["epoch"]]].append(r)
    for k,rows in result.items():b.write(out/("target-"+k+"-events.json"),b.encode(rows))
    return result

def controls_binding(raw,ctx):
    r=b.decode(raw)
    b.require(r["status"]=="PASS_MAGIC_TARGET_TRACE_SOURCE_CONTROLS"and r["passed"]is True
      and r["counts"]==dict(positive=6,refusal=18,lifecycle=3),"actual target source controls")
    b.require(r["current_context"]==dict(source=ctx["source"],run_id=ctx["run_id"],attempt=1,
      source_controls_only=True,native_executed=False)and r["native_executed"]is False,"current target controls")
    return r

def perform(ctx,reserved,controls_raw,expected,out,trace_controls,root=ROOT,api_call=b.frozen.api,fetch=b.frozen.download):
    _,_,_,admission=b.preflight(ctx,reserved,controls_raw,expected,root,api_call)
    controls_binding(trace_controls,ctx)
    c,p,inc,dc=proof(root)
    live=live_binding(c,p,api_call("actions/runs/"+str(c["run"])),
      api_call("actions/runs/"+str(c["run"])+"/attempts/1/jobs?per_page=100"),
      api_call("releases/"+str(c["release"])),api_call("git/ref/tags/"+c["tag"]))
    b.write(out/"admission.json",b.encode(dict(current=admission,qualified_trace=live)))
    b.write(out/"target-source-controls.json",trace_controls)
    work=out/"work";work.mkdir();trace=work/"resistor-physical-trace.jsonl"
    fetch(c["trace"],trace)
    b.require(b.pin(trace)=={k:c["trace"][k]for k in ("bytes","sha256")},"complete acquired trace bytes")
    census=b.validate_trace(trace,24356)
    b.require(census==p["assets/trace-summary.json"],"complete actual trace sequence/count/footer")
    b.write(out/"complete-trace-census.json",b.encode(census))
    records=select_epochs(trace,inc["targets"],out);reports={}
    for k,rows in records.items():
        report=analyze_epoch(rows,inc["targets"][k],dc[k])
        reports[k]=dict(counts=report["counts"],epoch=report["epoch"])
        b.write(out/("target-"+k+"-observation.json"),b.encode(report))
    b.source_guard(expected,root)
    return dict(status="COMPLETE_CURRENT_TARGET_TRACE_OBSERVATION_NOT_PHYSICAL_OWNERSHIP",
      current_context=ctx,producer=live,complete_trace=census,targets=reports,
      native_archive_acquired=False,native_build_executed=False,native_extraction_executed=False,
      new_numerical_solve=False,**FLAGS)

def source_archive_spec(root=ROOT):
    raw=b.frozen.regular(root,"scripts/magic-resistor-trace-source-inputs.json").read_bytes()
    spec=b.decode(raw);c,p,_,_=proof(root)
    b.require(spec["schema"]=="magic-qualified-trace-source-readback-v1"and
      (spec["producer_run"],spec["producer_source"])==(c["run"],c["source"]),"source archive identity")
    extra={n:load_pinned(root,v)for n,v in spec["archive_proofs"].items()}
    inventory=dict(extra["assets/publication-inventory.json"])
    for n in ("publication-inventory.json","direct-publication-plan.json"):
        v=spec["archive_proofs"]["assets/"+n]
        inventory[n]={k:v[k]for k in ("bytes","sha256")}
    validate_source_selection(spec,inventory)
    old=b.decode(b.frozen.regular(root,b.CONFIG).read_bytes())["source_producer"]["candidate"]
    for n in ("extract/extract.h","extract/extractInt.h"):
        b.require(inventory["work/baseline-source/"+n]["sha256"]==old[n],"qualified header source")
    b.require(inventory["work/baseline-source/extract/extractInt.h"]==
      inventory["work/trace-source/extract/extractInt.h"],"trace header unchanged")
    return spec,c,p,inventory,extra["assets/cdr-resistor-provenance-build-40978039972-1.parts.json"]

def validate_source_selection(spec,inventory):
    b.require(spec["full_archive_members"]==14508 and len(inventory)==14508,"complete successful archive census")
    names={"work/baseline-source/extract/extract.h","work/baseline-source/extract/extractInt.h",
      "work/trace-source/extract/extractInt.h","work/trace-source/resis/ResPrint.c"}
    names|={"supervision/"+v+"-make."+s for v in ("baseline","instrumented")for s in ("command.json","stdout","stderr")}
    b.require(set(spec["selected"])==names,"exact ten textual source/log selectors")
    b.require(all(inventory.get(n)==v for n,v in spec["selected"].items()),"selected full inventory identities")
    b.require(all(type(v["bytes"])is int and v["bytes"]>0 and isinstance(v["sha256"],str)and
      len(v["sha256"])==64 for v in spec["selected"].values()),"selected identity types")
    return dict(full_members=len(inventory),selected_members=len(names))

def perform_sources(ctx,reserved,controls_raw,expected,out,trace_controls,root=ROOT,
                    api_call=b.frozen.api,fetch=b.frozen.download):
    _,_,_,admission=b.preflight(ctx,reserved,controls_raw,expected,root,api_call)
    tests=controls_binding(trace_controls,ctx)
    b.require(tests["archive_source_controls"]["counts"]==dict(positive=1,refusal=5),
      "current archive source controls")
    spec,c,p,inventory,parts=source_archive_spec(root)
    live=live_binding(c,p,api_call("actions/runs/"+str(c["run"])),
      api_call("actions/runs/"+str(c["run"])+"/attempts/1/jobs?per_page=100"),
      api_call("releases/"+str(c["release"])),api_call("git/ref/tags/"+c["tag"]))
    assets={a["name"]:dict(id=a["id"],bytes=a["size"],sha256=a["digest"].removeprefix("sha256:"))
      for a in p["release.json"]["assets"]}
    b.write(out/"admission.json",b.encode(dict(current=admission,qualified_producer=live)))
    b.write(out/"target-source-controls.json",trace_controls)
    work=out/"work";work.mkdir()
    archive,transport=b.frozen.acquire(dict(assets=assets),parts,work,fetch)
    b.write(out/"transport.json",b.encode(transport))
    selected=work/"selected"
    census=b.frozen.select_archive(archive,{n:v["sha256"]for n,v in inventory.items()},
      sorted(spec["selected"]),parts["source_directory"],selected)
    b.require(census["full_members"]==inventory,"complete native capsule member size/hash identities")
    b.write(out/"full-census.json",b.encode(census))
    result={}
    for name,identity in spec["selected"].items():
        path=b.frozen.regular(selected,name)
        b.require(b.pin(path)==identity,"retained source/log bytes: "+name)
        result[name]=dict(identity=identity,text=path.read_bytes().decode("utf-8"))
    b.write(out/"qualified-build-text.json",b.encode(result))
    archive.unlink()
    b.source_guard(expected,root)
    return dict(status="COMPLETE_QUALIFIED_BUILD_SOURCE_READBACK_NOT_NEW_BUILD",
      current_context=ctx,producer=live,full_archive_members=len(inventory),selected_text_members=len(result),
      native_archive_acquired_on_runner=True,native_build_executed=False,native_extraction_executed=False,
      coefficient_types_or_values_not_reinterpreted=True,**FLAGS)


def main():
    p=argparse.ArgumentParser()
    for n in ("pins-sha256","reservation","controls","trace-controls","output"):p.add_argument("--"+n,required=True)
    p.add_argument("--operation",choices=("target-trace","trace-source"),default="target-trace")
    a=p.parse_args();ctx=b.context(os.environ)
    b.require(subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()==ctx["source"],"checkout source")
    raw=Path(a.trace_controls).read_bytes()
    b.run(ctx,b.decode(Path(a.reservation).read_bytes()),Path(a.controls).read_bytes(),a.pins_sha256,
      Path(a.output).resolve(),lambda *args:(perform_sources if a.operation=="trace-source"else perform)(*args,trace_controls=raw))
if __name__=="__main__":main()
