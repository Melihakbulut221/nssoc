#!/usr/bin/env python3
"""Cloud-only resistance sensitivity and physical-anchor mapping; never modifies RC/layout."""
import collections,hashlib,json,math,os,re,shlex,subprocess,sys,tarfile,traceback
from pathlib import Path,PurePosixPath
import numpy as np
import scipy
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import spsolve
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/"wire-path-map"
MANIFEST="scripts/cdr-wire-path-map-pins.json"
INPUT="scripts/cdr-wire-path-map-inputs.json"
BRANCH="codex/cdr-wire-path-map"
def need(ok,msg):
    if not ok:raise AssertionError(msg)
def digest(p):
    with p.open("rb")as f:return hashlib.file_digest(f,"sha256").hexdigest()
def save(name,obj):
    p=OUT/name;p.parent.mkdir(parents=True,exist_ok=True)
    with p.open("x")as f:json.dump(obj,f,sort_keys=True,indent=2,allow_nan=False);f.write("\n")
def api(p):
    return json.loads(subprocess.check_output(["gh","api","repos/Melihakbulut221/nssoc/"+p]))
def gate():
    e=os.environ
    need(e.get("GITHUB_ACTIONS")=="true"and e.get("RUNNER_ENVIRONMENT")=="github-hosted","cloud hosted")
    need(e["GITHUB_RUN_ATTEMPT"]=="1"and e["GITHUB_EVENT_NAME"]=="workflow_dispatch","first dispatch")
    need(e["GITHUB_REPOSITORY"]=="Melihakbulut221/nssoc"and e["GITHUB_REF"]=="refs/heads/"+BRANCH,"repository branch")
    need(subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip()==e["GITHUB_SHA"],"source")
    need(np.__version__=="2.3.3"and scipy.__version__=="1.16.2","pinned numerical runtime")
    m=json.loads((ROOT/MANIFEST).read_bytes())
    for n,pin in m["files"].items():
        p=ROOT/n;need(p.is_file()and not p.is_symlink(),"regular source")
        need(dict(bytes=p.stat().st_size,sha256=digest(p))==pin,"source digest "+n)
    return json.loads((ROOT/INPUT).read_bytes())
def relative(name,root):
    p=PurePosixPath(name)
    need(not p.is_absolute()and ".."not in p.parts and str(p)==name,"canonical archive path")
    need(len(p.parts)>1 and p.parts[0]==root,"archive prefix")
    return str(PurePosixPath(*p.parts[1:]))
