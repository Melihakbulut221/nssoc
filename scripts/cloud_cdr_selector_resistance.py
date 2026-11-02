"""Cloud-only passive comparison of actual source M1 RC against the measured prior ground model."""
import importlib.metadata,json,os,sys
from pathlib import Path
import cloud_cdr_wire_wave_diagnosis as prior
from cdr_selector_resistance import need,parse_model,solve

ROOT=Path(__file__).resolve().parents[1]
prior.BRANCH="codex/cdr-collector-via2-resistance"
prior.OUT=ROOT/"wire-selector-resistance"
prior.NATIVE=ROOT/"wire-selector-resistance-native"

def gate():
    cfg=prior.gate()
    need(importlib.metadata.version("numpy")=="2.3.3"and importlib.metadata.version("scipy")=="1.16.3","declared solver versions")
    need(cfg["parent"]["run"]==41391065497 and cfg["parent"]["source"]=="494a63a4136813f6018c8cab027632ff02f54d0d","actual rejected new-ground producer")
    current_configuration()
    return cfg

def compare_queries(old,new,ownership=None):
    import math
    need(len(old)==len(new)==32,"all32 comparisons")
    a={r["label"]:r for r in old};b={r["label"]:r for r in new}
    need(len(a)==len(b)==32 and set(a)==set(b),"unique identical semantic query labels")
    rows=[]
    for label in sorted(a):
        left,right=a[label],b[label]
        for key in("source_terminal","sink_terminal"):
            need(left[key]==right[key],"same native terminal ownership "+key)
        if ownership is None:
            need(left["native_net"]==right["native_net"],"same fixture net")
        else:
            need(set(ownership)==set(a),"all32actual ownership witnesses")
            p=ownership[label]
            need(left["native_net"]==p["old_native_net"]and right["native_net"]==p["new_native_net"],"actual full-partition names")
        x,y=left["effective_resistance_ohm"],right["effective_resistance_ohm"]
        need(math.isfinite(x)and math.isfinite(y)and x>0 and y>0,"positive finite measured resistances")
        rows.append(dict(label=label,source_terminal=right["source_terminal"],sink_terminal=right["sink_terminal"],
            native_net=right["native_net"],before_ohm=x,after_ohm=y,delta_ohm=y-x,ratio=y/x))
    return rows

def comparison_controls():
    import copy
    original=[dict(label="fixture_"+str(i),source_terminal=[i,"S"],sink_terminal="public_avss",native_net="avss",effective_resistance_ohm=2.)for i in range(32)]
    newer=copy.deepcopy(original)
    for r in newer:r["effective_resistance_ohm"]=1.
    need(all(r["delta_ohm"]==-1.0 and r["ratio"]==.5 for r in compare_queries(original,newer)),"known comparison")
    passed=["known32query ratios"]
    for label in("missing","duplicate","terminal","net","zero","nonfinite"):
        bad=copy.deepcopy(newer)
        if label=="missing":bad.pop()
        elif label=="duplicate":bad[-1]["label"]=bad[0]["label"]
        elif label=="terminal":bad[0]["source_terminal"]=[999,"S"]
        elif label=="net":bad[0]["native_net"]="avdd"
        elif label=="zero":bad[0]["effective_resistance_ohm"]=0.
        elif label=="nonfinite":bad[0]["effective_resistance_ohm"]=float("nan")
        try:compare_queries(original,bad)
        except ValueError:passed.append("reject "+label)
        else:raise AssertionError(label)
    prior.save("comparison-controls.json",dict(passed=passed,count=len(passed),native_executed=False))

