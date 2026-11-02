#!/usr/bin/env python3
"""Provisional eight slave collector resistor trial; all MOS geometry stays original; fixed wire RC is not matching physical extraction."""
import copy,hashlib,io,json,re,subprocess,zipfile
from pathlib import Path
TARGETS="scripts/cdr-sampler-bias-trial-targets.json"
SCOPE="PROVISIONAL_DEVICE_PARAMETER_TRIAL_WITH_FIXED_PARENT_INTERCONNECT_RC"
FLAGS=dict(matching_layout_verified=False,fresh_RC_for_modified_devices=False,physical_acceptance=False,qualified_pex=False,full_phy_accepted=False,final_timing_complete=False)
IDS={'SA_S_RP': 205, 'SA_S_RN': 202, 'SB_S_RP': 194, 'SB_S_RN': 191, 'SC_S_RP': 214, 'SC_S_RN': 212, 'SD_S_RP': 176, 'SD_S_RN': 175}
def require(ok,message):
    if not ok:raise AssertionError(message)
def digest(data):return hashlib.sha256(data).hexdigest()
def plan(target):
    name=target["schematic"]["name"]
    require(name in IDS and target["layout"]["id"]==IDS[name],"exact slave target identity")
    model="rppd";old=dict(b="0",l="2.6u",m="1",ps="0u",sw_et="1",w="32u")
    new=dict(old,l="1.9u");order=["rppd_1","rppd_2","rppd_sub"]
    require(target["layout"]["model"]==target["schematic"]["model"]==model and target["loaded_parameters"]==old,"exact parent model and parameters")
    return model,old,new,order
def rewrite_card(line,instance,model,nodes,old,new):
    fields=line.split();prefix=[instance,*nodes,model]
    require(fields[:len(prefix)]==prefix,"complete ordered primitive and nodes")
    params=fields[len(prefix):]
    require(all(x.count("=")==1 for x in params),"parameter token syntax")
    require(len(params)==len(old) and len({x.split("=")[0]for x in params})==len(params),"complete unique parameter keys")
    require(dict(x.split("=")for x in params)==old and set(old)==set(new),"exact original parameters")
    changed=line
    for key in old:
        if old[key]==new[key]:continue
        changed,n=re.subn(r"(?<!\S)"+re.escape(key+"="+old[key])+r"(?!\S)",key+"="+new[key],changed)
        require(n==1,"one exact parameter token "+key)
    require(changed!=line,"nonempty circuit parameter delta")
    return changed
def source_controls(root):
    targets=json.loads((root/TARGETS).read_bytes())
    require(len(targets)==8 and {p["schematic"]["name"]:p["layout"]["id"]for p in targets}==IDS,"all8 matched slave load targets")
    positive=[]
    for t in targets:
        model,old,new,order=plan(t);name=t["loaded_instance"];nodes=["n"+str(i)for i in range(len(order))]
        line=" ".join([name,*nodes,model,*[k+"="+v for k,v in old.items()]])+"\n"
        after=rewrite_card(line,name,model,nodes,old,new)
        require(rewrite_card(after,name,model,nodes,new,old)==line,"complete primitive roundtrip")
        positive.append(name)
    rejected=[]
    for model,old,new,nodes in [
        ("rppd",dict(b="0",l="2.6u",m="1",ps="0u",sw_et="1",w="32u"),dict(b="0",l="1.9u",m="1",ps="0u",sw_et="1",w="32u"),["a","b","bulk"]),
        ("sg13_lv_nmos",dict(ad="12.24p",**{"as":"12.24p"},l="0.3u",m="1",ng="1",pd="72.68u",ps="72.68u",rfmode="0",w="36u"),dict(ad="16.32p",**{"as":"16.32p"},l="0.3u",m="1",ng="1",pd="96.68u",ps="96.68u",rfmode="0",w="48u"),["d","g","s","bulk"])]:
        line=" ".join(["XDTEST",*nodes,model,*[k+"="+v for k,v in old.items()]])+"\n"
        key=next(iter(old));token=key+"="+old[key]
        for label,bad in [
            ("instance",line.replace("XDTEST","XDOTHER",1)),
            ("model",line.replace(" "+model+" "," wrong_model ",1)),
            ("nodes",line.replace(" "+nodes[0]+" "," wrong_node ",1)),
            ("missing",line.replace(" "+token,"",1)),
            ("duplicate",line.rstrip()+" "+token+"\n"),
            ("extra",line.rstrip()+" invented=1\n"),
            ("changed-old",line.replace(token,key+"=BAD",1))]:
            try:rewrite_card(bad,"XDTEST",model,nodes,old,new)
            except (AssertionError,ValueError):rejected.append(model+":"+label)
            else:raise AssertionError("accepted "+model+":"+label)
    return dict(status="PASS_SLAVE_LOAD_ONLY_TRIAL_SOURCE_CONTROLS",targets=8,positive_roundtrips=positive,rejected=rejected,native_model_modified=False,transient_executed=False,scope=SCOPE,**FLAGS)
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
    require(len(content)==796986 and digest(content)=="2beff7cbad50618c7a00100db3af5d63276a1476acb1dc56224e1822055ac06f","exact full mapped record")
    require(len(q["pairs"])==500 and all(p["status"]=="Match"for p in q["pairs"]),"all original500 matched pairs")
    expected=json.loads((host.ROOT/TARGETS).read_bytes())
    ids={p["layout"]["id"]for p in expected}
    actual=[p for p in q["pairs"]if p["layout"]["id"]in ids]
    require(sorted(actual,key=lambda p:p["layout"]["id"])==sorted(expected,key=lambda p:p["layout"]["id"]),"complete actual target parameters and terminals")
    p=host.DERIVED/"bias-parent-native-device-correspondence.json";p.write_bytes(content)
    host.save(host.DERIVED/"bias-mapping-acquisition.json",dict(run=r,artifact=13144567876,bytes=len(raw),sha256=digest(raw),mapping=host.pin(p),targets=expected,scope=SCOPE,**FLAGS))
    return expected
