#!/usr/bin/env python3
"""Physical HBT emitter-count repair over authenticated twelve-divider PD650."""
import copy,json,re
from pathlib import Path
import cdr_divider_drive_candidate as parent
original=parent.original
require=parent.require
encode=parent.encode
digest=parent.digest
cloned=parent.cloned
BUFFER_IDS={123,125,128,130,131,132,149,150}
SELECTOR_IDS={137,139,142,143,155,157,160,161}
XOR_IDS=set(range(133,149))|set(range(151,167))
CHANGES={i:("2","1")for i in BUFFER_IDS}
CHANGES.update({i:(("6","2")if i in SELECTOR_IDS else("4","1"))for i in XOR_IDS})
GOLDEN="0a2ce363d3f8159a290f8642fe3a26c7ac1997ca4d8b934e4530fb4823974ef3"
TARGET_FILE="scripts/cdr-hbt-load-targets.json"
SCOPE="Exploratory PD650 HBT load repair:40 actual buffer/XOR HBT Nx changes over authenticated twelve-divider/200MOS candidate. Original voltages,per-emitter current,data,phase and timing gates retained. Distributed wire RC retained only for screening; changed geometry requires regenerated layout and fresh PEX. No closed-loop CDR or full PHY acceptance."
def rewrite(text,contract,root=original.frozen.ROOT):
    spec=json.loads((Path(root)/TARGET_FILE).read_bytes())
    require(spec["schema"]=="pd650-hbt-load-targets-v1" and spec["producer_run"]==41295928971 and spec["producer_model_sha256"]==GOLDEN,"exact native parent target specification")
    targets={d["native_id"]:d for d in spec["targets"]}
    require(len(spec["targets"])==len(targets)==40 and set(targets)==set(CHANGES),"all40 unique physical targets")
    rows=contract["device_records"]
    require(len(rows)in(500,650) and contract["counts"]["devices"]==len(rows) and len({d["native_id"]for d in rows})==len(rows),"complete unique500/650 identity census")
    chosen={d["native_id"]:d for d in rows if d["native_id"]in CHANGES}
    require(set(chosen)==set(CHANGES),"exact40 HBT identities")
    result=text;updated=copy.deepcopy(contract);changes=[]
    for ident,(old,new)in sorted(CHANGES.items()):
        d=chosen[ident];target=targets[ident];name="XD"+format(ident,"04d")
        require(d["instance"]==target["instance"]==name and d["model"]==target["model"]=="npn13g2","exact HBT identity and model")
        require(d["parameters"]==target["parameters"]==dict(le="0.900u",nx=old,we="0.070u"),"exact old geometry and emitter count")
        ts=d["terminals"]
        actual=[{k:t[k]for k in("terminal","native_net","native_cluster","node")}for t in ts]
        require(actual==target["terminals"] and [t["terminal"]for t in ts]==["C","B","E","S"],"all ordered physical HBT terminals unchanged")
        found=list(re.finditer(r"(?mi)^"+name+r"[ \t][^\r\n]*(?:\r?\n\+[^\r\n]*)*",result))
        require(len(found)==1,"unique HBT card")
        match=found[0];before=match.group();words=re.sub(r"\r?\n\+"," ",before).split()
        require(words[:6]==[name,*[t["node"]for t in ts],"npn13g2"],"exact ordered HBT card nodes")
        require(len(words[6:])==3 and set(words[6:])=={k+"="+v for k,v in d["parameters"].items()},"complete original HBT card parameters")
        after,n=re.subn(r"(?<!\S)nx="+old+r"(?=\s|$)","nx="+new,before)
        require(n==1,"exactly one physical Nx token")
        result=result[:match.start()]+after+result[match.end():]
        next(x for x in updated["device_records"]if x["native_id"]==ident)["parameters"]["nx"]=new
        changes.append(dict(native_id=ident,before=before,after=after,old_nx=old,new_nx=new))
    reverse=result
    for change in changes:
        require(reverse.count(change["after"])==1,"unique reverse HBT card")
        reverse=reverse.replace(change["after"],change["before"],1)
    require(reverse==text,"all other model bytes including RC preserved")
    undo=copy.deepcopy(updated)
    for d in undo["device_records"]:
        if d["native_id"]in CHANGES:d["parameters"]["nx"]=CHANGES[d["native_id"]][0]
    require(undo==contract,"all non-Nx descriptor values preserved")
    return result,updated,dict(changes=changes,original_model_sha256=digest(text.encode()),candidate_model_sha256=digest(result.encode()),all_other_model_bytes_preserved=True,wire_rc_recomputed=False,layout_regenerated=False,physical_acceptance=False,full_phy_accepted=False,final_timing_complete=False)
def derive(text,contract,root=original.frozen.ROOT,native=True):
    s=parent.derive(text,contract,root,native=native)
    if native:require(digest(s["text"].encode())==GOLDEN,"exact published twelve-divider native parent")
    golden=copy.deepcopy(s["summary"])
    s["baseline_text"],s["baseline_contract"],base_delta=rewrite(s["baseline_text"],s["baseline_contract"],root)
    s["text"],s["contract"],delta=rewrite(s["text"],s["contract"],root)
    require(base_delta["changes"]==delta["changes"],"same40 HBT changes in binder and650 model")
    s["summary"]=dict(golden_divider_pd650=golden,hbt_delta=delta,binder_delta=base_delta,candidate_model_sha256=digest(s["text"].encode()),candidate_composition_sha256=digest(encode(s["contract"])),candidate_devices=650,mos_units=200,mos_origins=50,hbt_devices=124,hbt_nx_changes=40,scope=SCOPE,all_other_model_bytes_preserved=True,wire_rc_recomputed=False,layout_regenerated=False,physical_acceptance=False,full_phy_accepted=False,final_timing_complete=False)
    return s
def variant(baseline_paths,candidate_paths,root=original.frozen.ROOT):
    ns=dict(original.__dict__);ns["derive"]=derive
    functions=cloned(original.variant,ns)(baseline_paths,candidate_paths,root)
    old=functions["prepare_case"].__globals__["block"]
    def block(name,namespace,root=root):
        result=old(name,namespace,root)
        if name=="scenario":namespace["r"].update(scope=SCOPE,hbt_nx_delta_ids=sorted(CHANGES),hbt_nx_changes=40)
        return result
    adapted=dict(functions["prepare_case"].__globals__);adapted["block"]=block
    return {k:cloned(v,adapted)for k,v in functions.items()}
def materialize(baseline_paths,candidate_directory,root=original.frozen.ROOT):
    ns=dict(original.__dict__);ns["derive"]=derive
    return cloned(original.materialize,ns)(baseline_paths,candidate_directory,root)
