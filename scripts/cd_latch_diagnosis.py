#!/usr/bin/env python3
"""Derived-only simultaneous C/D latch diagnosis; no wave, model or geometry acquisition."""
import base64,hashlib,json,math,os,pathlib,subprocess
ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=ROOT/"cloud-cd-latch-diagnosis"
CFG="scripts/cd-latch-diagnosis-inputs.json"
GROUPS={
 "d":{"followers":[69,70],"input_buffer":[59,60],"master_data":[54,56],"master_hold":[58,57],
      "slave_data":[53,55],"slave_hold":[51,52],"master_data_clock":[61,62],
      "master_hold_clock":[64,65],"slave_data_clock":[66,68],"slave_hold_clock":[63,67]},
 "c":{"followers":[121,124],"input_buffer":[111,112],"master_data":[106,108],"master_hold":[110,109],
      "slave_data":[105,107],"slave_hold":[103,104],"master_data_clock":[115,116],
      "master_hold_clock":[118,119],"slave_data_clock":[114,120],"slave_hold_clock":[113,117]}}
def need(ok,label):
 if not ok:raise ValueError(label)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def enc(d):return(json.dumps(d,sort_keys=True,indent=2,allow_nan=False)+"\n").encode()
def fetch(pin):
 def api(path):
  p=subprocess.run(["gh","api","repos/Melihakbulut221/nssoc/"+path],capture_output=True,timeout=120)
  need(p.returncode==0,p.stderr.decode()[:2000]);return json.loads(p.stdout)
 d=api("contents/"+pin["path"]+"?ref="+pin["source"])
 b=d if d.get("content")else api("git/blobs/"+d["sha"]);raw=base64.b64decode(b["content"])
 need(len(raw)==pin["bytes"]and sha(raw)==pin["sha256"],"exact immutable derived input")
 return raw
def name(i):return "xpd.xd"+format(i,"04d")
def term(row,t):
 a=[x for x in row["terminals"]if x["terminal"]==t];need(len(a)==1,"unique terminal")
 return a[0]["native_cluster"]
def topology(comp,report):
 rows=comp["device_records"];byid={r["native_id"]:r for r in rows}
 need(len(rows)==len(byid)==500,"complete native500")
 for row in rows:
  if row["model"]!="npn13g2":continue
  d=report["devices"][name(row["native_id"])]
  need(d["nodes"]==["xpd."+t["node"].lower()for t in row["terminals"]]and d["nx"]==int(row["parameters"]["nx"]),"all124 HBT native identities")
 def pins(ids,t):return [term(byid[i],t)for i in ids]
 for tag,g in GROUPS.items():
  need(all(byid[i]["model"]=="npn13g2"for ids in g.values()for i in ids),"HBT roles")
  need(pins(g["followers"],"E")==pins(g["input_buffer"],"B"),"follower to input buffer")
  need(pins(g["input_buffer"],"C")==list(reversed(pins(g["master_data"],"B"))),"inverting input buffer to master")
  need(pins(g["master_data"],"C")==pins(g["slave_data"],"B"),"master to slave data")
  for part in ("master","slave"):
   data=g[part+"_data"];hold=g[part+"_hold"]
   need(pins(data,"C")==pins(hold,"C")and pins(hold,"B")==list(reversed(pins(hold,"C"))),"cross-coupled hold pair")
   for role,clock in ((data,g[part+"_data_clock"]),(hold,g[part+"_hold_clock"])):
    need(len(set(pins(role,"E")+pins(clock,"C")))==1,"actual gated tail connection")
   dc=pins(g[part+"_data_clock"],"B");hc=pins(g[part+"_hold_clock"],"B")
   need(set(dc)==({26}if part=="master"else{27})and set(hc)==({27}if part=="master"else{26}),"actual opposite clock ownership")
  points=report["binding"]["probe_witnesses"]
  need(pins(g["slave_data"],"C")==[points[tag+"qp"]["native_cluster"],points[tag+"qn"]["native_cluster"]],"actual sampled outputs")
 return byid
def clock_connections(rows):
    result={}
    for tag,g in GROUPS.items():
        ids=[i for role,a in g.items()if role.endswith("_clock")for i in a]
        clusters=sorted({term(rows[i],"E")for i in ids})
        traced=[]
        for cluster in clusters:
            neighbors=[dict(record=r,connected_terminals=[t["terminal"]for t in r["terminals"]if t["native_cluster"]==cluster])
                for r in rows.values()if any(t["native_cluster"]==cluster for t in r["terminals"])]
            gates=sorted({t["native_cluster"]for n in neighbors for t in n["record"]["terminals"]if t["terminal"]=="G"})
            gate_neighbors={str(gate):[dict(record=r,connected_terminals=[t["terminal"]for t in r["terminals"]if t["native_cluster"]==gate])
                for r in rows.values()if any(t["native_cluster"]==gate for t in r["terminals"])]for gate in gates}
            traced.append(dict(clock_emitter_cluster=cluster,clock_ids=[i for i in ids if term(rows[i],"E")==cluster],
                complete_direct_neighbors=neighbors,mos_gate_connections=gate_neighbors))
        result[tag]=traced
    return result
