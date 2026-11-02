"""Cloud-only exact report-to-original-owner selection; not route acceptance."""
import collections,copy,hashlib,io,json,os,subprocess,traceback,zipfile
from pathlib import Path
OUT=Path("route47-plan")
REPO="repos/Melihakbulut221/nssoc/"
def need(value,message):
    if not value:raise ValueError(message)
def sha(b):return hashlib.sha256(b).hexdigest()
def encode(x):return (json.dumps(x,sort_keys=True,indent=2)+"\n").encode()
def save(name,value):(OUT/name).write_bytes(encode(value))
def api(path):return json.loads(subprocess.check_output(["gh","api",REPO+path]))
def select(records,scope):
    owned=scope["routing_nets"];protected=scope["protected_nets"]
    need(owned and len(owned)==len(set(owned)),"unique routing scope")
    need(protected and len(protected)==len(set(protected)),"unique protected scope")
    owned=set(owned);protected=set(protected);need(not owned&protected,"protected scope disjoint")
    need(records,"nonempty complete report")
    selected=set();unknown=set();rows=[];counts=collections.Counter()
    for record in records:
        source=record["sources"];tokens=source.split(" ")
        need(tokens and all(t.startswith("net:")and len(t)>4 and not any(c.isspace()for c in t)for t in tokens),"literal net source tokens")
        names=[t[4:]for t in tokens]
        need(record["type"]in("Short","Metal Spacing"),"observed iteration20 types")
        affected=sorted(set(names)&owned)
        need(affected,"every violation touches authorized routing owner")
        selected.update(affected)
        classifications=["owned"if n in owned else"protected"if n in protected else"outside_scope_requires_native_identity"for n in names]
        unknown.update(n for n in names if n not in owned|protected)
        counts["+".join(sorted(set(classifications)))]+=1
        rows.append(dict(**record,names=names,classes=classifications,selected_owners=affected))
    need(selected<=owned and not selected&protected,"selected scope")
    return dict(selected_routing_nets=sorted(selected),selected_count=len(selected),records=rows,violations=len(rows),
        class_counts=dict(counts),outside_scope_requires_native_identity=sorted(unknown),
        full_native_identity_verified=False,native_execution_authorized=False,
        routing_complete=False,physical_acceptance=False,timing_accepted=False,full_phy_accepted=False)
def controls():
    s=dict(routing_nets=["owned","literal\\[3\\]"],protected_nets=["clk"])
    r=[dict(sources="net:owned net:clk",type="Short",layer="Metal2",bbox_line="synthetic"),
       dict(sources="net:literal\\[3\\] net:foreign",type="Metal Spacing",layer="Metal3",bbox_line="synthetic")]
    result=select(r,s);need(result["selected_routing_nets"]==["literal\\[3\\]","owned"],"literal escaped identifiers preserved")
    need(result["outside_scope_requires_native_identity"]==["foreign"]and not result["native_execution_authorized"],"unresolved names retained")
    cases=["literal escaped identity","unresolved names retained without routing admission"]
    for label in ("protected-owner","duplicate-owner","duplicate-clock","unowned-only","bad-prefix","double-space","empty-net","unknown-type","empty-report"):
        a=copy.deepcopy(r);b=copy.deepcopy(s)
        if label=="protected-owner":b["routing_nets"].append("clk")
        elif label=="duplicate-owner":b["routing_nets"].append("owned")
        elif label=="duplicate-clock":b["protected_nets"].append("clk")
        elif label=="unowned-only":a[0]["sources"]="net:foreign net:clk"
        elif label=="bad-prefix":a[0]["sources"]="pin:owned net:clk"
        elif label=="double-space":a[0]["sources"]="net:owned  net:clk"
        elif label=="empty-net":a[0]["sources"]="net: net:clk"
        elif label=="unknown-type":a[0]["type"]="ignored"
        elif label=="empty-report":a=[]
        try:select(a,b)
        except ValueError:cases.append("refuse "+label)
        else:raise AssertionError(label)
    need(len(cases)==11,"complete controls")
    return cases
def acquire(cfg):
    run=api("actions/runs/"+str(cfg["run"]))
    need(run["head_sha"]==cfg["source"]and run["status"]=="completed"and run["conclusion"]==cfg["conclusion"]and run["run_attempt"]==1,"exact terminal producer")
    art=api("actions/artifacts/"+str(cfg["artifact"]))
    need(not art["expired"]and art["workflow_run"]["id"]==cfg["run"]and art["workflow_run"]["head_sha"]==cfg["source"],"exact artifact producer")
    need(art["size_in_bytes"]==cfg["bytes"]and art["digest"]=="sha256:"+cfg["sha256"],"artifact identity")
    data=subprocess.check_output(["gh","api",REPO+"actions/artifacts/"+str(cfg["artifact"])+"/zip"])
    need(len(data)==cfg["bytes"]and sha(data)==cfg["sha256"],"whole artifact bytes")
    archive=zipfile.ZipFile(io.BytesIO(data));names=archive.namelist()
    need(len(names)==len(set(names))and cfg["member"]in names,"unique exact member")
    b=archive.read(cfg["member"])
    save(cfg["label"]+"-receipt.json",dict(run=run,artifact=art,member=cfg["member"],member_pin=dict(bytes=len(b),sha256=sha(b))))
    value=json.loads(b);save(cfg["label"]+"-input.json",value)
    return value
def main():
    OUT.mkdir(exist_ok=False)
    try:
        need(os.environ["GITHUB_REF"]=="refs/heads/codex/mainchip-route47-plan"and os.environ["GITHUB_RUN_ATTEMPT"]=="1","first exact branch dispatch")
        pins=json.loads(Path("scripts/mainchip-route47-pins.json").read_bytes())
        for n,p in pins.items():
            b=Path(n).read_bytes();need(dict(bytes=len(b),sha256=sha(b))==p,"source "+n)
        save("controls.json",dict(count=11,cases=controls()))
        cfg=json.loads(Path("scripts/mainchip-route47-inputs.json").read_bytes())
        reports=acquire(cfg["reports"]);scope=acquire(cfg["scope"])
        actual=reports["iterations"]["20"]
        need(actual["violations"]==len(actual["records"])==140 and actual["by_type"]=={"Short":89,"Metal Spacing":51},"actual complete iteration20 report")
        need(len(scope["routing_nets"])==828 and len(scope["protected_nets"])==1691,"actual original scope")
        result=select(actual["records"],scope)
        need(result["selected_count"]==47 and len(result["outside_scope_requires_native_identity"])==68,"actual literal report incidence")
        need(result["class_counts"]=={"owned+protected":7,"outside_scope_requires_native_identity+owned":127,"owned":6},"all140records classified without guessing names")
        result["snapshot"]=reports["matching_snapshot_pins"]["20"]
        result["requires"]=["native ODB identity of every source name","reversible FIXED overlay for all nonselected wires","all1691 clocks unchanged","actual routing and full DRC/antenna","full scope connectivity and LVS","original three-corner final STA"]
        save("selected-repair-net-plan.json",result)
    except Exception as exc:
        save("failure.json",dict(error=repr(exc),traceback=traceback.format_exc()));raise
if __name__=="__main__":main()
