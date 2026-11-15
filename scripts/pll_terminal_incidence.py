import os,json,hashlib,subprocess,base64
from pathlib import Path
import compare_cloud_routed_endpoints as reports
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/"pll-terminal-incidence";OUT.mkdir();reports.OUT=OUT
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def api(p):return json.loads(subprocess.check_output(["gh","api",p],timeout=180))
r=dict(source=os.environ["GITHUB_SHA"],status="RUNNING",native_query_validated=False,transient_run=False,acquisition_accepted=False,full_phy_accepted=False)
def save():(OUT/"readback.json").write_text(json.dumps(r,indent=2)+"\n")
save()
try:
 assert os.environ["GITHUB_ACTIONS"]=="true" and os.environ["GITHUB_RUN_ATTEMPT"]=="1"
 assert os.environ["GITHUB_REF"]=="refs/heads/codex/pll-terminal-incidence"
 run=api("repos/Melihakbulut221/nssoc/actions/runs/39920519407")
 assert run["head_sha"]=="efe9885e87bce9eb82a1c6decc4ed85ab2d65160" and run["conclusion"]=="success"
 names=["candidate-circuit.cir","terminal-instrumentation.json","composition/composition.json","composition/pll845-mim-wire.spice"]+["model-sources/models/models/"+n for n in ["sg13g2_hbt_mod.lib","cornerHBT.lib","sg13g2_hbt_stat.lib","sg13g2_hbt_mod_mismatch.lib"]]
 prepared,proof=reports.restore_report("pll-rhi120-c8-preparation",39920519407,"63c6b8d34ecf277dce223427c72bdb943ed0dc010c80f496d8feb33f268f94dd","92a85edae348ad4e3ebfb62b372f627dde16ef9aadb4fcb55cedc1422a9d4657",OUT/"prepared",names)
 assert prepared["source_head"]==run["head_sha"] and prepared["sources_unchanged"]
 for n in names:assert sha(OUT/"prepared"/n)==prepared["outputs"][n]
 model=OUT/"prepared/model-sources/models/models/sg13g2_hbt_mod.lib"
 assert sha(model)=="ae9288f885dd30fab24b07ed1e7e02e69eac9154022a0a6da576985183b0bd79"
 contract=json.loads((OUT/"prepared/composition/composition.json").read_text())
 devices=[d for d in contract["device_records"]if d["native_id"]in [391,392,393,394,395,396,400]]
 assert len(devices)==7 and len({d["native_id"]for d in devices})==7
 r.update(preparation=proof,devices=devices,model_sha256=sha(model),model_lines={n:[dict(line=i,text=l)for i,l in enumerate((OUT/"prepared"/n).read_bytes().decode("latin-1").splitlines(),1)]for n in names if n.endswith(".lib")},original_circuit_sha256=sha(OUT/"prepared/candidate-circuit.cir"))
 pins={"vbic.c":"e6dd50fd8f07c2c41cc7d7de86895014b175f75d97768357cde651b5ed47e903","vbicask.c":"92a12d2cc99505427945fec0e984e3f56b9ebd0b2b61d811af3b4405170f2b51","vbicdefs.h":"0185f8162e02de0cf9c332bbc827d6e43af9a1c494e8e86642b2d7d8ec57ef9b","vbicload.c":"ae2fca22ca7178bce26f31b4e433307945cafa9d8661d55007eed8fc096ff866"}
 for n,digest in pins.items():
  b=base64.b64decode(api("repos/ngspice/ngspice/contents/src/spicelib/devices/vbic/"+n+"?ref=a80f6e3e95d51534905b1f23410a951802666656")["content"]);assert hashlib.sha256(b).hexdigest()==digest;(OUT/n).write_bytes(b)
 import build_pcie_local_vco_hybrid_v6 as parser
 cards=parser.statements((OUT/"prepared/composition/pll845-mim-wire.spice").read_text())
 assert sum(c[0].lower()==".subckt"for c in cards)==1 and sum(c[0].lower()==".ends"for c in cards)==1
 elements=[c for c in cards if not c[0].startswith(".")]
 assert all(c[0][0].lower()in ("r","c","x")for c in elements)
 assert len({c[0].lower()for c in elements})==len(elements)
 rows=[]
 for device in devices:
  own=next(c for c in elements if c[0].lower()==device["instance"].lower())
  assert own[-1].lower().startswith("le=") or any(v.lower()=="npn13g2"for v in own)
  for terminal in device["terminals"]:
   if terminal["terminal"]not in ("C","B","E"):continue
   node=terminal["node"];passives=[];others=[]
   for c in elements:
    if c[0][0].lower()in ("r","c"):
     assert len(c)>=4
     if node not in c[1:3]:continue
     assert c[1]!=c[2]
     passives.append(dict(instance=c[0],kind=c[0][0].lower(),positive=c[1],negative=c[2],outward_sign=1 if c[1]==node else -1,card=c))
    elif node in c[1:] and c[0].lower()!=own[0].lower():others.append(c)
   rows.append(dict(device=device["native_id"],terminal=terminal["terminal"],node=node,own_card=own,passive_branches=passives,other_device_cards=others,unique_device_with_explicit_passive_boundary=bool(passives)and not others))
 assert len(rows)==21
 r.update(terminal_incidence=rows,unique_boundaries=sum(x["unique_device_with_explicit_passive_boundary"]for x in rows),
  metal_model_sha256=sha(OUT/"prepared/composition/pll845-mim-wire.spice"),
  proposed_method="For each unique boundary: device current into terminal = negative sum of signed existing native passive currents. Native R/C accessor, orientation and full dynamic KCL still require validation; no ideal shunts or model changes.")
 r.update(upstream_source_pins=pins,status="EXACT_TERMINAL_INCIDENCE_READBACK_REQUIRES_NATIVE_BRANCH_QUERIES",no_parameter_change=True,no_native_execution=True)

except BaseException as e:r.update(status="FAIL_OR_ERROR",error=repr(e));raise
finally:save()
