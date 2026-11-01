#!/usr/bin/env python3
"""Audit exact MOS parameter/domain declarations in the existing native archive, cloud only."""
import base64,hashlib,json,os,pathlib,re,subprocess,tarfile
from decimal import Decimal
ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=ROOT/"cloud-mos-model-domain-audit"
CFG="scripts/mos-model-domain-audit-inputs.json"
REPO="repos/Melihakbulut221/nssoc/"
def require(ok,label):
    if not ok:raise ValueError(label)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def enc(value):return(json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+"\n").encode()
def pin(path):
    with path.open("rb")as stream:return dict(bytes=path.stat().st_size,sha256=hashlib.file_digest(stream,"sha256").hexdigest())
def api(path):
    r=subprocess.run(["gh","api",REPO+path],capture_output=True,timeout=120)
    require(r.returncode==0,r.stderr.decode()[:2000]);return json.loads(r.stdout)
def fetch(p):
    d=api("contents/"+p["path"]+"?ref="+p["source"])
    b=d if d.get("content")else api("git/blobs/"+d["sha"])
    raw=base64.b64decode(b["content"])
    require(dict(bytes=len(raw),sha256=sha(raw))=={k:p[k]for k in("bytes","sha256")},"exact derived input")
    return raw
def restore(archive,inventory,wanted,directory,prefix="cloud-cdr-via2-m3-loaded"):
    """Hash every member; materialize only explicitly requested native members."""
    require(set(wanted)<=set(inventory)and not directory.exists(),"exclusive selected native output")
    directory.mkdir();seen=set();dirs=set();receipt={}
    with tarfile.open(archive,"r|gz")as tar:
        for member in tar:
            path=pathlib.PurePosixPath(member.name.rstrip("/"))
            require(not path.is_absolute()and ".."not in path.parts and str(path)==member.name.rstrip("/")and path.parts[0]==prefix,"owned archive path")
            if member.isdir():
                require(str(path)not in dirs,"duplicate archive directory");dirs.add(str(path));continue
            require(member.isreg()and len(path.parts)>1,"regular archive member only")
            name="/".join(path.parts[1:]);require(name in inventory and name not in seen,"complete unique archive member")
            expected=inventory[name];require(member.size==expected["bytes"],"member declared byte count")
            stream=tar.extractfile(member);require(stream is not None,"regular member stream")
            destination=(directory/("selected-"+str(len(receipt))))if name in wanted else None
            output=destination.open("xb")if destination else None
            h=hashlib.sha256();count=0
            try:
                while block:=stream.read(4*1024**2):
                    count+=len(block);require(count<=expected["bytes"],"bounded member stream");h.update(block)
                    if output:output.write(block)
            finally:
                stream.close()
                if output:output.close()
            require(dict(bytes=count,sha256=h.hexdigest())==expected,"complete member digest")
            seen.add(name)
            if destination:receipt[name]=dict(path=str(destination),**expected)
    require(seen==set(inventory)and set(receipt)==set(wanted),"all indexed members and requested files")
    return dict(verified_members=len(seen),all_members_verified=True,selected=receipt)

def inspect_text(path):
    raw=path.read_bytes();lines=raw.decode().splitlines()
    pattern=re.compile(r"\b[wl](?:min|max)\b|(?:validity|valid|calibrat|characteriz).*range|range.*(?:valid|calibrat)|(?:finger.*width|width.*finger)|(?:maximum|minimum).*\b(?:width|length)\b|\bw\s*/\s*ng\b",re.I)
    rows=[dict(line=i,text=line.strip())for i,line in enumerate(lines,1)if pattern.search(line)]
    headers=[dict(line=i,text=line.strip())for i,line in enumerate(lines,1)if re.match(r"\s*\.subckt\s+sg13_lv_[np]mos\b",line,re.I)]
    require(len(rows)<200,"bounded parameter/domain declaration report")
    return dict(file_pin=pin(path),total_lines=len(lines),domain_or_finger_expression_matches=rows,device_headers=headers,
        no_match_is_not_domain_acceptance=True)
def scalar(value):
    m=re.fullmatch(r"([0-9]+(?:\.[0-9]*)?)([unp]?)",value)
    require(m is not None,"explicit geometry scalar")
    return Decimal(m[1])*{"":Decimal(1),"u":Decimal("1e-6"),"n":Decimal("1e-9"),"p":Decimal("1e-12")}[m[2]]