def partition_identity(left,right):
    import re
    def normalize(c):
        need(len(c["device_records"])==500 and sum(len(d["terminals"])for d in c["device_records"])==1446,"whole500device1446terminal composition")
        public=set(c["interface"])-{"wire_cref"}
        need(len(public)==25,"all25real ports")
        devices={};groups={}
        for d in c["device_records"]:
            i=int(d["native_id"]);need(i not in devices,"unique native device id")
            devices[i]=dict(model=d["model"],parameters=d["parameters"],terminals=sorted((t["terminal"],t["anchor"])for t in d["terminals"]))
            for t in d["terminals"]:
                name=t["native_net"];need(name in public or re.fullmatch(r"\$[0-9]+",name),"public or actual unnamed native net")
                g=groups.setdefault(t["native_cluster"],dict(name=name,members=[]))
                need(g["name"]==name,"one name per actual cluster")
                g["members"].append((i,d["model"],t["terminal"]))
        out={}
        for cluster,g in groups.items():
            key=json.dumps(dict(public_port=g["name"]if g["name"]in public else None,terminals=sorted(g["members"])),sort_keys=True,separators=(",",":"))
            need(key not in out,"unique complete native partition")
            out[key]=dict(native_net=g["name"],native_cluster=cluster,terminal_count=len(g["members"]))
        need(len({g["native_net"]for g in out.values()})==len(out),"unique full native names")
        return devices,out,public
    a,x,pa=normalize(left);b,y,pb=normalize(right)
    need(a==b and pa==pb,"all actual primitive parameters terminals anchors and port names preserved")
    need(set(x)==set(y),"all complete native terminal partitions preserved")
    rows=[dict(partition=json.loads(k),old=x[k],new=y[k])for k in sorted(x)]
    return dict(status="PASS_ALL500_PRIMITIVES1446_TERMINALS_COMPLETE_PARTITIONS",partition_count=len(rows),rows=rows)

def ownership_for_queries(proof,queries):
    out={}
    for q in queries:
        origin=tuple(q["source_terminal"])
        found=[r for r in proof["rows"]if any((m[0],m[2])==origin for m in r["partition"]["terminals"])]
        need(len(found)==1,"unique whole native source partition")
        r=found[0];dest=q["sink_terminal"]
        if dest=="public_avss":need(r["partition"]["public_port"]=="avss","actual public ground endpoint")
        else:need(any((m[0],m[2])==tuple(dest)for m in r["partition"]["terminals"]),"actual sink in same full partition")
        need(q["native_net"]==r["old"]["native_net"],"original query really belongs to old partition")
        out[q["label"]]=dict(old_native_net=r["old"]["native_net"],new_native_net=r["new"]["native_net"],full_partition=r["partition"])
    need(len(out)==len(queries)==32,"all32owned queries")
    return out

def partition_controls():
    import copy
    original=json.loads((ROOT/"scripts/cdr-source-m1-resistance-reference-composition.json").read_bytes())
    renamed=copy.deepcopy(original);changes=0
    for d in renamed["device_records"]:
        for t in d["terminals"]:
            if t["native_net"]=="$700":t["native_net"]="$999999";changes+=1
    need(changes>0,"actual formerly numbered emitter net present")
    proof=partition_identity(original,renamed)
    need(any(r["old"]["native_net"]=="$700"and r["new"]["native_net"]=="$999999"for r in proof["rows"]),"renumbering preserves complete ownership")
    passed=["complete actual500device partition identity across unnamed renumbering"]
    for label in("changed-membership","changed-parameter","renamed-public"):
        bad=copy.deepcopy(original)
        if label=="changed-membership":
            terms=bad["device_records"][0]["terminals"];terms[0]["native_cluster"]=terms[1]["native_cluster"];terms[0]["native_net"]=terms[1]["native_net"]
        elif label=="changed-parameter":bad["device_records"][0]["parameters"]["w"]="99u"
        elif label=="renamed-public":
            for d in bad["device_records"]:
                for t in d["terminals"]:
                    if t["native_net"]=="avss":t["native_net"]="avss_changed"
        try:partition_identity(original,bad)
        except ValueError:passed.append("reject "+label)
        else:raise AssertionError(label)
    prior.save("partition-controls.json",dict(count=len(passed),passed=passed,native_executed=False))

def current_configuration():
    c=json.loads((ROOT/"scripts/cdr-source-m1-resistance-inputs.json").read_bytes())
    p=c["producer"];ref=c["reference"]
    need(c["schema"]=="nssoc.collector-via2.resistance-comparison.v1","exact comparison schema")
    need((p["run"],p["source"],p["release"])==(41439516945,"710869eb13082f3c3dc488159bf167d937294454",431398178),"actual current freshRC")
    need((ref["run"],ref["source"],ref["artifact"]["id"])==(41395210468,"4a20c52579eddaa7f0a1f82f41cb6af8445b806c",13118444894),"actual prior full-network sensitivity")
    q=c["qualification"]
    need(q["candidate"]==dict(bytes=1078900,sha256="c0d420cdbc31863bf21086e88c12f494779961225031c261d6b05fe07e7585a7"),"current actual geometry")
    need(q["model"]==dict(bytes=2112906,sha256="e388befe16436bf93ae3ab561f3d3ffb0d0403cabae887d0de3a142b41566001"),"current actual new model")
    need(q["counts"]==dict(devices=500,R=26222,C=16798),"actual measured complete census")
    return c

