#!/usr/bin/env python3
"""Read-only native LVS cross-reference from loaded-wave IDs to schematic instances."""
import argparse,collections,copy,hashlib,io,json,os,pathlib,subprocess,tarfile,traceback,zipfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=ROOT/"collector-device-map"
CONFIG=ROOT/"scripts/cdr-collector-device-map-inputs.json"
PINS=ROOT/"scripts/cdr-collector-device-map-pins.json"
BRANCH="codex/cdr-collector-device-map"
R="repos/Melihakbulut221/nssoc/"
TOP="nssoc_cdr_pd500_resistor_v59"
CRITICAL={**{n:"npn13g2" for n in (54,56,61,62,106,108,115,116)},**{n:"sg13_lv_nmos"for n in (3,4,5,6,32,33,34,35)}}
CENSUS=dict(npn13g2=124,sg13_lv_nmos=50,rppd=98,cap_cmim=7,ptap1=221)
FLAGS=dict(electrical_accepted=False,full_phy_accepted=False,physical_acceptance=False,final_timing_complete=False,layout_modified=False)
def need(ok,message):
    if not ok:raise ValueError(message)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def enc(v):return (json.dumps(v,sort_keys=True,indent=2,allow_nan=False)+"\n").encode()
def fp(path):
    with path.open("rb")as f:d=hashlib.file_digest(f,"sha256").hexdigest()
    return dict(bytes=path.stat().st_size,sha256=d)
def save(name,value):
    p=OUT/name;p.parent.mkdir(parents=True,exist_ok=True)
    with p.open("xb")as f:f.write(enc(value))
def api(path):return json.loads(subprocess.check_output(["gh","api",R+path],timeout=120))
def guard():
    e=os.environ
    need(e.get("GITHUB_ACTIONS")=="true"and e.get("RUNNER_ENVIRONMENT")=="github-hosted","hosted only")
    need(e["GITHUB_REPOSITORY"]=="Melihakbulut221/nssoc"and e["GITHUB_REF"]=="refs/heads/"+BRANCH,"exact repository and branch")
    need(e["GITHUB_RUN_ATTEMPT"]=="1"and e["GITHUB_EVENT_NAME"]=="workflow_dispatch","first explicit dispatch")
    need(subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip()==e["GITHUB_SHA"],"exact source")
    pins=json.loads(PINS.read_bytes())
    for name,pin in pins.items():
        p=ROOT/name;need(p.is_file()and not p.is_symlink()and fp(p)==pin,"source pin "+name)
    return pins
def validate(rows,count,census,critical):
    need(type(count)is int and count>0 and len(rows)==count,"complete pair census")
    need(all(r["status"]=="Match"for r in rows),"all device pairs matched")
    need(all(type(r["layout"]["id"])is int and r["layout"]["id"]>0 and type(r["schematic"]["id"])is int and r["schematic"]["id"]>0 for r in rows),"positive native IDs")
    need(len({r["layout"]["id"]for r in rows})==len({r["schematic"]["id"]for r in rows})==count,"bijective device IDs")
    need(all(r["layout"]["model"]==r["schematic"]["model"]for r in rows),"same matched primitive model")
    need(dict(collections.Counter(r["layout"]["model"]for r in rows))==census,"complete primitive census")
    need(all(r["schematic"]["expanded_name"]for r in rows),"named schematic source")
    byid={r["layout"]["id"]:r for r in rows}
    need(set(critical)<=set(byid)and all(byid[i]["layout"]["model"]==m for i,m in critical.items()),"all critical primitive identities")
    return byid
def controls():
    a=dict(id=61,model="npn13g2",expanded_name="$61")
    b=dict(id=7,model="npn13g2",expanded_name="SAMPLER.XSEL")
    c=dict(id=3,model="sg13_lv_nmos",expanded_name="$3")
    d=dict(id=8,model="sg13_lv_nmos",expanded_name="SAMPLER.XTAIL")
    fixture=[dict(status="Match",layout=a,schematic=b),dict(status="Match",layout=c,schematic=d)]
    census=dict(npn13g2=1,sg13_lv_nmos=1);critical={61:"npn13g2",3:"sg13_lv_nmos"}
    need(set(validate(fixture,2,census,critical))=={61,3},"valid source-only fixture")
    cases=[(0,"status","Mismatch"),(0,"layout.id",0),(0,"layout.id",True),(1,"layout.id",61),
      (1,"schematic.id",7),(0,"schematic.model","rppd"),(0,"schematic.expanded_name",""),
      (0,"layout.model","rppd"),(0,"layout.id",62)]
    rejected=0
    for index,key,value in cases:
        rows=copy.deepcopy(fixture);target=rows[index];path=key.split(".")
        for k in path[:-1]:target=target[k]
        target[path[-1]]=value
        try:validate(rows,2,census,critical)
        except ValueError:rejected+=1
        else:raise AssertionError(key)
    try:validate(fixture[:-1],2,census,critical)
    except ValueError:rejected+=1
    else:raise AssertionError("partial census")
    need(rejected==10,"all refusal controls")
    save("controls.json",dict(status="PASS_MAPPING_ADMISSION_CONTROLS",negative_controls=rejected,native_executed=False,fixture_only=True,**FLAGS))
