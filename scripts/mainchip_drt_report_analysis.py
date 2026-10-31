#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted textual DRT record census; no layout geometry or physical causality."""
import argparse,collections,json,os,re,subprocess,time,types
from pathlib import Path
import mainchip_terminal_readback as q
ROOT=Path(__file__).resolve().parents[1]
BRANCH="codex/mainchip-drt-report-analysis"
GROUP="mainchip-drt-report-analysis"
MANIFEST="scripts/mainchip-drt-report-analysis-source.json"
CONFIG="scripts/mainchip-drt-report-analysis-inputs.json"
OUT=ROOT/"drt-report-analysis"
FLAGS=dict(physical_acceptance=False,timing_accepted=False,full_phy_accepted=False,
           native_tools_executed=False,reroute_executed=False,geometry_computed=False,
           physical_cause_proven=False)
def parse_report(raw):
    text=raw.decode("utf-8")
    q.require(text.endswith("\n")and "\r"not in text,"complete LF report")
    lines=text.splitlines();q.require(lines and len(lines)%3==0,"complete triples")
    rows=[]
    for i in range(0,len(lines),3):
        kind=re.fullmatch(r"violation type: ([A-Za-z][A-Za-z0-9 ()/_-]*)",lines[i])
        source=re.fullmatch(r"\tsrcs: (net:\S+(?: net:\S+)*)",lines[i+1])
        box=re.fullmatch(r"\tbbox = \((-?\d+\.\d+), (-?\d+\.\d+)\) - \((-?\d+\.\d+), (-?\d+\.\d+)\) on Layer ([A-Za-z][A-Za-z0-9_]*)",lines[i+2])
        q.require(kind is not None and source is not None and box is not None,"exact complete report grammar")
        # Coordinates stay exact strings. No overlap, area, distance or grid calculation.
        rows.append(dict(ordinal=i//3,kind=kind[1],nets=[s[4:]for s in source[1].split(" ")],
          layer=box[5],bbox_text=lines[i+2],raw="\n".join(lines[i:i+3])+"\n"))
    return rows
def ownership(plan,mutation):
    for value in(plan,mutation):
        q.require(all(value[k]is False for k in("physical_acceptance","timing_accepted","full_phy_accepted")),"rejected input scope")
    def names(value):
        q.require(type(value)is list and value and all(type(s)is str and s for s in value),"nonempty names")
        q.require(len(value)==len(set(value)),"unique names");return set(value)
    mutable=names(plan["mutable_nets"]);protected=names(plan["protected_nets"])
    added=names(plan["added_instances"]);attachments=plan["attachments"]
    q.require(type(attachments)is dict and set(attachments)==added,"complete added attachment census")
    q.require(set(attachments.values())==mutable and not mutable&protected,"exact disjoint ownership")
    q.require(mutation["complete"]is True and mutation["all_guides_unchanged"]is True,"completed clear")
    delta=mutation["delta"]
    q.require(delta["complete"]is True and delta["all_nonmutable_exact"]is True
      and delta["all_instances_and_guides_checked_separately"]is True,"full clear guards")
    q.require(names(delta["cleared_nets"])==mutable and set(mutation["removed"])==mutable,"actual clear ownership")
    q.require(all(delta[k]is False for k in("physical_acceptance","timing_accepted","full_phy_accepted")),"clear rejected scope")
    return mutable,protected,attachments
def classify(rows,owners):
    mutable,protected,attachments=owners
    attached=collections.defaultdict(list)
    for inst,net in attachments.items():attached[net].append(inst)
    result=[];groups=collections.Counter();pairs=collections.Counter()
    for row in rows:
        def label(net):
            if net in mutable:return "mutable_cleared_manifest"
            if net in protected:return "protected_manifest"
            return "not_in_either_manifest"
        r=dict(row)
        r["net_ownership"]=[dict(net=n,ownership=label(n),attached_added_instances=sorted(attached.get(n,[])))for n in row["nets"]]
        classes=tuple(sorted(label(n)for n in row["nets"]))
        groups[(row["kind"],row["layer"],classes)]+=1
        pairs[(row["kind"],row["layer"],tuple(sorted(row["nets"])))]+=1
        result.append(r)
    return dict(records=result,total_records=len(rows),
      by_type_layer_ownership=[dict(kind=k[0],layer=k[1],ownership=list(k[2]),records=v)for k,v in sorted(groups.items())],
      by_type_layer_net_tuple=[dict(kind=k[0],layer=k[1],nets=list(k[2]),records=v)for k,v in sorted(pairs.items())])
def exact_delta(before,after):
    a=collections.Counter(x["raw"]for x in before);b=collections.Counter(x["raw"]for x in after)
    def rows(c):return [dict(raw=raw,occurrences=count)for raw,count in sorted(c.items())]
    return dict(method="exact raw three-line multiset; no geometric equivalence",
      unchanged=rows(a&b),removed=rows(a-b),added=rows(b-a),
      unchanged_records=sum((a&b).values()),removed_records=sum((a-b).values()),added_records=sum((b-a).values()))
def analyze(inputs):
    owners=ownership(q.decode(inputs["insertion-plan.json"]),q.decode(inputs["stale-wire-mutation.json"]))
    before=parse_report(inputs["fixed-routing.drc-5.rpt"]);after=parse_report(inputs["fixed-routing.drc-10.rpt"])
    return dict(status="COMPLETE_TEXTUAL_DRT_MANIFEST_CLASSIFICATION",
      ownership_scope="Only exact manifest membership and attached instance names; no current physical ownership proof",
      physical_geometry_scope="No bbox arithmetic, layout acquisition, OpenDB, CAD, or route execution",
      mutable_manifest_nets=len(owners[0]),protected_manifest_nets=len(owners[1]),
      added_attachment_records=len(owners[2]),iteration5=classify(before,owners),
      iteration10=classify(after,owners),exact_record_delta=exact_delta(before,after),**FLAGS)