def main():
    require(os.environ.get("GITHUB_ACTIONS")=="true"and os.environ.get("GITHUB_RUN_ATTEMPT")=="1"and os.environ.get("GITHUB_REPOSITORY")=="Melihakbulut221/nssoc","single cloud execution")
    c=json.loads((ROOT/CFG).read_bytes())
    for p,expected in c["source_files"].items():require(pin(ROOT/p)==expected,"exact audit source")
    OUT.mkdir(exist_ok=False)
    for p in [*c["source_files"],CFG]:
        target=OUT/"source"/p;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((ROOT/p).read_bytes())
    values={}
    for name,p in c["inputs"].items():
        raw=fetch(p);(OUT/name).write_bytes(raw);values[name]=json.loads(raw)
    index=values["index.json"];parts=values["parts.json"]
    require(parts["context"]==index["context"]==c["producer_context"]and parts["archive"]==c["archive"],"exact native producer and complete archive")
    run=api("actions/runs/"+str(c["producer_context"]["run_id"]));release=api("releases/"+str(c["release_id"]));tag=api("git/ref/tags/"+c["release_tag"])
    require(run["status"]=="completed"and run["conclusion"]=="failure"and run["run_attempt"]==1 and run["head_sha"]==c["producer_context"]["source"],"actual producer identity")
    require(release["target_commitish"]==c["producer_context"]["source"]and release["tag_name"]==c["release_tag"]and tag["object"]["type"]=="commit"and tag["object"]["sha"]==c["producer_context"]["source"],"exact archive release")
    assets={a["name"]:a for a in release["assets"]}
    require(len(assets)==len(release["assets"])==6 and len(parts["parts"])==4 and len(index["files"])==109,"complete release and archive inventory")
    work=pathlib.Path(os.environ["RUNNER_TEMP"])/("nssoc-mos-model-audit-"+os.environ["GITHUB_RUN_ID"]);work.mkdir(exist_ok=False)
    archive=work/"complete-native.tar.gz";observations=[]
    with archive.open("xb")as output:
        for i,row in enumerate(parts["parts"]):
            a=assets[row["name"]];require(row["index"]==i and a["state"]=="uploaded"and a["size"]==row["bytes"]and a["digest"]=="sha256:"+row["sha256"],"exact ordered archive part")
            p=work/("part-"+str(i))
            with p.open("xb")as stream:r=subprocess.run(["gh","api",REPO+"releases/assets/"+str(a["id"]),"-H","Accept: application/octet-stream"],stdout=stream,stderr=subprocess.PIPE,timeout=600)
            observed=pin(p);require(r.returncode==0 and observed=={k:row[k]for k in("bytes","sha256")},"complete part acquired")
            observations.append(dict(index=i,asset=a["id"],pin=observed));(OUT/"acquisition.json").write_bytes(enc(observations))
            with p.open("rb")as stream:
                while block:=stream.read(4*1024**2):output.write(block)
    require(pin(archive)==c["archive"],"complete native archive digest")
    selected=restore(archive,index["files"],set(c["model_members"]),work/"selected",prefix="cloud-sampler-load")
    (OUT/"restore.json").write_bytes(enc(selected))
    models={name:inspect_text(pathlib.Path(value["path"]))for name,value in selected["selected"].items()}
    comp=values["composition.json"];require(len(comp["device_records"])==500 and len({r["native_id"]for r in comp["device_records"]})==500,"complete composition")
    mos=[]
    for r in comp["device_records"]:
        if not {"D","G","S","B"}<={t["terminal"]for t in r["terminals"]}:continue
        p=r["parameters"];ng=int(p["ng"]);require(ng>0,"positive gate count")
        mos.append(dict(native_id=r["native_id"],model=r["model"],parameters=p,
            total_width_um=str(scalar(p["w"])/Decimal("1e-6")),
            reported_finger_width_um=str(scalar(p["w"])/ng/Decimal("1e-6"))))
    require(len(mos)==50,"all50 MOS geometry records")
    result=dict(status="COMPLETE_PINNED_MOS_MODEL_PARAMETER_AUDIT_NOT_ACCEPTANCE",
        source=os.environ["GITHUB_SHA"],run=int(os.environ["GITHUB_RUN_ID"]),producer_context=c["producer_context"],
        native_archive=c["archive"],models=models,all50_mos=mos,
        proposed_slave_width_trial=dict(native_ids=[7,8,9,10,36,37,38,39],width_um=54,ng=1,dispatched=False,model_domain_qualified=False),
        interpretation="Range declarations and width/finger mapping from the exact used model must be interpreted before a new width trial. LVS total-width equality and prior stress-gate success are not model-domain qualification. No model file or raw archive is included in derived outputs.",
        native_models_retained_on_runner_only=True,native_simulation_rerun=False,geometry_changed=False,physical_acceptance=False,full_phy_accepted=False,final_timing_complete=False)
    (OUT/"producer.json").write_bytes(enc(dict(run=run,release=release,tag=tag)))
    (OUT/"result.json").write_bytes(enc(result));print(json.dumps(dict(status=result["status"],models=models,mos_geometry_census=len(mos))),flush=True)
if __name__=="__main__":main()
