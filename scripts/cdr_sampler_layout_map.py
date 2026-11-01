#!/usr/bin/env python3
"""Join authenticated complete native-derived inventories; no GDS processing."""
import argparse,ast,base64,copy,hashlib,json,os,pathlib,subprocess,traceback
from decimal import Decimal
ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=ROOT/"cloud-sampler-layout-map"
FLAGS=dict(native_payloads_acquired=False,native_geometry_processed=False,layout_changed=False,physical_acceptance=False,full_phy_accepted=False,final_timing_complete=False)
def require(ok,msg):
    if not ok:raise ValueError(msg)
def encode(x):return(json.dumps(x,sort_keys=True,indent=2,allow_nan=False)+"\n").encode()
def sha(x):return hashlib.sha256(x).hexdigest()
def fetch(pin):
    prefix="repos/Melihakbulut221/nssoc/"
    def api(path):
        r=subprocess.run(["gh","api",prefix+path],capture_output=True,text=True,timeout=120)
        require(r.returncode==0,r.stderr[:2000]);return json.loads(r.stdout)
    meta=api("contents/"+pin["path"]+"?ref="+pin["source"])
    blob=meta if meta.get("content")else api("git/blobs/"+meta["sha"])
    raw=base64.b64decode(blob["content"])
    require(len(raw)==pin["bytes"]and sha(raw)==pin["sha256"],"exact immutable derived input")
    return raw
def canonical_model(name):
    return {"npn13G2":"npn13g2"}.get(name,name)
EXTRA={
 227:("3.6u","1.8u","1u",("$450",88),("$787",139)),
 228:("21.6u","10.8u","1u",("$787",139),("avss",23)),
 229:("3.6u","1.8u","1u",("$449",87),("$788",140)),
 230:("21.6u","10.8u","1u",("$788",140),("avss",23)),
 238:("3.6u","1.8u","1u",("$623",118),("$869",152)),
 239:("21.6u","10.8u","1u",("$869",152),("avss",23)),
 240:("3.6u","1.8u","1u",("$622",117),("$870",153)),
 241:("21.6u","10.8u","1u",("$870",153),("avss",23)),
}
def join(loc,inventory,composition,targets,counts=(500,4928)):
    records=loc["devices"];physical={r["native_id"]:r for r in records}
    require(len(records)==len(physical)==counts[0],"complete unique physical device census")
    electrical={r["native_id"]:r for r in composition["device_records"]}
    require(len(electrical)==len(composition["device_records"])==counts[0]and set(electrical)==set(physical),"complete matching electrical device census")
    bypath={r["path"]:r for r in inventory}
    require(len(bypath)==len(inventory)==counts[1],"complete unique physical instance inventory")
    used=set()
    for ident,row in physical.items():
        cell=row["pcell"];path=cell["path"]
        require(path in bypath and cell==bypath[path]and path not in used,"exact unique device enclosure")
        used.add(path);other=electrical[ident]
        require(canonical_model(row["model"])==other["model"],"same model with explicit native npn13G2 alias only")
        p={t["name"]:(t["net"],t["native_cluster"])for t in row["terminals"]}
        e={t["terminal"]:(t["native_net"],t["native_cluster"])for t in other["terminals"]}
        require(len(p)==len(row["terminals"])and len(e)==len(other["terminals"])and p==e,"all original terminal partitions")
    selected=[]
    require(set(targets)<=set(physical),"all requested physical devices")
    selected_paths={physical[i]["pcell"]["path"]:i for i in targets}
    all_device_paths={r["pcell"]["path"]:r["native_id"]for r in records}
    for ident,(old,new,width,first,second)in sorted(targets.items()):
        p=physical[ident];e=electrical[ident]
        require(p["model"]=="rppd"and e["instance"]=="XD"+format(ident,"04d"),"target resistor identity")
        require(e["parameters"]==dict(b="0",l=old,m="1",ps="0u",sw_et="1",w=width),"exact original electrical resistor")
        require(Decimal(str(p["parameters"]["l"]))==Decimal(old[:-1])and Decimal(str(p["parameters"]["w"]))==Decimal(width[:-1]),"exact physical length and width")
        terms={t["name"]:(t["net"],t["native_cluster"])for t in p["terminals"]}
        require(terms==dict(rppd_1=first,rppd_2=second,rppd_sub=("$1",1)),"exact requested resistor terminals")
        others=[dict(native_id=r["native_id"],path=r["pcell"]["path"])for r in records if r["pcell"]["cell"]==p["pcell"]["cell"]and r["native_id"]not in targets]
        all_users=[dict(path=r["path"],native_id=all_device_paths.get(r["path"]))for r in inventory if r["cell"]==p["pcell"]["cell"]]
        untargeted_instances=[r for r in all_users if r["path"]not in selected_paths]
        targeted_users=[dict(**r,requested_l=targets[selected_paths[r["path"]]][1],width=targets[selected_paths[r["path"]]][2])for r in all_users if r["path"]in selected_paths]
        conflicts=len({(r["requested_l"],r["width"])for r in targeted_users})>1
        selected.append(dict(native_id=ident,pcell=p["pcell"],terminals=p["terminals"],old_l=old,requested_l=new,width=width,
            untargeted_users_of_same_cell=others,all_instance_users_of_same_cell=all_users,
            untargeted_instance_users_of_same_cell=untargeted_instances,targeted_instance_users_of_same_cell=targeted_users,
            conflicting_requested_dimensions=conflicts,private_cell_required=bool(untargeted_instances)or conflicts))
    return dict(status="COMPLETE_DERIVED_NATIVE_INSTANCE_MAP",verified_devices=counts[0],verified_instance_inventory=counts[1],selected=selected,**FLAGS)