def acquire(cfg):
    p=cfg["physical"];run=api("actions/runs/"+str(p["run"]));rel=api("releases/"+str(p["release"]))
    need(run["status"]=="completed"and run["conclusion"]=="success"and run["head_sha"]==p["source"]and run["run_attempt"]==1,"actual successful physical producer")
    need(rel["target_commitish"]==p["source"]and rel["tag_name"]==p["tag"],"physical release identity")
    need(api("git/ref/tags/"+p["tag"])["object"]["sha"]==p["source"],"physical source tag")
    assets={a["name"]:a for a in rel["assets"]};need(set(assets)==set(p["assets"]),"complete immutable release")
    work=pathlib.Path(os.environ["RUNNER_TEMP"])/("collector-device-map-"+os.environ["GITHUB_RUN_ID"])
    work.mkdir();paths={}
    for name,pin in p["assets"].items():
        a=assets[name];need(a["id"]==pin["id"]and a["size"]==pin["bytes"]and a["digest"]=="sha256:"+pin["sha256"],"asset metadata")
        target=work/name
        with target.open("xb")as f:subprocess.run(["gh","api",R+"releases/assets/"+str(pin["id"]),"-H","Accept: application/octet-stream"],stdout=f,check=True,timeout=300)
        need(fp(target)=={k:pin[k]for k in ("bytes","sha256")},"complete asset bytes")
        paths[name]=target
    index=json.loads(paths["complete-output-index.json"].read_bytes());need(index==p["index"],"complete exact index")
    selected=set(cfg["selected"]);observed={};inputs={}
    with tarfile.open(paths["native-physical.tar.gz"],"r|gz")as tar:
        for m in tar:
            parts=pathlib.PurePosixPath(m.name).parts
            need(parts and parts[0]=="wire-shortcuts-physical"and not m.name.startswith("/")and ".."not in parts and m.isfile(),"regular contained archive member")
            name="/".join(parts[1:])
            need(name in index["files"]and name not in observed and m.size==index["files"][name]["bytes"],"unique indexed member")
            h=hashlib.sha256();count=0;dest=None
            if name in selected:
                target=work/"selected"/name;target.parent.mkdir(parents=True,exist_ok=True);dest=target.open("xb");inputs[name]=target
            try:
                source=tar.extractfile(m)
                for data in iter(lambda:source.read(4*1024**2),b""):
                    h.update(data);count+=len(data)
                    if dest is not None:dest.write(data)
            finally:
                if dest is not None:dest.close()
            observed[name]=dict(bytes=count,sha256=h.hexdigest())
            need(observed[name]==index["files"][name],"complete member bytes")
    need(observed==index["files"]and set(inputs)==selected,"all producer material authenticated")
    q=json.loads(inputs["physical-qualification.json"].read_bytes())
    need(q["status"]=="PASS_COLLECTOR_VIA2_GDS_FULL560_DRC_DEEP_FLAT_LVS13","qualified current geometry")
    need(q["gds"]==cfg["candidate"],"exact loaded candidate GDS")
    save("acquisition.json",dict(physical=p,authenticated_members=observed,selected=sorted(selected),native_payloads_cloud_only=True))
    return inputs
def device_row(device):
    dc=device.device_class()
    return dict(id=device.id(),name=device.name,expanded_name=device.expanded_name(),model=dc.name.lower(),
      parameters={p.name:device.parameter(p.id())for p in dc.parameter_definitions()},
      terminals={t.name:dict(id=device.net_for_terminal(t.id()).id(),name=device.net_for_terminal(t.id()).name,expanded_name=device.net_for_terminal(t.id()).expanded_name(),cluster=device.net_for_terminal(t.id()).cluster_id)for t in dc.terminal_definitions()})
