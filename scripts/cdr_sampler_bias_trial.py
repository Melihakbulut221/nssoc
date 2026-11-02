#!/usr/bin/env python3
"""Provisional balanced eight-resistor input-bias trial; fixed wire RC is not matching PEX."""
import copy,hashlib,io,json,re,subprocess,zipfile
from pathlib import Path
TARGETS="scripts/cdr-sampler-bias-trial-targets.json"
SCOPE="PROVISIONAL_DEVICE_PARAMETER_TRIAL_WITH_FIXED_PARENT_INTERCONNECT_RC"
FLAGS=dict(matching_layout_verified=False,fresh_RC_for_modified_devices=False,physical_acceptance=False,qualified_pex=False,full_phy_accepted=False,final_timing_complete=False)
def require(ok,message):
    if not ok:raise AssertionError(message)
def digest(data):return hashlib.sha256(data).hexdigest()
PLAN={name:(("1.8u","1.75u","8u")if name.endswith(("UP","UN"))else("5u","6u","4u"))for name in ("SD_UP","SD_UN","SC_UP","SC_UN","SD_DP","SD_DN","SC_DP","SC_DN")}
def rewrite_card(line,instance,old="1.8u",new="1.75u",width="8u"):
    fields=line.split()
    require(fields and fields[0]==instance,"literal primitive instance")
    require(len(fields)>5 and fields[4]=="rppd","three-terminal rppd card")
    params=fields[5:]
    require(len({x.split("=")[0]for x in params})==len(params),"unique primitive parameters")
    require(dict(x.split("=")for x in params)==dict(b="0",l=old,m="1",ps="0u",sw_et="1",w=width),"exact parent resistor parameters")
    pattern=r"(?<!\S)l="+re.escape(old)+r"(?!\S)"
    changed,n=re.subn(pattern,"l="+new,line)
    require(n==1 and changed.replace("l="+new,"l="+old,1)==line,"one reversible length token")
    return changed
def source_controls(root):
    targets=json.loads((root/TARGETS).read_bytes())
    require({p["schematic"]["name"]:p["layout"]["id"]for p in targets}==dict(SD_UP=182,SD_UN=183,SC_UP=220,SC_UN=221,SD_DP=184,SD_DN=185,SC_DP=222,SC_DN=223),"eight actual matched resistors")
    line="XD0182 w_T182_rppd_1 w_T182_rppd_2 w_T182_rppd_sub rppd b=0 l=1.8u m=1 ps=0u sw_et=1 w=8u\n"
    out=rewrite_card(line,"XD0182")
    require(out==line.replace("l=1.8u","l=1.75u"),"literal complete positive delta")
    down=line.replace("XD0182","XD0184").replace("l=1.8u","l=5u").replace("w=8u","w=4u")
    require(rewrite_card(down,"XD0184",old="5u",new="6u",width="4u")==down.replace("l=5u","l=6u"),"actual pull-down parameter shape")
    rejected=[]
    for name,card,instance in [
        ("wrong-instance",line,"XD0183"),("wrong-model",line.replace(" rppd "," cap_cmim "),"XD0182"),
        ("wrong-old-length",line.replace("1.8u","1.7u"),"XD0182"),
        ("wrong-width",line.replace("w=8u","w=9u"),"XD0182"),
        ("duplicate-length",line.rstrip()+" l=1.8u\n","XD0182"),
        ("missing-parameter",line.replace(" sw_et=1",""),"XD0182")]:
        try:rewrite_card(card,instance)
        except (AssertionError,ValueError):rejected.append(name)
        else:raise AssertionError("accepted "+name)
    return dict(status="PASS_PROVISIONAL_TRIAL_SOURCE_CONTROLS",targets=8,rejected=rejected,native_model_modified=False,transient_executed=False,scope=SCOPE,**FLAGS)
def acquire_mapping(host):
    r=host.api("actions/runs/41450661063")
    require(r["status"]=="completed"and r["conclusion"]=="success"and r["head_sha"]=="22baa225789b8ec1c9ce98437196af1e48fc2918"and r["run_attempt"]==1,"actual successful full500 mapping")
    raw=subprocess.check_output(["gh","api","repos/"+host.REPO+"/actions/artifacts/13144567876/zip"],timeout=180)
    require(len(raw)==66389 and digest(raw)=="415215780ef60cd6bd971ccb782d1dfbe4430a67c2f5ae10a3f0d60c6bbcd9cb","exact mapping artifact")
    z=zipfile.ZipFile(io.BytesIO(raw));names=z.namelist()
    require(len(names)==len(set(names))and all(not n.startswith("/")and ".."not in Path(n).parts for n in names),"safe mapping member names")
    found=[n for n in names if n.endswith("/device-correspondence.json")or n=="device-correspondence.json"]
    require(len(found)==1,"unique mapping")
    content=z.read(found[0]);q=json.loads(content)
    require(len(q["pairs"])==500 and all(p["status"]=="Match"for p in q["pairs"]),"all original500 matched pairs")
    expected=json.loads((host.ROOT/TARGETS).read_bytes())
    ids={p["layout"]["id"]for p in expected}
    actual=[p for p in q["pairs"]if p["layout"]["id"]in ids]
    require(sorted(actual,key=lambda p:p["layout"]["id"])==sorted(expected,key=lambda p:p["layout"]["id"]),"complete actual target parameters and terminals")
    p=host.DERIVED/"bias-parent-native-device-correspondence.json"
    p.write_bytes(content)
    host.save(host.DERIVED/"bias-mapping-acquisition.json",dict(run=r,artifact=13144567876,bytes=len(raw),sha256=digest(raw),mapping=host.pin(p),targets=expected,scope=SCOPE,**FLAGS))
    return expected