def acquire(cfg):
    work=ROOT/"wire-native-cache";work.mkdir()
    rid=cfg["producer_run_id"];source=cfg["producer_source"]
    r=api("actions/runs/"+str(rid));need(r["status"]=="completed"and r["head_sha"]==source and r["run_attempt"]==1,"actual producer")
    rel=api("releases/"+str(cfg["release_id"]));need(rel["tag_name"]==cfg["tag"]and rel["target_commitish"]==source,"release identity")
    need(api("git/ref/tags/"+cfg["tag"])["object"]["sha"]==source,"tag identity")
    assets={x["name"]:x for x in rel["assets"]};need(set(assets)=={x["name"]for x in cfg["assets"]},"complete asset set")
    for pin in cfg["assets"]:
        a=assets[pin["name"]];need(a["id"]==pin["id"]and a["size"]==pin["bytes"]and a["digest"]=="sha256:"+pin["sha256"],"asset metadata")
        p=work/pin["name"];need(p.parent==work,"flat asset")
        with p.open("xb")as f:subprocess.run(["gh","api","repos/Melihakbulut221/nssoc/releases/assets/"+str(a["id"]),"-H","Accept: application/octet-stream"],stdout=f,check=True)
        need(p.stat().st_size==pin["bytes"]and digest(p)==pin["sha256"],"asset bytes")
    parts=sorted([work/p["name"]for p in cfg["assets"]if ".tar.gz.part"in p["name"]])
    need(len(parts)==1 and parts[0].name.endswith(".part0000"),"actual single-part RC archive")
    archive=parts[0];need(archive.stat().st_size==cfg["archive_bytes"]and digest(archive)==cfg["archive_sha256"],"archive digest")
    target=work/"selected";seen={};names=set()
    selected={cfg["model"]["path"],cfg["composition"]["path"],"mim/composition/verified-wire-projection.spice",
      "mim/precise/wire/anchors08.json","mim/precise/wire/rc03/pump_wires.ext","mim/precise/wire/rc03/pump_wires.res.ext",
      "wire-stage/wire/audit.json","binding/inputs/parent/layout/nssoc_cdr_pd500_resistor_v59.gds",
      "binding/inputs/wire/native05/wires.l2n","binding/inputs/wire/native05/wires.gds",
      "binding/inputs/parent/layout/result.json","binding/inputs/parent/layout/schematic.cir",
      "binding/inputs/parent/layout/nssoc_cdr_pd500_resistor_v59.lef"}
    with tarfile.open(archive,"r|gz")as tar:
        for m in tar:
            need(m.name not in names,"duplicate member");names.add(m.name)
            if m.isdir():
                p=PurePosixPath(m.name);need(not p.is_absolute()and ".."not in p.parts,"directory path");continue
            n=relative(m.name,cfg["archive_root"]);need(m.isfile()and n in cfg["complete_members"]and n not in seen,"regular known member")
            h=hashlib.sha256();size=0;f=None
            if n in selected:
                p=target/n;p.parent.mkdir(parents=True,exist_ok=True);f=p.open("xb")
            try:
                stream=tar.extractfile(m)
                for b in iter(lambda:stream.read(1024*1024),b""):
                    size+=len(b);h.update(b)
                    if f:f.write(b)
            finally:
                if f:f.close()
            pin=dict(bytes=size,sha256=h.hexdigest());need(pin==cfg["complete_members"][n],"member digest "+n);seen[n]=pin
    if not(set(seen)==set(cfg["complete_members"])and selected<=set(seen)):
        save("acquisition-failure.json",dict(authenticated_members=len(seen),missing_selected=sorted(selected-set(seen)),missing_members=sorted(set(cfg["complete_members"])-set(seen)),unexpected_members=sorted(set(seen)-set(cfg["complete_members"]))))
    need(set(seen)==set(cfg["complete_members"])and selected<=set(seen),"complete authenticated capsule")
    save("acquisition.json",dict(run=r,release=rel,members_authenticated=seen,selected=sorted(selected),native_payloads_cloud_only=True))
    return target
def number(token):
    m=re.fullmatch(r"([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)([a-zA-Z]*)",token)
    need(m is not None,"SPICE numeric token")
    scales={"":1.,"t":1e12,"g":1e9,"meg":1e6,"k":1e3,"m":1e-3,"u":1e-6,"n":1e-9,"p":1e-12,"f":1e-15}
    suffix=m[2].lower();need(suffix in scales,"SPICE suffix")
    value=float(m[1])*scales[suffix];need(math.isfinite(value)and value>0,"finite positive resistance");return value
def resistors(text):
    rows=[];names=set()
    for line in text.splitlines():
        line=line.strip()
        if not line or line[0].upper()!="R":continue
        t=line.split();need(len(t)==4 and t[0].lower()not in names and t[1]!=t[2],"four-token unique resistor")
        names.add(t[0].lower());rows.append((t[0],t[1],t[2],number(t[3])))
    need(rows,"nonempty resistor graph");return rows
def solve(edges,a,b):
    adj=collections.defaultdict(set)
    for _,u,v,r in edges:
        need(u!=v and math.isfinite(r)and r>0,"valid resistor edge");adj[u].add(v);adj[v].add(u)
    need(a in adj and b in adj and a!=b,"actual distinct endpoints")
    found={a};todo=[a]
    while todo:
        u=todo.pop()
        for v in adj[u]-found:found.add(v);todo.append(v)
    need(b in found,"same connected resistance component")
    es=[e for e in edges if e[1]in found]
    nodes=sorted(found-{b});pos={n:i for i,n in enumerate(nodes)};ii=[];jj=[];vv=[]
    for _,u,v,r in es:
        g=1/r
        for n in(u,v):
            if n!=b:ii.append(pos[n]);jj.append(pos[n]);vv.append(g)
        if u!=b and v!=b:
            ii.extend([pos[u],pos[v]]);jj.extend([pos[v],pos[u]]);vv.extend([-g,-g])
    mat=coo_matrix((vv,(ii,jj)),shape=(len(nodes),len(nodes))).tocsc()
    rhs=np.zeros(len(nodes));rhs[pos[a]]=1.;pot=spsolve(mat,rhs)
    need(np.all(np.isfinite(pot)),"finite solved voltages")
    residual=float(np.max(np.abs(mat@pot-rhs)));need(residual<1e-7,"Kirchhoff residual")
    v={n:float(pot[i])for n,i in pos.items()};v[b]=0.
    resistance=v[a];need(resistance>0,"positive effective R")
    ranked=[]
    for name,u,w,r in es:
        current=(v[u]-v[w])/r;power=current*current*r
        ranked.append(dict(name=name,a=u,b=w,resistance_ohm=r,unit_injection_current_a=current,
          unit_injection_power_w=power,effective_resistance_contribution_fraction=power/resistance))
    energy=sum(x["unit_injection_power_w"]for x in ranked)
    need(math.isclose(energy,resistance,rel_tol=1e-7,abs_tol=1e-9),"unit injection energy conservation")
    return dict(source=a,sink=b,nodes=len(found),edges=len(es),effective_resistance_ohm=resistance,
      maximum_kcl_residual_a=residual,unit_injection_energy_w=energy,
      top_edges=sorted(ranked,key=lambda x:x["unit_injection_power_w"],reverse=True)[:20])