def acquire_current(c):
    p=c["producer"];run=prior.api("actions/runs/"+str(p["run"]));rel=prior.api("releases/"+str(p["release"]));tag=prior.api("git/ref/tags/"+p["tag"])
    need(run["status"]=="completed"and run["conclusion"]=="success"and run["head_sha"]==p["source"]and run["run_attempt"]==1,"current successful fresh RC producer")
    need(rel["target_commitish"]==p["source"]and rel["tag_name"]==p["tag"]and tag["object"]["sha"]==p["source"],"current exact release source")
    live={a["name"]:a for a in rel["assets"]};need(set(live)==set(p["assets"]),"complete current release set")
    prior.NATIVE.mkdir(exist_ok=True)
    cache=prior.NATIVE/"current";cache.mkdir()
    for name,a in p["assets"].items():
        actual=live[name]
        need(actual["id"]==a["id"]and actual["size"]==a["bytes"]and actual["digest"]=="sha256:"+a["sha256"],"current release asset identity")
        dest=cache/name
        with dest.open("xb")as f:prior.subprocess.run(["gh","api","repos/"+prior.REPO+"/releases/assets/"+str(a["id"]),"-H","Accept: application/octet-stream"],stdout=f,check=True,timeout=600)
        need(prior.pin(dest)==dict(bytes=a["bytes"],sha256=a["sha256"]),"complete current asset bytes")
    idx=json.loads((cache/"complete-output-index.json").read_bytes())
    need(idx==c["index"]and idx["context"]==dict(run=p["run"],source=p["source"],attempt=1),"complete current native index")
    wanted=set(c["selected"]);seen=set();dest=cache/"selected";dest.mkdir()
    need(wanted<=set(idx["files"]),"known selected native inputs")
    with prior.tarfile.open(cache/"native-fresh-rc.tar.gz","r|gz")as tar:
        for m in tar:
            prefix="wire-shortcuts-fresh-rc/";need(m.name.startswith(prefix),"owned archive root")
            name=m.name[len(prefix):];q=Path(name)
            need(m.isfile()and name not in seen and name in idx["files"]and not q.is_absolute()and ".."not in q.parts and str(q)==name,"unique regular indexed safe member")
            expected=idx["files"][name];need(m.size==expected["bytes"],"member size")
            h=prior.hashlib.sha256();size=0;f=tar.extractfile(m);target=dest/name
            if name in wanted:target.parent.mkdir(parents=True,exist_ok=True)
            out=target.open("xb")if name in wanted else None
            try:
                while chunk:=f.read(8*1024*1024):
                    h.update(chunk);size+=len(chunk)
                    if out is not None:out.write(chunk)
            finally:
                if out is not None:out.close()
                f.close()
            need(dict(bytes=size,sha256=h.hexdigest())==expected,"complete member digest "+name);seen.add(name)
    need(seen==set(idx["files"]),"all current native members authenticated")
    paths={role:dest/name for name,role in c["selected"].items()}
    q=json.loads(paths["qualification"].read_bytes());oq=json.loads(paths["original_qualification"].read_bytes())
    need(q==c["qualification"]and q["status"]=="PASS_COLLECTOR_VIA2_FRESH_RC_NUMERICAL_QUALIFICATION_REQUIRES_LOADED_WAVES"and q["fresh_RC_executed"],"actual complete new RC qualification")
    need(oq["status"]=="PASS_CURRENT_VIA2_M3_FRESH_RC_NUMERICAL_QUALIFICATION_REQUIRES_LOADED_WAVES"and oq["fresh_RC_pipeline_complete"]and oq["execution_scope"]=="ACTUAL_AUTHORIZED_NATIVE_PHASE","original actual numerical qualification")
    need(q["current_context"]==oq["context"]==dict(run_id=p["run"],source=p["source"],attempt=1),"current numerical context")
    need(q["original_qualification"]==prior.pin(paths["original_qualification"])and len(oq["phase_receipts"])==11,"all current numerical receipts")
    for name,value in oq["phase_receipts"].items():need(idx["files"]["native-phase-reports/"+name+".json"]==value,"phase receipt")
    for role in("model","composition"):need(prior.pin(paths[role])==q[role],"current role bytes")
    need(q["counts"]==oq["counts"],"actual full model census")
    prior.save("current-acquisition.json",dict(producer=p,authenticated_members=len(seen),selected=c["selected"],native_payloads_cloud_only=True,all_native_members_authenticated=True))
    return paths

