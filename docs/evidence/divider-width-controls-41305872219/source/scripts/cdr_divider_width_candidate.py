#!/usr/bin/env python3
"""Twelve physical divider widths over the authenticated PD650 parent."""
import copy,re
from pathlib import Path
import cdr_divider_drive_candidate as parent
original=parent.original
require=parent.require
encode=parent.encode
digest=parent.digest
cloned=parent.cloned
TARGETS=parent.TARGETS
GOLDEN="0a2ce363d3f8159a290f8642fe3a26c7ac1997ca4d8b934e4530fb4823974ef3"
SCOPE="Exploratory PD650 divider impedance trial:12 rppd widths1um to2um over the exact twelve-divider/200MOS parent. All lengths,ratios,HBT Nx,MOS units,ports and original electrical/current/data/phase gates retained. Existing distributed wire RC is screening only; changed geometry requires regenerated layout and fresh PEX. No closed-loop,full PHY,physical or final timing acceptance."
def rewrite(text,contract,root=original.frozen.ROOT):
    rows=contract["device_records"]
    require(len(rows)in(500,650)and contract["counts"]["devices"]==len(rows)and len({d["native_id"]for d in rows})==len(rows),"complete unique500/650 census")
    chosen={d["native_id"]:d for d in rows if d["native_id"]in TARGETS}
    require(len(chosen)==12 and set(chosen)==set(TARGETS),"exact12 divider identities")
    result=text;updated=copy.deepcopy(contract);changes=[]
    for ident,(_,length,first,second)in sorted(TARGETS.items()):
        d=chosen[ident];name="XD"+format(ident,"04d")
        require(d["instance"]==name and d["model"]=="rppd","exact divider instance/model")
        require(d["parameters"]==dict(b="0",l=length,m="1",ps="0u",sw_et="1",w="1u"),"exact parent divider parameters")
        ts=d["terminals"]
        require([(t["terminal"],t["native_net"],t["native_cluster"])for t in ts]==[("rppd_1",*first),("rppd_2",*second),("rppd_sub","$1",1)],"exact ordered physical divider terminals")
        found=list(re.finditer(r"(?mi)^"+name+r"[ \t][^\r\n]*(?:\r?\n\+[^\r\n]*)*",result))
        require(len(found)==1,"unique divider card")
        match=found[0];before=match.group();words=re.sub(r"\r?\n\+"," ",before).split()
        require(words[:5]==[name,*[t["node"]for t in ts],"rppd"],"exact ordered divider card nodes")
        require(len(words[5:])==len(d["parameters"])and set(words[5:])=={k+"="+v for k,v in d["parameters"].items()},"complete original card parameters")
        after,n=re.subn(r"(?<!\S)w=1u(?=\s|$)","w=2u",before)
        require(n==1,"one physical width token")
        result=result[:match.start()]+after+result[match.end():]
        next(x for x in updated["device_records"]if x["native_id"]==ident)["parameters"]["w"]="2u"
        changes.append(dict(native_id=ident,before=before,after=after,old_w="1u",new_w="2u",unchanged_l=length))
    reverse=result
    for change in changes:
        require(reverse.count(change["after"])==1,"unique reverse card")
        reverse=reverse.replace(change["after"],change["before"],1)
    require(reverse==text,"all unrelated model bytes including RC unchanged")
    undo=copy.deepcopy(updated)
    for d in undo["device_records"]:
        if d["native_id"]in TARGETS:d["parameters"]["w"]="1u"
    require(undo==contract,"all non-width descriptor values unchanged")
    return result,updated,dict(changes=changes,original_model_sha256=digest(text.encode()),candidate_model_sha256=digest(result.encode()),
        all_other_model_bytes_preserved=True,wire_rc_recomputed=False,layout_regenerated=False,physical_acceptance=False,full_phy_accepted=False,final_timing_complete=False)
def derive(text,contract,root=original.frozen.ROOT,native=True):
    s=parent.derive(text,contract,root,native=native)
    if native:require(digest(s["text"].encode())==GOLDEN,"exact published twelve-divider native parent")
    golden=copy.deepcopy(s["summary"])
    s["baseline_text"],s["baseline_contract"],base_delta=rewrite(s["baseline_text"],s["baseline_contract"],root)
    s["text"],s["contract"],delta=rewrite(s["text"],s["contract"],root)
    require(base_delta["changes"]==delta["changes"],"same12 width changes in binder and650 model")
    s["summary"]=dict(golden_divider_pd650=golden,divider_width_delta=delta,binder_delta=base_delta,
        candidate_model_sha256=digest(s["text"].encode()),candidate_composition_sha256=digest(encode(s["contract"])),
        candidate_devices=650,mos_units=200,mos_origins=50,hbt_devices=124,divider_width_changes=12,scope=SCOPE,
        all_other_model_bytes_preserved=True,wire_rc_recomputed=False,layout_regenerated=False,physical_acceptance=False,full_phy_accepted=False,final_timing_complete=False)
    return s
def variant(baseline_paths,candidate_paths,root=original.frozen.ROOT):
    ns=dict(original.__dict__);ns["derive"]=derive
    functions=cloned(original.variant,ns)(baseline_paths,candidate_paths,root)
    old=functions["prepare_case"].__globals__["block"]
    def block(name,namespace,root=root):
        result=old(name,namespace,root)
        if name=="scenario":namespace["r"].update(scope=SCOPE,divider_width_delta_ids=sorted(TARGETS),divider_width_changes=12)
        return result
    adapted=dict(functions["prepare_case"].__globals__);adapted["block"]=block
    return {k:cloned(v,adapted)for k,v in functions.items()}
def materialize(baseline_paths,candidate_directory,root=original.frozen.ROOT):
    ns=dict(original.__dict__);ns["derive"]=derive
    return cloned(original.materialize,ns)(baseline_paths,candidate_directory,root)