def derive(host,paths):
    # Parent authentication and original RC qualification have already completed.
    parent_basis=host.basis()
    parent_pins={k:host.pin(p)for k,p in paths.items()}
    require(all(parent_pins[k]=={f:parent_basis["inputs"][k][f]for f in ("bytes","sha256")}for k in paths),"exact authenticated parent inputs")
    targets=acquire_mapping(host)
    original=Path(paths["model"]).read_bytes();text=original.decode()
    composition=host.read(paths["composition"]);changed=copy.deepcopy(composition)
    require(len(composition["device_records"])==500,"complete500 model")
    by_id={d["native_id"]:d for d in composition["device_records"]}
    require(len(by_id)==500,"unique device IDs")
    lines=text.splitlines(keepends=True);indices={}
    for i,line in enumerate(lines):
        parts=line.split()
        if parts:
            require(parts[0]not in indices or not parts[0].startswith("XD"),"unique native primitive cards")
            indices[parts[0]]=i
    delta=[]
    for target in targets:
        d=by_id[target["layout"]["id"]];name=target["loaded_instance"]
        require(d["model"]=="rppd"and d["instance"]==name and d["parameters"]==target["loaded_parameters"],"actual loaded mapped resistor")
        require({t["terminal"]:dict(cluster=t["native_cluster"],name=t["native_net"])for t in d["terminals"]}==
                {k:dict(cluster=v["cluster"],name=v["name"])for k,v in target["layout"]["terminals"].items()},"actual native resistor terminal identity")
        require(name in indices,"one actual target primitive")
        old,new,width=PLAN[target["schematic"]["name"]]
        require(d["parameters"]["l"]==old and d["parameters"]["w"]==width,"exact planned input dimensions")
        i=indices[name];before=lines[i];lines[i]=rewrite_card(before,name,old=old,new=new,width=width)
        cd=next(x for x in changed["device_records"]if x["native_id"]==d["native_id"])
        cd["parameters"]["l"]=new
        delta.append(dict(instance=name,native_id=d["native_id"],schematic=target["schematic"]["name"],old_length=old,new_length=new,width=width,line_index=i,original_card_sha256=digest(before.encode()),trial_card_sha256=digest(lines[i].encode())))
    require(len(delta)==8 and len({d["line_index"]for d in delta})==8,"eight distinct exact modifications")
    modified="".join(lines).encode();reversed_lines=list(lines)
    for d in delta:reversed_lines[d["line_index"]]=rewrite_card(lines[d["line_index"]],d["instance"],old=d["new_length"],new=d["old_length"],width=d["width"])
    require("".join(reversed_lines).encode()==original,"entire parent model exact reversal including every R/C card")
    reversed_contract=copy.deepcopy(changed)
    for d in reversed_contract["device_records"]:
        if d["native_id"]in {t["layout"]["id"]for t in targets}:d["parameters"]["l"]=next(x["old_length"]for x in delta if x["native_id"]==d["native_id"])
    require(reversed_contract==composition,"all other492 devices and all contract metadata unchanged")
    dest=host.NATIVE/"provisional-bias-model";dest.mkdir()
    (dest/"model.spice").write_bytes(modified);host.save(dest/"composition.json",changed)
    result=dict(model=str(dest/"model.spice"),composition=str(dest/"composition.json"),planes=paths["planes"])
    require(all(host.pin(paths[k])==parent_pins[k]for k in paths),"parent files untouched")
    receipt=dict(status="DERIVED_PROVISIONAL_BALANCED_EIGHT_RESISTOR_BIAS_TRIAL",scope=SCOPE,parent_rc_producer=parent_basis["producer"]["run"],parent_layout=parent_basis["candidate"],parent_inputs=parent_pins,trial_inputs={k:host.pin(p)for k,p in result.items()},delta=delta,entire_model_exact_reversal=True,all_other492_devices_unchanged=True,all_parent_wire_RC_cards_unchanged=True,original_measurement_limits_unchanged=True,closed_loop=False,**FLAGS)
    receipt_path=host.DERIVED/"provisional-bias-derivation.json";host.save(receipt_path,receipt)
    b=copy.deepcopy(parent_basis);ctx=host.context()
    b["producer"]=dict(source=ctx["source"],run=ctx["run_id"],release=host.release_gate()["id"])
    b["inputs"]={k:dict(path=p,**host.pin(p))for k,p in result.items()}
    protected={str(Path(p)):parent_pins[k]for k,p in paths.items()}
    protected[str(receipt_path)]=host.pin(receipt_path)
    return result,b,protected