def acquire_reference(c):
    import io,zipfile
    p=c["reference"];r=prior.api("actions/runs/"+str(p["run"]));a=prior.api("actions/artifacts/"+str(p["artifact"]["id"]))
    need(r["status"]=="completed"and r["conclusion"]=="success"and r["head_sha"]==p["source"]and r["run_attempt"]==1,"qualified reference resistance run")
    need(a["workflow_run"]["id"]==p["run"]and a["workflow_run"]["head_sha"]==p["source"]and a["size_in_bytes"]==p["artifact"]["bytes"]and a["digest"]=="sha256:"+p["artifact"]["sha256"],"reference artifact source")
    raw=prior.subprocess.check_output(["gh","api","repos/"+prior.REPO+"/actions/artifacts/"+str(a["id"])+"/zip"],timeout=180)
    need(len(raw)==p["artifact"]["bytes"]and prior.hashlib.sha256(raw).hexdigest()==p["artifact"]["sha256"],"whole reference artifact")
    z=zipfile.ZipFile(io.BytesIO(raw));need(len(z.namelist())==len(set(z.namelist())),"unique reference members")
    rb=z.read("result.json");need(dict(bytes=len(rb),sha256=prior.hashlib.sha256(rb).hexdigest())==p["result"],"reference result pin")
    q=json.loads(rb)
    need(q["status"]=="COMPLETE_ACTUAL_EXTRACTED_SELECTOR_RESISTANCE_SENSITIVITY"and q["run"]==p["run"]and q["source"]==p["source"]and q["original_electrical_rejection_preserved"],"actual previous passive measurement")
    need(q["inputs"]["model"]==dict(bytes=1982585,sha256="0bfdbf74c8dd73b2234b771746785af57fade28f122af94b436096c27b2ff943"),"actual preceding horizontal-ground model")
    need(q["counts"]==dict(devices=500,R=24530,C=15676)and len(q["queries"])==32,"complete old network query census")
    for row in q["queries"]:
        b=z.read(row["full_result"])
        need(dict(bytes=len(b),sha256=prior.hashlib.sha256(b).hexdigest())==row["full_result_pin"],"actual original full pair solution")
        pair=json.loads(b)
        need(pair["effective_resistance_ohm"]==row["effective_resistance_ohm"],"old full solution summary binding")
    prior.save("reference-result.json",q)
    prior.save("reference-acquisition.json",dict(run=r,artifact=a,all32_full_pair_results_authenticated=True))
    return q

