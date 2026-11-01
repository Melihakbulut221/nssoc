#!/usr/bin/env python3
"""Join existing derived physical device and waveform records on GitHub only.
Net membership establishes connectivity, not equal voltage across distributed RC.
No native acquisition, simulator, geometry modification or acceptance claim.
"""
import base64, collections, copy, hashlib, json, os, pathlib, subprocess, traceback
OUT=pathlib.Path("cloud-cdr-topology")
def require(ok,reason):
    if not ok: raise ValueError(reason)
def encoded(value):
    return (json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+"\n").encode()
def save(name,value):
    p=OUT/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(encoded(value))
def api(path):
    p=subprocess.run(["gh","api","repos/Melihakbulut221/nssoc/"+path],capture_output=True,text=True)
    require(p.returncode==0,p.stderr[:2000])
    return json.loads(p.stdout)
def acquire(pin):
    d=api("contents/"+pin["path"]+"?ref="+pin["source"])
    if not d.get("content"):d=api("git/blobs/"+d["sha"])
    raw=base64.b64decode(d["content"])
    require(len(raw)==pin["bytes"] and hashlib.sha256(raw).hexdigest()==pin["sha256"],"input byte identity")
    return raw
def join(c,p,m,w):
    records=c["device_records"]
    require(len(records)==500,"500 physical devices")
    require(len({d["native_id"] for d in records})==500,"unique native ids")
    require(len({d["instance"].lower() for d in records})==500,"unique instances")
    counts=collections.Counter(d["model"] for d in records)
    require(counts==dict(npn13g2=124,sg13_lv_nmos=50,rppd=98,cap_cmim=7,ptap1=221),"complete device census")
    ext={n:("0" if n in ("avss","sub","wire_cref") else n) for n in c["interface"]}
    def probe(n):return ext.get(n,"xpd."+n.lower())
    groups=m["binding"]["groups"]
    flat={n:d for g in groups.values() for n,d in g.items()}
    require(len(flat)==500 and sum(map(len,groups.values()))==500,"complete bound census")
    logical={};net_alias=collections.defaultdict(set)
    for a in p["anchors"]:
        pair=(a["native_cluster"],a["native_name"])
        require(a["logical_net"] not in logical or logical[a["logical_net"]]==pair,"ambiguous logical anchor")
        logical[a["logical_net"]]=pair;net_alias[pair].add(a["logical_net"])
    require(len(logical)==51,"51 logical nets")
    index={};adj=collections.defaultdict(list)
    for d in records:
        name="xpd."+d["instance"].lower()
        require(name in groups[d["model"]],"device group identity")
        bound=flat[name]
        require(bound["native_id"]==d["native_id"],"native id binding")
        require(bound["nodes"]==[probe(t["node"]) for t in d["terminals"]],"ordered terminal probe binding")
        require(bound["parameters"]==d["parameters"],"device parameter binding")
        terminals=[]
        for t in d["terminals"]:
            pair=(t["native_cluster"],t["native_net"])
            row=dict(t,probe=probe(t["node"]),logical_aliases=sorted(net_alias[pair]))
            terminals.append(row)
            adj[pair].append(dict(device=name,model=d["model"],terminal=t["terminal"],probe=row["probe"]))
        index[name]=dict(name=name,native_id=d["native_id"],model=d["model"],parameters=d["parameters"],terminals=terminals)
    hbt=groups["npn13g2"]
    require(m["devices"]==hbt,"measurement HBT identity")
    require({r["name"] for r in w["hbt"]}==set(hbt) and len(w["hbt"])==124,"wave HBT census")
    for row in w["hbt"]:
        require(row["native_id"]==hbt[row["name"]]["native_id"],"wave native identity")
        require(row["original_metrics_reproduced"] is True,"original HBT metrics")
    for alias,target in m["binding"]["aliases"].items():
        logical_name=alias.removeprefix("xpd.")
        require(logical_name in logical,"alias logical name")
        candidates=[t for d in index.values() for t in d["terminals"] if t["probe"]==target]
        require(candidates and all((t["native_cluster"],t["native_net"])==logical[logical_name] for t in candidates),"alias native topology")
    require(w["all124HBT_metrics_reproduced"] is True and w["all6stage_and1530_bit_delays_reproduced"] is True and w["original_phase_and_VI_reproduced"] is True,"complete original reproduction")
    events=w["failing_hbt_events"]
    require({e["native_id"] for e in events}=={61,62,115,116} and len(events)==4,"original four failing devices")
    targets=[]
    for e in events:
        name=e["name"];d=index[name]
        require(e["nodes"]==hbt[name]["nodes"] and e["native_id"]==d["native_id"],"event terminal identity")
        require(e["nx"]==int(d["parameters"]["nx"]) and e["original_gate_v"]==.4 and e["vce_v"]<.4,"original event gate")
        connected={}
        for t in d["terminals"]:
            if t["terminal"]=="S":continue
            key=(t["native_cluster"],t["native_net"])
            connected[t["terminal"]]=dict(native_cluster=key[0],native_net=key[1],logical_aliases=sorted(net_alias[key]),members=adj[key])
        neighbors={r["device"] for g in connected.values() for r in g["members"]}
        # Preserve direct devices, then traverse one extra hop only through signal nets.
        second=set()
        for n in neighbors:
            for t in index[n]["terminals"]:
                key=(t["native_cluster"],t["native_net"])
                if t["terminal"] in ("S","B") and index[n]["model"] in ("ptap1","sg13_lv_nmos"):continue
                if set(net_alias[key]) & {"avdd","avss","sub","wire_cref"}:continue
                second.update(x["device"] for x in adj[key])
        targets.append(dict(device=d,event=e,terminal_membership=connected,direct_devices=sorted(neighbors),second_hop_devices=sorted(second),neighborhood=[index[n] for n in sorted(neighbors|second)]))
    return dict(status="COMPLETE_DERIVED_TOPOLOGY_JOIN",counts=dict(counts),logical_net_count=len(logical),device_index=index,targets=targets,
        source=w["source"],original_run=w["run"],native_simulation_rerun=False,physical_acceptance=False,full_phy_accepted=False,final_timing_complete=False,
        interpretation="Connectivity is a native-net partition only; distinct terminal nodes and their measured voltages remain distinct. No RC is removed or shorted.")