def source_gate():
    q.require(os.environ.get("GITHUB_ACTIONS")=="true"and os.environ.get("GITHUB_REPOSITORY")==q.REPO,"hosted only")
    q.require(os.environ.get("GITHUB_EVENT_NAME")=="workflow_dispatch"and os.environ.get("GITHUB_REF")=="refs/heads/"+BRANCH,"actual manual source branch")
    head=os.environ["GITHUB_SHA"];q.require(re.fullmatch("[a-f0-9]{40}",head)is not None,"source SHA")
    q.require(subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()==head,"exact checkout")
    m=q.decode((ROOT/MANIFEST).read_bytes())
    q.require(m["schema"]=="mainchip-textual-drt-analysis-source-v1"and m["native_execution_authorized"]is False,"source scope")
    for n,p in m["files"].items():
        q.valid_name(n);q.filepin(p);q.require((ROOT/n).is_file()and not(ROOT/n).is_symlink()and q.pin(ROOT/n)==p,"protected source "+n)
    return q.decode((ROOT/CONFIG).read_bytes()),head
def producer(p):
    run=q.api("actions/runs/"+str(p["run"]));release=q.api("releases/"+str(p["release_id"]));ref=q.api("git/ref/tags/"+p["tag"])
    q.require(run["status"]=="completed"and run["conclusion"]=="success"and run["head_sha"]==p["source"]and run["run_attempt"]==1,"completed exact source readback")
    q.require(q.immutable_release(release)==p["immutable_release"],"exact complete derived publication")
    q.require(ref["object"]["type"]=="commit"and ref["object"]["sha"]==p["source"],"derived tag source")
    return dict(run=run,release=release,ref=ref)
def run():
    c,head=source_gate()
    q.require(os.environ.get("GITHUB_JOB")=="analysis"and os.environ.get("MODE")=="analysis"and os.environ.get("APPROVED_SOURCE")==head,"reviewed exact source analysis")
    q.require(os.environ.get("GITHUB_RUN_ATTEMPT")=="1","one attempt")
    destination=types.FunctionType(q.destination.__code__,dict(q.destination.__globals__,GROUP=GROUP),q.destination.__name__,q.destination.__defaults__,q.destination.__closure__)
    deadline=time.monotonic()+180
    while True:
        try:tag,reserved=destination(head,True);break
        except subprocess.CalledProcessError as exc:
            if b"HTTP 404"not in(exc.stderr or b"")or time.monotonic()>=deadline:raise
            time.sleep(2)
    q.require(not OUT.exists(),"exclusive output");OUT.mkdir()
    (OUT/"reservation.json").write_bytes(q.encode(reserved))
    try:
        before={k:producer(p)for k,p in c["producers"].items()}
        inputs={}
        for n,p in c["inputs"].items():
            q.require(n in("fixed-routing.drc-5.rpt","fixed-routing.drc-10.rpt","insertion-plan.json","stale-wire-mutation.json"),"derived input whitelist")
            assets={a["name"]:a for a in before[p["producer"]]["release"]["assets"]};a=assets[p["asset_name"]]
            q.require(a["id"]==p["asset_id"]and a["size"]==p["bytes"]and a["digest"]=="sha256:"+p["sha256"],"pinned derived input identity")
            raw=q.api("releases/assets/"+str(p["asset_id"]),True);q.checked(raw,{k:p[k]for k in("bytes","sha256")});raw.decode("utf-8");inputs[n]=raw
        result=analyze(inputs);result.update(source=head,run=int(os.environ["GITHUB_RUN_ID"]),input_pins=c["inputs"])
        after={k:producer(p)for k,p in c["producers"].items()}
        for k in before:q.require(q.immutable_release(before[k]["release"])==q.immutable_release(after[k]["release"])and before[k]["ref"]==after[k]["ref"],"unchanged source publication")
        (OUT/"producer-before.json").write_bytes(q.encode(before));(OUT/"producer-after.json").write_bytes(q.encode(after))
        (OUT/"result.json").write_bytes(q.encode(result))
        expected={p.name:q.pin(p)for p in OUT.iterdir()}
        destination(head,True)
        for n in expected:subprocess.run(["gh","release","upload",tag,str(OUT/n),"--repo",q.REPO],check=True)
        _,published=destination(head,False,expected)
        receipt=dict(source=head,run=int(os.environ["GITHUB_RUN_ID"]),release_id=published["id"],tag=tag,files=dict(expected),receipt_self_not_in_files=True,**FLAGS)
        rp=OUT/"publication-receipt.json";rp.write_bytes(q.encode(receipt))
        subprocess.run(["gh","release","upload",tag,str(rp),"--repo",q.REPO],check=True)
        expected[rp.name]=q.pin(rp);destination(head,False,expected)
        print(json.dumps(dict(status=result["status"],source=head,run=result["run"],iteration5=result["iteration5"]["total_records"],iteration10=result["iteration10"]["total_records"],**FLAGS)),flush=True)
    except BaseException as exc:
        (OUT/"failure.json").write_bytes(q.encode(dict(error=repr(exc),**FLAGS)));raise
def main():
    p=argparse.ArgumentParser();p.add_argument("--controls",action="store_true");args=p.parse_args()
    if args.controls:
        c,head=source_gate();print(json.dumps(dict(status="PASS_TEXTUAL_DRT_SOURCE_BINDING_ONLY",source=head,selected_inputs=sorted(c["inputs"]),**FLAGS)))
    else:run()
if __name__=="__main__":main()