def main():
 need(os.environ.get("GITHUB_ACTIONS")=="true"and os.environ.get("GITHUB_RUN_ATTEMPT")=="1","single cloud execution")
 cfg=json.loads((ROOT/CFG).read_bytes())
 for p,pin in cfg["source_files"].items():
  b=(ROOT/p).read_bytes();need(dict(bytes=len(b),sha256=sha(b))==pin,"exact source")
 OUT.mkdir(exist_ok=False);raw={k:fetch(p)for k,p in cfg["inputs"].items()}
 for k,b in raw.items():(OUT/k).write_bytes(b)
 report=json.loads(raw["measurement.json"]);result=json.loads(raw["operating-points.json"]);comp=json.loads(raw["composition.json"])
 need(report["current_context"]==cfg["producer_context"]and report["devices_passed"]is True,"exact original mixed20 nominal case")
 need(result["status"]=="COMPLETE_CANDIDATE_WAVE_HEADROOM_DIAGNOSIS"and result["all124HBT_metrics_reproduced"]and result["all6stage_and1530_bit_delays_reproduced"]and result["original_phase_and_VI_reproduced"],"original full-wave metric reproduction")
 rows=topology(comp,report);events={}
 for tag,groups in GROUPS.items():
  points=result["stage_operating_points"][tag];need(len(points)==2,"both original failure events")
  events[tag]=[]
  for point in points:
   snap=point["all124_hbt"];need(set(snap)==set(report["devices"])and len(snap)==124,"same-time all124 snapshot")
   for n,x in snap.items():
    need(x["native_id"]==report["devices"][n]["native_id"]and x["nodes"]==report["devices"][n]["nodes"]and x["nx"]==report["devices"][n]["nx"],"same-time complete identity")
    v=x["terminal_v"];need(set(v)=={"C","B","E","S"}and all(math.isfinite(z)for z in v.values()),"complete finite terminals")
    need(abs(x["vce_v"]-(v["C"]-v["E"]))<1e-12 and abs(x["vbe_v"]-(v["B"]-v["E"]))<1e-12,"same-time voltage identity")
    need(abs(x["collector_current_per_emitter_a"]-x["collector_current_a"]/x["nx"])<1e-15,"same-time current per emitter")
   group_rows={}
   for role,ids in groups.items():
    pair=[snap[name(i)]for i in ids];a,b=pair
    group_rows[role]=dict(ids=ids,devices=pair,
      first_minus_second_terminal_v={t:a["terminal_v"][t]-b["terminal_v"][t]for t in("C","B","E")},
      total_collector_current_a=sum(x["collector_current_a"]for x in pair),
      first_minus_second_collector_current_a=a["collector_current_a"]-b["collector_current_a"],
      original_alltime_device_checks={name(i):report["device_checks"][name(i)]for i in ids})
   events[tag].append(dict(event=point["event"],signed_margin_v=point["signed_margin_v"],
     observed_clock_v={n:point["observed_nodes_v"][n]for n in("cp","cn")},groups=group_rows))
 out=dict(status="COMPLETE_AUTHENTICATED_CD_LATCH_SNAPSHOTS",source=os.environ["GITHUB_SHA"],run=int(os.environ["GITHUB_RUN_ID"]),
   producer_context=cfg["producer_context"],topology_groups=GROUPS,events=events,clock_emitter_connections=clock_connections(rows),
   current_observation_limit="Only HBT collector currents are captured at these instants; static MOS gate connectivity is not a simultaneous current or causality proof.",
   interpretation="Paired currents and voltages at each original common timestamp. Global extrema remain separate; these observations are not proof that resizing fixes the circuit.",
   native_payloads_acquired=False,native_simulation_rerun=False,gates_changed=False,physical_acceptance=False,full_phy_accepted=False,final_timing_complete=False)
 (OUT/"result.json").write_bytes(enc(out))
 (OUT/"clock-emitter-connections.json").write_bytes(enc(out["clock_emitter_connections"]))
 summary={tag:[dict(event=x["event"],signed_margin_v=x["signed_margin_v"],clock=x["observed_clock_v"],
  groups={n:{k:v for k,v in row.items()if k not in("devices","original_alltime_device_checks")}for n,row in x["groups"].items()})for x in points]for tag,points in events.items()}
 (OUT/"summary.json").write_bytes(enc(summary));print(json.dumps(summary),flush=True)
if __name__=="__main__":main()