def native_map(cfg,inputs):
    import klayout.db as db
    audit=json.loads(inputs["physical/lvs_flat/audit.json"].read_bytes())
    need(audit["status"]=="PASS within comparison scope"and not audit["reasons"]and not audit["extraction_diagnostics"],"actual flat LVS clean audit")
    log=inputs["physical/lvs_flat/deck.log"].read_text()
    need("INFO : Congratulations! Netlists match."in log and "ERROR : Netlists don't match"not in log,"original explicit comparison verdict")
    lvs=db.LayoutVsSchematic();lvs.read(str(inputs["physical/lvs_flat/result.lvsdb"]))
    need(not list(lvs.each_log_entry()),"no native extraction diagnostics")
    xref=lvs.xref();need(xref is not None,"native comparison cross-reference")
    circuits=list(xref.each_circuit_pair());need(len(circuits)==1,"one flat native circuit pair")
    pair=circuits[0];left,right=pair.first(),pair.second()
    need(str(pair.status())=="Match"and left is not None and right is not None,"matching top")
    need(left.name==TOP and right.name.casefold()==TOP.casefold(),"exact top identities")
    need(left.pin_count()==right.pin_count()==25 and not list(left.each_subcircuit())and not list(right.each_subcircuit()),"flat25port actual circuits")
    need(sum(1 for _ in left.each_device())==sum(1 for _ in right.each_device())==500,"both full500device circuits")
    rows=[]
    for pair in xref.each_device_pair(circuits[0]):
        a,b=pair.first(),pair.second();need(a is not None and b is not None,"no unmatched primitive")
        need(xref.other_device_for(a).id()==b.id()and xref.other_device_for(b).id()==a.id(),"bidirectional native cross-reference")
        rows.append(dict(status=str(pair.status()),layout=device_row(a),schematic=device_row(b)))
    byid=validate(rows,500,CENSUS,CRITICAL)
    # IDs originate in this exact LVS database in the unchanged canonical planes extractor.
    # The loaded model's ID binding is verified from the independently pinned derived planes.
    zraw=subprocess.check_output(["gh","api",R+"actions/artifacts/"+str(cfg["planes"]["artifact"])+"/zip"],timeout=300)
    need(dict(bytes=len(zraw),sha256=sha(zraw))==cfg["planes"]["archive"],"actual freshRC derived archive")
    z=zipfile.ZipFile(io.BytesIO(zraw));need(len(z.namelist())==len(set(z.namelist())),"unique derived members")
    raw=z.read(cfg["planes"]["member"]);need(dict(bytes=len(raw),sha256=sha(raw))==cfg["planes"]["pin"],"actual loaded native terminal metadata")
    planes=json.loads(raw);actual=[]
    for row in rows:
        for name,t in row["layout"]["terminals"].items():
            actual.append(dict(device=row["layout"]["id"],model=row["layout"]["model"],terminal=name,native_cluster=t["cluster"],native_name=t["name"]))
    key=lambda x:(x["device"],x["model"],x["terminal"])
    need(len(actual)==1446 and sorted(actual,key=key)==sorted(planes["native_terminals"],key=key),"all1446 actual loaded native terminal identities")
    refs=[v for k,v in planes["inputs"].items()if k.endswith("/parent/physical/lvs_flat/result.lvsdb")]
    need(len(refs)==1 and refs[0]==fp(inputs["physical/lvs_flat/result.lvsdb"])["sha256"],"actual loaded planes use exact current LVS database")
    comp_raw=z.read("mim/composition/composition.json")
    need(dict(bytes=len(comp_raw),sha256=sha(comp_raw))==cfg["composition"],"exact actual loaded composition")
    composition=json.loads(comp_raw)
    records=composition["device_records"]
    need(len(records)==500 and len({v["native_id"]for v in records})==500 and {v["native_id"]for v in records}==set(byid),"all loaded device IDs")
    for record in records:
        row=byid[record["native_id"]]
        need(record["model"]==row["layout"]["model"],"loaded primitive model identity")
        terms=row["layout"]["terminals"]
        need(len(record["terminals"])==len(terms)and {t["terminal"]for t in record["terminals"]}==set(terms),"all loaded terminals")
        for terminal in record["terminals"]:
            actual=terms[terminal["terminal"]]
            need(terminal["native_cluster"]==actual["cluster"]and terminal["native_net"]==actual["expanded_name"],"exact loaded net identity")
        row["loaded_instance"]=record["instance"]
        row["loaded_parameters"]=record["parameters"]
    save("device-correspondence.json",dict(status="OBSERVED_FULL500_LVS_SCHEMATIC_CORRESPONDENCE",source_run=cfg["physical"]["run"],
      loaded_run=41441047354,canonical_run=41438707959,fresh_rc_run=41439516945,klayout_version=__import__("importlib.metadata",fromlist=["version"]).version("klayout"),
      circuit=dict(layout=left.name,schematic=right.name,ports=25),native_terminals=1446,counts=CENSUS,
      critical={str(i):byid[i]for i in sorted(CRITICAL)},pairs=rows,
      symmetric_devices_may_have_equivalent_schematic_pairings=True,**FLAGS))
    for name,p in inputs.items():need(fp(p)==cfg["physical"]["index"]["files"][name],"native inputs unchanged")
def main():
    pins=guard();OUT.mkdir()
    parser=argparse.ArgumentParser();parser.add_argument("--controls",action="store_true");args=parser.parse_args()
    try:
        if args.controls:controls()
        else:
            cfg=json.loads(CONFIG.read_bytes());inputs=acquire(cfg);native_map(cfg,inputs)
        save("result.json",dict(status="PASS_SOURCE_CONTROLS"if args.controls else"COMPLETE_NATIVE_SCHEMATIC_IDENTITY_OBSERVATION",native_executed=not args.controls,**FLAGS))
    except BaseException as exc:
        save("failure.json",dict(error=repr(exc),traceback=traceback.format_exc(),**FLAGS))
        raise
    finally:
        need(guard()==pins,"sources unchanged")
if __name__=="__main__":main()