def extended_targets(baseline,candidate,extra):
    require(not(set(baseline)&set(extra)),"additional targets do not replace baseline targets")
    require(candidate==(baseline|extra),"exact retained baseline plus additional targets")
def mixed_targets(baseline,candidate,extra,restored):
    require(set(restored)<=set(baseline),"all restored loads belong to baseline")
    retained={k:v for k,v in baseline.items()if k not in restored}
    extended_targets(retained,candidate,extra)
def literal_targets(raw):
    nodes=[n for n in ast.parse(raw).body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=="TARGETS"for t in n.targets)]
    require(len(nodes)==1,"one literal candidate target definition")
    return ast.literal_eval(nodes[0].value)
def fixture():
    inv=[];rows=[];elec=[]
    for ident,cell in [(1,"shared"),(2,"shared"),(3,"other")]:
        p=dict(cell=cell,path="top/"+str(ident),transform="r0",bbox="fixture",pins=[]);inv.append(p)
        terms=[dict(name=k,net=n,native_cluster=i)for k,n,i in [("rppd_1","avdd",16),("rppd_2","out"+str(ident),20+ident),("rppd_sub","$1",1)]]
        rows.append(dict(native_id=ident,model="rppd",parameters=dict(l=2.6,w=32.),pcell=copy.deepcopy(p),terminals=terms))
        elec.append(dict(native_id=ident,instance="XD"+format(ident,"04d"),model="rppd",parameters=dict(b="0",l="2.6u",m="1",ps="0u",sw_et="1",w="32u"),terminals=[dict(terminal=t["name"],native_net=t["net"],native_cluster=t["native_cluster"])for t in terms]))
    rows[2].update(model="npn13G2",parameters=dict(Nx=2,we=.07,le=.9),terminals=[dict(name=k,net=n,native_cluster=i)for k,n,i in [("C","c3",31),("B","b3",32),("E","e3",33),("S","$1",1)]])
    elec[2].update(model="npn13g2",parameters=dict(nx="2",we=".07u",le=".9u"),terminals=[dict(terminal=t["name"],native_net=t["net"],native_cluster=t["native_cluster"])for t in rows[2]["terminals"]])
    return dict(devices=rows),inv,dict(device_records=elec),{1:("2.6u","1.5u","32u",("avdd",16),("out1",21))}
def controls():
    args=fixture();p=join(*args,counts=(3,3))
    require(p["selected"][0]["private_cell_required"]and p["selected"][0]["untargeted_users_of_same_cell"]==[dict(native_id=2,path="top/2")],"shared-cell edit cannot affect unselected device")
    mutations=[
      ("missing device",lambda a:a[0]["devices"].pop()),
      ("duplicate physical identity",lambda a:a[0]["devices"][1].__setitem__("native_id",1)),
      ("missing instance",lambda a:a[1].pop()),
      ("wrong shared cell",lambda a:a[0]["devices"][0]["pcell"].__setitem__("cell","wrong")),
      ("wrong native terminal",lambda a:a[0]["devices"][0]["terminals"][0].__setitem__("native_cluster",99)),
      ("different native HBT variant",lambda a:a[0]["devices"][2].__setitem__("model","npn13G2l")),
      ("wrong physical length",lambda a:a[0]["devices"][0]["parameters"].__setitem__("l",2.5)),
      ("wrong electrical width",lambda a:a[2]["device_records"][0]["parameters"].__setitem__("w","16u")),
      ("wrong selected terminal",lambda a:a[3].__setitem__(1,("2.6u","1.5u","32u",("avdd",16),("out2",22)))),
    ];refused=[]
    for name,change in mutations:
        a=copy.deepcopy(args);change(a)
        try:join(*a,counts=(3,3))
        except ValueError:refused.append(name)
        else:raise AssertionError("accepted "+name)
    # A physical instance need not be represented by an extracted device.
    a=copy.deepcopy(args);a[1].append(dict(a[1][0],path="top/unbound"))
    observed=join(*a,counts=(3,4))["selected"][0]
    require(dict(path="top/unbound",native_id=None)in observed["untargeted_instance_users_of_same_cell"]and observed["private_cell_required"],"all-instance shared definition guard")
    a=copy.deepcopy(args);a[3][2]=("2.6u","1.8u","32u",("avdd",16),("out2",22))
    observed=join(*a,counts=(3,3))["selected"]
    require(all(r["conflicting_requested_dimensions"]and r["private_cell_required"]and not r["untargeted_instance_users_of_same_cell"]for r in observed),"conflicting selected users need private geometry")
    left=args[3];extra={2:("2.6u","1.8u","32u",("avdd",16),("out2",22))};right=left|extra
    extended_targets(left,right,extra)
    for name,bad in [
        ("changed original target",dict(right)|{1:("2.6u","2.0u","32u",("avdd",16),("out1",21))}),
        ("missing divider target",dict(left)),
        ("wrong divider terminal",dict(right)|{2:("2.6u","1.8u","32u",("avdd",16),("wrong",99))}),
        ("unexpected target",dict(right)|{3:right[2]}),
    ]:
        try:extended_targets(left,bad,extra)
        except ValueError:refused.append(name)
        else:raise AssertionError("accepted "+name)
    # Restored loads must be removed; retained targets must be byte-equivalent.
    original={1:left[1],3:left[1]};new={1:left[1]}|extra
    mixed_targets(original,new,extra,{3})
    for name,bad in [("restored target still changed",new|{3:original[3]}),
                     ("retained target dropped",extra),
                     ("retained target altered",new|{1:("2.6u","2.0u","32u",("avdd",16),("out1",21))})]:
        try:mixed_targets(original,bad,extra,{3})
        except ValueError:refused.append(name)
        else:raise AssertionError("accepted "+name)
    return dict(synthetic_only=True,refused=refused,positive_shared_cell_fixture=True,
        positive_unbound_physical_instance_fixture=True,positive_conflicting_target_geometry_fixture=True,**FLAGS)