def controls():
    checks=[]
    for label,edges,want in[
      ("series",[("r1","a","m",2.),("r2","m","b",3.)],5.),
      ("parallel",[("r1","a","b",2.),("r2","a","b",3.)],1.2),
      ("triangle",[("r1","a","b",3.),("r2","a","m",2.),("r3","m","b",4.)],2.)]:
        got=solve(edges,"a","b");need(math.isclose(got["effective_resistance_ohm"],want,rel_tol=1e-12),label);checks.append(label)
        reverse=solve(edges,"b","a");need(math.isclose(reverse["effective_resistance_ohm"],want,rel_tol=1e-12),"reciprocity");checks.append(label+" reciprocity")
    for label,edges in[("disconnected",[("r1","a","m",1.),("r2","b","n",2.)]),("zero",[("r","a","b",0.)]),("negative",[("r","a","b",-1.)]),("nonfinite",[("r","a","b",float("nan"))])]:
        try:solve(edges,"a","b")
        except AssertionError:checks.append("reject "+label)
        else:raise AssertionError(label)
    need(number("2k")==2000 and number("2m")==.002 and number("2meg")==2e6,"SPICE suffix distinction");checks.append("SPICE milli kilo mega")
    for t in("nan","inf","1x"):
        try:number(t)
        except AssertionError:checks.append("reject numeric "+t)
        else:raise AssertionError(t)
    return checks
def parse_physical_nodes(text):
    out=collections.defaultdict(list);scale=[1.,1.,1.];scales_seen=0
    for line in text.splitlines():
        t=shlex.split(line)
        if not t:continue
        if t[0]=="scale":
            need(len(t)==4,"EXT scale");scales_seen+=1;need(scales_seen==1,"single EXT scale");scale=list(map(float,t[1:]));need(all(math.isfinite(x)and x>0 for x in scale),"positive scales")
        if t[0]in("node","rnode"):
            need(len(t)>=7,"EXT node record")
            x,y=float(t[4]),float(t[5]);need(math.isfinite(x)and math.isfinite(y),"finite EXT coordinates")
            out[t[1]].append(dict(record=t[0],x_native=x,y_native=y,material=t[6]if t[0]=="node"else None,rnode_type_field=t[6]if t[0]=="rnode"else None))
    return dict(scale=scale,nodes=dict(out),node_coordinates_are_reference_points_not_resistor_footprints=True)
def physical_nodes(path):return parse_physical_nodes(path.read_text())
def coordinate_controls():
    checks=[]
    row=parse_physical_nodes('scale 1000 1 0.5\nnode "P" 0 1 240 6400 m7\nrnode "P.n0" 0 2 300 6400 0\n')
    need(row["scale"]==[1000.,1.,.5]and row["nodes"]["P"][0]["material"]=="m7","ordinary node geometry");checks.append("ordinary node scale")
    r=row["nodes"]["P.n0"][0];need(r["record"]=="rnode"and r["material"]is None and r["rnode_type_field"]=="0"and r["x_native"]==300.,"rnode coordinate and unknown material");checks.append("rnode numeric type is not a metal")
    for label,text in[("duplicate scale","scale 1 1 1\nscale 1 1 1"),("nonfinite coordinate",'rnode "x" 0 1 nan 2 0'),("short record",'rnode "x" 0 1 2')]:
        try:parse_physical_nodes(text)
        except AssertionError:checks.append("reject "+label)
        else:raise AssertionError(label)
    return checks