def derive(host,paths):
    parent_basis=host.basis();parent_pins={k:host.pin(p)for k,p in paths.items()}
    require(all(parent_pins[k]=={f:parent_basis["inputs"][k][f]for f in ("bytes","sha256")}for k in paths),"exact authenticated parent inputs")
    targets=acquire_mapping(host)
    require(len(targets)==8 and {p["schematic"]["name"]:p["layout"]["id"]for p in targets}==IDS,"exact complete plan")
    original=Path(paths["model"]).read_bytes();composition=host.read(paths["composition"]);changed=copy.deepcopy(composition)
    require(len(composition["device_records"])==500,"complete500 model")
    by_id={d["native_id"]:d for d in composition["device_records"]};require(len(by_id)==500,"unique device IDs")
    lines=original.decode().splitlines(keepends=True);indices={}
    for i,line in enumerate(lines):
        parts=line.split()
        if parts:
            require(parts[0]not in indices or not parts[0].startswith("XD"),"unique native primitive cards")
            indices[parts[0]]=i
    delta=[]
    for target in targets:
        d=by_id[target["layout"]["id"]];name=target["loaded_instance"];model,old,new,order=plan(target)
        require(d["model"]==model and d["instance"]==name and d["parameters"]==old,"actual loaded mapped primitive")
        require([t["terminal"]for t in d["terminals"]]==order,"actual native terminal order")
        require({t["terminal"]:dict(cluster=t["native_cluster"],name=t["native_net"])for t in d["terminals"]}==
                {k:dict(cluster=v["cluster"],name=v["name"])for k,v in target["layout"]["terminals"].items()},"actual native terminal identity")
        require(name in indices,"one actual target primitive")
        nodes=[t["node"]for t in d["terminals"]]
        i=indices[name];before=lines[i];lines[i]=rewrite_card(before,name,model,nodes,old,new)
        next(x for x in changed["device_records"]if x["native_id"]==d["native_id"])["parameters"]=new
        delta.append(dict(instance=name,native_id=d["native_id"],schematic=target["schematic"]["name"],model=model,nodes=nodes,old=old,new=new,line_index=i,original_card_sha256=digest(before.encode()),trial_card_sha256=digest(lines[i].encode())))
    require(len(delta)==8 and len({d["line_index"]for d in delta})==8,"8 distinct exact load modifications")
    modified="".join(lines).encode();reversed_lines=list(lines)
    for d in delta:reversed_lines[d["line_index"]]=rewrite_card(lines[d["line_index"]],d["instance"],d["model"],d["nodes"],d["new"],d["old"])
    require("".join(reversed_lines).encode()==original,"entire parent model exact reversal including every R/C card")
    reversed_contract=copy.deepcopy(changed)
    for d in delta:next(x for x in reversed_contract["device_records"]if x["native_id"]==d["native_id"])["parameters"]=d["old"]
    require(reversed_contract==composition,"all other492 devices and all contract metadata unchanged")
    require(all(d["model"]=="rppd" and set(k for k in d["old"]if d["old"][k]!=d["new"][k])=={"l"}for d in delta),"only8 resistor length changes")
    require([d for d in changed["device_records"]if d["model"]=="sg13_lv_nmos"]==[d for d in composition["device_records"]if d["model"]=="sg13_lv_nmos"],"all actual MOS cards and geometry unchanged")

    dest=host.NATIVE/"provisional-bias-model";dest.mkdir()
    (dest/"model.spice").write_bytes(modified);host.save(dest/"composition.json",changed)
    result=dict(model=str(dest/"model.spice"),composition=str(dest/"composition.json"),planes=paths["planes"])
    require(all(host.pin(paths[k])==parent_pins[k]for k in paths),"parent files untouched")
    receipt=dict(status="DERIVED_PROVISIONAL_SLAVE_LOAD_ONLY_TRIAL",scope=SCOPE,parent_rc_producer=parent_basis["producer"]["run"],parent_layout=parent_basis["candidate"],parent_inputs=parent_pins,trial_inputs={k:host.pin(p)for k,p in result.items()},delta=delta,entire_model_exact_reversal=True,all_other492_devices_unchanged=True,all_parent_wire_RC_cards_unchanged=True,original_measurement_limits_unchanged=True,closed_loop=False,**FLAGS)
    receipt_path=host.DERIVED/"provisional-bias-derivation.json";host.save(receipt_path,receipt)
    b=copy.deepcopy(parent_basis);ctx=host.context()
    b["producer"]=dict(source=ctx["source"],run=ctx["run_id"],release=host.release_gate()["id"])
    b["inputs"]={k:dict(path=p,**host.pin(p))for k,p in result.items()}
    protected={str(Path(p)):parent_pins[k]for k,p in paths.items()};protected[str(receipt_path)]=host.pin(receipt_path)
    return result,b,protected