def controls(inputs):
    c,p,m,w=inputs
    passed=[]
    mutations=[
        ("duplicate device",0,lambda x:x["device_records"].__setitem__(1,copy.deepcopy(x["device_records"][0]))),
        ("wrong bound id",2,lambda x:x["devices"]["xpd.xd0061"].__setitem__("native_id",999)),
        ("wrong bound terminal",2,lambda x:x["binding"]["groups"]["npn13g2"]["xpd.xd0061"]["nodes"].__setitem__(0,"xpd.wrong")),
        ("wrong parameter",0,lambda x:x["device_records"][60]["parameters"].__setitem__("nx","999")),
        ("wrong event node",3,lambda x:x["failing_hbt_events"][0]["nodes"].__setitem__(0,"xpd.wrong")),
        ("relaxed original gate",3,lambda x:x["failing_hbt_events"][0].__setitem__("original_gate_v",.3)),
        ("missing waveform HBT",3,lambda x:x["hbt"].pop()),
        ("ambiguous plane alias",1,lambda x:x["anchors"].append(dict(x["anchors"][0],native_cluster=999999))),
        ("wrong alias",2,lambda x:x["binding"]["aliases"].__setitem__("xpd.aqp","xpd.w_t061_c")),
    ]
    for label,which,mutate in mutations:
        altered=copy.deepcopy(inputs);mutate(altered[which])
        try:join(*altered)
        except ValueError as e:passed.append(dict(control=label,rejected=True,reason=str(e)))
        else:raise AssertionError("control accepted: "+label)
    return passed
def main():
    require(os.environ.get("GITHUB_ACTIONS")=="true","GitHub runner only")
    require(os.environ.get("GITHUB_RUN_ATTEMPT")=="1","single attempt")
    OUT.mkdir(exist_ok=False)
    cfg=json.loads(pathlib.Path("scripts/cdr-loaded-topology-inputs.json").read_bytes())
    save("context.json",dict(source=os.environ["GITHUB_SHA"],run=os.environ["GITHUB_RUN_ID"],attempt=1,inputs=cfg["inputs"]))
    values={}
    for name,pin in cfg["inputs"].items():
        raw=acquire(pin);path=OUT/"inputs"/name;path.parent.mkdir(exist_ok=True);path.write_bytes(raw);values[name]=json.loads(raw)
    inputs=[values[n] for n in ("composition.json","planes.json","measurement.json","diagnostic.json")]
    result=join(*inputs)
    save("controls.json",controls(inputs))
    save("result.json",result)
    summary=dict(status=result["status"],counts=result["counts"],controls_passed=9,full_phy_accepted=False,
        targets=[dict(name=t["device"]["name"],native_id=t["device"]["native_id"],vce_v=t["event"]["vce_v"],terminals=t["device"]["terminals"],terminal_membership=t["terminal_membership"],direct_devices=t["direct_devices"]) for t in result["targets"]])
    save("summary.json",summary)
    print(json.dumps(summary,sort_keys=True))
if __name__=="__main__":
    try:main()
    except Exception:
        OUT.mkdir(exist_ok=True);(OUT/"failure.txt").write_text(traceback.format_exc());raise