def main():
    global OUT
    p=argparse.ArgumentParser();p.add_argument("--controls",action="store_true");args=p.parse_args()
    require(os.environ.get("GITHUB_ACTIONS")=="true"and os.environ.get("GITHUB_RUN_ATTEMPT")=="1"and os.environ.get("GITHUB_REPOSITORY")=="Melihakbulut221/nssoc","single cloud execution")
    cfg=json.loads((ROOT/"scripts/cdr-sampler-layout-map-inputs.json").read_bytes())
    for path,pin in cfg["source_files"].items():
        raw=(ROOT/path).read_bytes();require(dict(bytes=len(raw),sha256=sha(raw))==pin,"exact source "+path)
    if args.controls:OUT=ROOT/"cloud-sampler-layout-map-controls"
    OUT.mkdir(exist_ok=False)
    c=controls();(OUT/"controls.json").write_bytes(encode(c));require(len(c["refused"])==16,"all corruption refusals")
    if args.controls:print(json.dumps(c));return
    cfg=json.loads((ROOT/"scripts/cdr-sampler-layout-map-inputs.json").read_bytes())
    raw={name:fetch(pin)for name,pin in cfg["inputs"].items()}
    for name,value in raw.items():(OUT/name).write_bytes(value)
    targets=literal_targets(raw["candidate.py"]);baseline=literal_targets(raw["baseline-q15.py"])
    require(set(baseline)=={175,176,182,183,184,185,191,194,202,205,212,214,220,221,222,223},"exact retained sixteen baseline targets")
    restored={175,176,212,214}
    mixed_targets(baseline,targets,EXTRA,restored)
    require(len(targets)==20,"exact20 candidate devices")
    loc=json.loads(raw["locations.json"])
    require(loc["status"]=="PASS_ALL_500_DEVICES_HAVE_UNIQUE_PHYSICAL_PCELL_ENCLOSURE","original qualified enclosure report")
    inputs=loc["inputs"]
    for suffix,expected in [(".gds",cfg["baseline_gds_sha256"]),(".lvsdb",cfg["baseline_lvsdb_sha256"]),("pcell-inventory01.json",sha(raw["inventory.json"]))]:
        matches=[value for name,value in inputs.items()if name.endswith(suffix)]
        require(matches==[expected],"same exact native geometry and inventory provenance")
    result=join(loc,json.loads(raw["inventory.json"]),json.loads(raw["composition.json"]),targets)
    result["candidate_source"]=cfg["inputs"]["candidate.py"]["source"]
    result["retained_q15_targets"]=sorted(set(baseline)-restored)
    result["restored_original_cd_output_ids"]=sorted(restored)
    result["additional_ac_divider_targets"]=sorted(EXTRA)
    result["all_instance_sharing_audited"]=True
    result.update(source=os.environ["GITHUB_SHA"],run=int(os.environ["GITHUB_RUN_ID"]),baseline_gds_sha256=cfg["baseline_gds_sha256"],baseline_lvsdb_sha256=cfg["baseline_lvsdb_sha256"])
    (OUT/"result.json").write_bytes(encode(result))
    print(json.dumps(dict(status=result["status"],selected=[dict(native_id=r["native_id"],cell=r["pcell"]["cell"],private_cell_required=r["private_cell_required"],untargeted_users=r["untargeted_users_of_same_cell"])for r in result["selected"]]),sort_keys=True))
if __name__=="__main__":
    try:main()
    except BaseException:
        OUT.mkdir(exist_ok=True);(OUT/"failure.txt").write_text(traceback.format_exc());raise