def main():
    cfg=gate();prior.OUT.mkdir(exist_ok=True)
    if sys.argv[1:]==["--controls"]:
        prior.controls()
        comparison_controls()
        partition_controls()
        return
    need(sys.argv[1:]==["--analyze"],"explicit read-only analysis")
    current=current_configuration()
    paths=acquire_current(current)
    reference=acquire_reference(current)
    before={name:prior.pin(path)for name,path in paths.items()}
    contract=json.loads(paths["composition"].read_bytes())
    need(prior.pin(paths["model"])==dict(bytes=2112906,sha256="e388befe16436bf93ae3ab561f3d3ffb0d0403cabae887d0de3a142b41566001"),"exact actual source M1 RC")
    need(prior.pin(paths["composition"])==dict(bytes=1015133,sha256="d775d58fcaaba7c6f4d5d06a51645839e0b0e4e853de5e6249f3156b1f9b27d5"),"exact actual source M1 composition")
    edges,counts=parse_model(paths["model"].read_text(),contract)
    need(counts==dict(devices=500,R=26222,C=16798),"complete actual RC census")
    device={int(d["native_id"]):d for d in contract["device_records"]}
    def terminal(i,t):
        rows=[r for r in device[i]["terminals"]if r["terminal"]==t]
        need(len(rows)==1,"unique actual native terminal")
        return rows[0]
    queries=[]
    for first,seconds,origin,dest,group in [
        ((61,62),(54,56),"C","E","D_collector"),
        ((115,116),(106,108),"C","E","C_collector"),
        ((61,62),(3,4,5,6),"E","D","D_emitter"),
        ((115,116),(32,33,34,35),"E","D","C_emitter")]:
        for a in first:
            for b in seconds:
                x=terminal(a,origin);y=terminal(b,dest)
                need((x["native_cluster"],x["native_net"])==(y["native_cluster"],y["native_net"]),"same real extracted net")
                queries.append(dict(label=group+"_"+str(a)+"_"+str(b),source=x["node"].lower(),sink=y["node"].lower(),native_net=x["native_net"],source_terminal=[a,origin],sink_terminal=[b,dest]))
    need("avss"in contract["interface"],"real public avss port")
    for i in(3,4,5,6,32,33,34,35):
        x=terminal(i,"S");need(x["native_net"]=="avss","actual source ground ownership")
        queries.append(dict(label="ground_"+str(i),source=x["node"].lower(),sink="avss",native_net="avss",source_terminal=[i,"S"],sink_terminal="public_avss"))
    need(len(queries)==32,"all four selectors and eight source ground paths")
    summary=[]
    for query in queries:
        result=solve(edges,query["source"],query["sink"])
        reverse=solve(edges,query["sink"],query["source"])
        reff=result["effective_resistance_ohm"]
        need(abs(reverse["effective_resistance_ohm"]-reff)<=max(1e-9,1e-7*reff),"actual network reciprocity")
        result.update(query=query,reverse_resistance_ohm=reverse["effective_resistance_ohm"],physical_acceptance=False,full_phy_accepted=False)
        filename="pairs/"+query["label"]+".json";prior.save(filename,result)
        summary.append(dict(**query,effective_resistance_ohm=reff,component_nodes=result["component_nodes"],
            component_resistors=result["component_resistors"],maximum_kcl_residual_a=result["maximum_kcl_residual_a"],
            full_result=filename,full_result_pin=prior.pin(prior.OUT/filename),top_edges=result["full_edge_contributions"][:12]))
    old_contract=json.loads((ROOT/"scripts/cdr-source-m1-resistance-reference-composition.json").read_bytes())
    need(prior.pin(ROOT/"scripts/cdr-source-m1-resistance-reference-composition.json")==reference["inputs"]["composition"],"actual old analyzed composition")
    identity=partition_identity(old_contract,contract)
    ownership=ownership_for_queries(identity,reference["queries"])
    prior.save("native-partition-comparison.json",identity)
    prior.save("query-ownership.json",ownership)
    comparison=compare_queries(reference["queries"],summary,ownership)

    prior.save("model-comparison.json",dict(status="COMPLETE_ACTUAL_COLLECTOR_VIA2_RESISTANCE_COMPARISON",
        current_rc=current["producer"],reference=current["reference"],queries=comparison,
        same_frozen_solver=True,all32_actual_full_network_queries=True,new_transient_executed=False,
        loaded_simulation_passed=False,qualified_pex=False,full_phy_accepted=False,final_timing_complete=False))
    need(before=={name:prior.pin(path)for name,path in paths.items()},"all actual model and evidence bytes unchanged")
    gate()
    prior.save("result.json",dict(status="COMPLETE_ACTUAL_COLLECTOR_VIA2_SELECTOR_RESISTANCE_SENSITIVITY",
        source=os.environ["GITHUB_SHA"],run=int(os.environ["GITHUB_RUN_ID"]),reference_parent=cfg["parent"],current_rc=current["producer"],counts=counts,
        inputs=before,queries=summary,solver_versions={n:importlib.metadata.version(n)for n in("numpy","scipy")},
        original_electrical_rejection_preserved=True,all_native_members_authenticated=True,
        new_transient_executed=False,loaded_simulation_passed=False,qualified_pex=False,
        full_phy_accepted=False,physical_acceptance=False,final_timing_complete=False,
        limits="Resistor-only unit-current network with other terminals floating. Capacitors are counted and preserved but excluded from this diagnostic. Edge power ranks sensitivity, not actual operating power. No nonlinear or transient acceptance follows."))
    print("COMPLETE_ACTUAL_COLLECTOR_VIA2_SELECTOR_RESISTANCE_SENSITIVITY",flush=True)

if __name__=="__main__":
    try:main()
    except BaseException as exc:
        import traceback
        prior.OUT.mkdir(exist_ok=True)
        prior.save("failure-"+sys.argv[1].lstrip("-")+".json",dict(error=repr(exc),traceback=traceback.format_exc(),physical_acceptance=False,full_phy_accepted=False))
        raise