def analyze(base,cfg):
    comp=json.loads((base/cfg["composition"]["path"]).read_bytes())
    anchors=json.loads((base/"mim/precise/wire/anchors08.json").read_bytes())
    raw=(base/"mim/composition/verified-wire-projection.spice").read_text()
    edges=resistors(raw);model=resistors((base/cfg["model"]["path"]).read_text())
    mapping=comp["wire_node_map"]
    expect=collections.Counter((n,mapping[u],mapping[v],r)for n,u,v,r in edges)
    need(expect==collections.Counter(model),"exact all original model R cards via original node map")
    need(len(model)==cfg["actual_numerical_counts"]["R"],"original R count")
    physical={a["label"]:a for a in anchors["anchors"]};need(len(physical)==len(anchors["anchors"]),"unique physical anchors")
    ext={name:physical_nodes(base/("mim/precise/wire/rc03/"+name))for name in("pump_wires.ext","pump_wires.res.ext")}
    targets=[
      ("supply124","P_avdd","T124_C"),("ground126","P_avss","T126_E"),("ground129","P_avss","T129_E"),
      ("shunt228ground","P_avss","T228_rppd_2"),("shunt235ground","P_avss","T235_rppd_2"),("shunt239ground","P_avss","T239_rppd_2"),
      ("A_series_to_shunt","T227_rppd_2","T228_rppd_1"),("A_series_to_base","T227_rppd_2","T123_B"),
      ("A_shunt_to_base","T228_rppd_1","T123_B"),("C_series_to_shunt","T238_rppd_2","T239_rppd_1"),
      ("D_series_to_shunt","T234_rppd_2","T235_rppd_1")]
    results={}
    for label,a,b in targets:
        need(a in physical and b in physical,"actual physical anchor")
        pa,pb=physical[a],physical[b];need(pa["native_cluster"]==pb["native_cluster"]and pa["wire_component"]==pb["wire_component"],"native conductor ownership")
        row=solve(edges,a,b);row["source_anchor"]=pa;row["sink_anchor"]=pb
        row["terminal_coordinate_offsets_dbu"]={}
        for name,anchor in ((a,pa),(b,pb)):
            records=ext["pump_wires.res.ext"]["nodes"].get(name,[])
            need(records,"actual rnode coordinate for physical terminal")
            row["terminal_coordinate_offsets_dbu"][name]=[dict(delta_x=r["x_native"]*ext["pump_wires.res.ext"]["scale"][2]*10-anchor["point_dbu"][0],delta_y=r["y_native"]*ext["pump_wires.res.ext"]["scale"][2]*10-anchor["point_dbu"][1])for r in records]
        for e in row["top_edges"]:
            e["native_node_references"]={n:{f:info["nodes"].get(n,[])for f,info in ext.items()}for n in(e["a"],e["b"])}
            need(all(refs["pump_wires.res.ext"]for refs in e["native_node_references"].values()),"all ranked edge endpoints have native rnode records")
        results[label]=row
    save("physical-path-resistance-map.json",dict(source=os.environ["GITHUB_SHA"],run=int(os.environ["GITHUB_RUN_ID"]),
      producer=cfg["producer_run_id"],original_model_R_cards_exact=True,resistors=len(edges),targets=results,
      all_ranked_endpoints_have_rnode_coordinates=True,
      ext_scale={n:i["scale"]for n,i in ext.items()},ext_coordinate_reference="https://opencircuitdesign.com/magic/manpages/ext_manpage.html",
      scope="Unit-current passive DC sensitivity on original extracted wire graph; not operational currents, AC transfer, proof of cause, resistor footprints or PEX signoff.",
      devices_mutated=False,layout_mutated=False,RC_mutated=False,physical_acceptance=False,full_phy_accepted=False,final_timing_complete=False))
    save("summary.json",{k:{n:v for n,v in r.items()if n not in("top_edges","source_anchor","sink_anchor")}for k,r in results.items()})
def main():
    try:
        cfg=gate();checks=controls()+coordinate_controls();save("controls.json",dict(count=len(checks),passed=checks))
        if sys.argv[1:] == ["--controls"]:return
        need(sys.argv[1:]==["--map"],"explicit mode")
        base=acquire(cfg);analyze(base,cfg)
        save("result.json",dict(status="COMPLETE_NATIVE_WIRE_PATH_MAP",physical_acceptance=False,full_phy_accepted=False))
    except Exception as exc:
        save("failure.json",dict(type=type(exc).__name__,message=str(exc),traceback=traceback.format_exc(),physical_acceptance=False));raise
if __name__=="__main__":main()
