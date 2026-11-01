#!/usr/bin/env python3
"""A/C buffer drive trial over the immutable width2 PD650 parent."""
import copy,json,re
from pathlib import Path
import cdr_divider_width_candidate as parent
original=parent.original
require=parent.require
encode=parent.encode
digest=parent.digest
cloned=parent.cloned
TARGET_FILE="scripts/cdr-buffer-drive-targets.json"
CHANGES={126:("nx","4","8"),129:("nx","4","8"),
         232:("l","1.8u","0.9u"),233:("l","1.8u","0.9u"),
         243:("l","1.8u","0.9u"),244:("l","1.8u","0.9u")}
SCOPE="Exploratory width2 PD650 A/C buffer drive trial:two tail HBT Nx4 to8 and four collector rppd lengths1.8um to0.9um, widths8um retained. Original electrical/current/data/phase gates and 200MOS units unchanged. Retained distributed RC is screening only; changed geometry needs regenerated layout and fresh PEX. No full PHY,physical or final timing acceptance."
def rewrite(text,contract,root=original.frozen.ROOT):
    spec=json.loads((Path(root)/TARGET_FILE).read_bytes())
    require(spec["schema"]=="pd650-buffer-drive-targets-v1" and spec["parent_source"]=="2a62d651d415fba8db3c5b758d1b66c05cde3a38","exact width2 source")
    targets={d["native_id"]:d for d in spec["targets"]}
    require(len(spec["targets"])==len(targets)==6 and set(targets)==set(CHANGES),"six unique physical targets")
    rows=contract["device_records"]
    require(len(rows)in(500,650) and contract["counts"]["devices"]==len(rows) and len({d["native_id"]for d in rows})==len(rows),"complete unique500/650 census")
    chosen={d["native_id"]:d for d in rows if d["native_id"]in CHANGES}
    require(set(chosen)==set(CHANGES),"exact six identities")
    result=text;updated=copy.deepcopy(contract);changes=[]
    for ident,(key,old,new)in sorted(CHANGES.items()):
        d=chosen[ident];name="XD"+format(ident,"04d")
        require(d==targets[ident] and d["instance"]==name,"complete original physical target record")
        require(d["parameters"][key]==old,"exact parent parameter")
        ts=d["terminals"]
        found=list(re.finditer(r"(?mi)^"+name+r"[ \t][^\r\n]*(?:\r?\n\+[^\r\n]*)*",result))
        require(len(found)==1,"unique target card")
        match=found[0];before=match.group();words=re.sub(r"\r?\n\+"," ",before).split()
        offset=2+len(ts)
        require(words[:offset]==[name,*[t["node"]for t in ts],d["model"]],"exact ordered physical card")
        require(len(words[offset:])==len(d["parameters"])and set(words[offset:])=={k+"="+v for k,v in d["parameters"].items()},"complete original card parameters")
        after,n=re.subn(r"(?<!\S)"+key+"="+re.escape(old)+r"(?=\s|$)",key+"="+new,before)
        require(n==1,"one targeted parameter")
        result=result[:match.start()]+after+result[match.end():]
        next(x for x in updated["device_records"]if x["native_id"]==ident)["parameters"][key]=new
        changes.append(dict(native_id=ident,parameter=key,old=old,new=new,before=before,after=after))
    reverse=result
    for change in changes:
        require(reverse.count(change["after"])==1,"unique reverse card")
        reverse=reverse.replace(change["after"],change["before"],1)
    require(reverse==text,"all unrelated native model bytes preserved")
    undo=copy.deepcopy(updated)
    for d in undo["device_records"]:
        if d["native_id"]in CHANGES:
            key,old,_=CHANGES[d["native_id"]];d["parameters"][key]=old
    require(undo==contract,"all unrelated descriptors preserved")
    return result,updated,dict(changes=changes,original_model_sha256=digest(text.encode()),candidate_model_sha256=digest(result.encode()),
        all_other_model_bytes_preserved=True,wire_rc_recomputed=False,layout_regenerated=False,physical_acceptance=False,full_phy_accepted=False,final_timing_complete=False)
def derive(text,contract,root=original.frozen.ROOT,native=True):
    s=parent.derive(text,contract,root,native=native)
    golden=copy.deepcopy(s["summary"])
    s["baseline_text"],s["baseline_contract"],base_delta=rewrite(s["baseline_text"],s["baseline_contract"],root)
    s["text"],s["contract"],delta=rewrite(s["text"],s["contract"],root)
    require(base_delta["changes"]==delta["changes"],"same six changes in binder and650 native model")
    s["summary"]=dict(width2_parent=golden,buffer_drive_delta=delta,binder_delta=base_delta,
        candidate_model_sha256=digest(s["text"].encode()),candidate_composition_sha256=digest(encode(s["contract"])),
        candidate_devices=650,mos_units=200,mos_origins=50,hbt_devices=124,buffer_drive_changes=6,scope=SCOPE,
        all_other_model_bytes_preserved=True,wire_rc_recomputed=False,layout_regenerated=False,physical_acceptance=False,full_phy_accepted=False,final_timing_complete=False)
    return s
def variant(baseline_paths,candidate_paths,root=original.frozen.ROOT):
    ns=dict(original.__dict__);ns["derive"]=derive
    functions=cloned(original.variant,ns)(baseline_paths,candidate_paths,root)
    old=functions["prepare_case"].__globals__["block"]
    def block(name,namespace,root=root):
        result=old(name,namespace,root)
        if name=="scenario":namespace["r"].update(scope=SCOPE,buffer_drive_delta_ids=sorted(CHANGES),buffer_drive_changes=6)
        return result
    adapted=dict(functions["prepare_case"].__globals__);adapted["block"]=block
    return {k:cloned(v,adapted)for k,v in functions.items()}
def materialize(baseline_paths,candidate_directory,root=original.frozen.ROOT):
    ns=dict(original.__dict__);ns["derive"]=derive
    return cloned(original.materialize,ns)(baseline_paths,candidate_directory,root)
