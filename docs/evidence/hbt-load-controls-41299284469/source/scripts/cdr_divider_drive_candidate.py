#!/usr/bin/env python3
"""Twelve lower-impedance dividers over authenticated PD650; original gates."""
import copy,re,types
from pathlib import Path
import cdr_sampler_load_candidate as original
require=original.require
encode=original.encode
digest=original.digest
TARGETS={
227:("1.8u","0.9u",("$450",88),("$787",139)),
228:("10.8u","5.4u",("$787",139),("avss",23)),
229:("1.8u","0.9u",("$449",87),("$788",140)),
230:("10.8u","5.4u",("$788",140),("avss",23)),
234:("6u","3u",("$70",18),("$851",150)),
235:("8.6u","4.3u",("$851",150),("avss",23)),
236:("6u","3u",("$69",17),("$852",151)),
237:("8.6u","4.3u",("$852",151),("avss",23)),
238:("1.8u","0.9u",("$623",118),("$869",152)),
239:("10.8u","5.4u",("$869",152),("avss",23)),
240:("1.8u","0.9u",("$622",117),("$870",153)),
241:("10.8u","5.4u",("$870",153),("avss",23)),
}
SCOPE="Exploratory PD650:12 A/C data and D selector divider resistors halved from authenticated mixed20/200MOS model;24 unique resistor changes versus original500. Original electrical gates,200MOS,RC and ports retained. No regenerated layout,fresh PEX,closed loop or full PHY acceptance."
def rewrite(text,contract):
    rows=contract["device_records"]
    require(len(rows)in(500,650) and contract["counts"]["devices"]==len(rows) and len({d["native_id"]for d in rows})==len(rows),"complete unique500/650 identity census")
    chosen={d["native_id"]:d for d in rows if d["native_id"]in TARGETS}
    require(set(chosen)==set(TARGETS),"exact12 divider identities")
    result=text;updated=copy.deepcopy(contract);changes=[]
    for ident,(old,new,first,second)in TARGETS.items():
        d=chosen[ident];name="XD"+format(ident,"04d")
        require(d["instance"]==name and d["model"]=="rppd","exact divider model and identity")
        require(d["parameters"]==dict(b="0",l=old,m="1",ps="0u",sw_et="1",w="1u"),"exact divider parameters")
        ts=d["terminals"]
        require([(t["terminal"],t["native_net"],t["native_cluster"])for t in ts]==[("rppd_1",*first),("rppd_2",*second),("rppd_sub","$1",1)],"exact ordered physical divider terminals")
        found=list(re.finditer(r"(?mi)^"+name+r"[ \t][^\r\n]*(?:\r?\n\+[^\r\n]*)*",result))
        require(len(found)==1,"unique divider card")
        m=found[0];before=m.group();words=re.sub(r"\r?\n\+"," ",before).split()
        require(words[:5]==[name,*[t["node"]for t in ts],"rppd"],"exact ordered card nodes")
        require(len(words[5:])==len(d["parameters"]) and set(words[5:])=={k+"="+v for k,v in d["parameters"].items()},"exact complete card parameters")
        after,n=re.subn(r"(?<!\S)l="+re.escape(old)+r"(?=\s|$)","l="+new,before)
        require(n==1,"one length token only")
        result=result[:m.start()]+after+result[m.end():]
        next(x for x in updated["device_records"]if x["native_id"]==ident)["parameters"]["l"]=new
        changes.append(dict(native_id=ident,before=before,after=after,old_l=old,new_l=new,w="1u"))
    reverse=result
    for change in changes:
        require(reverse.count(change["after"])==1,"unique reverse card")
        reverse=reverse.replace(change["after"],change["before"],1)
    require(reverse==text,"every unrelated model byte unchanged")
    undo=copy.deepcopy(updated)
    for d in undo["device_records"]:
        if d["native_id"]in TARGETS:d["parameters"]["l"]=TARGETS[d["native_id"]][0]
    require(undo==contract,"every unrelated descriptor value unchanged")
    return result,updated,dict(changes=changes,original_model_sha256=digest(text.encode()),candidate_model_sha256=digest(result.encode()),original_composition_sha256=digest(encode(contract)),candidate_composition_sha256=digest(encode(updated)),all_other_model_bytes_preserved=True,wire_rc_recomputed=False,layout_regenerated=False,physical_acceptance=False,full_phy_accepted=False,final_timing_complete=False)
def derive(text,contract,root=original.frozen.ROOT,native=True):
    s=original.derive(text,contract,root,native=native)
    golden=copy.deepcopy(s["summary"])
    s["baseline_text"],s["baseline_contract"],base_delta=rewrite(s["baseline_text"],s["baseline_contract"])
    s["text"],s["contract"],delta=rewrite(s["text"],s["contract"])
    require(base_delta["changes"]==delta["changes"],"same resistor delta in baseline binder and650 model")
    s["summary"]=dict(golden_pd650=golden,divider_delta=delta,binder_delta=base_delta,candidate_model_sha256=digest(s["text"].encode()),candidate_composition_sha256=digest(encode(s["contract"])),candidate_devices=650,mos_units=200,mos_origins=50,unique_resistor_changes_vs_original500=24,scope=SCOPE,all_other_model_bytes_preserved=True,wire_rc_recomputed=False,layout_regenerated=False,physical_acceptance=False,full_phy_accepted=False,final_timing_complete=False)
    return s
def cloned(fn,ns):
    result=types.FunctionType(fn.__code__,ns,fn.__name__,fn.__defaults__,fn.__closure__)
    result.__kwdefaults__=fn.__kwdefaults__
    return result
def variant(baseline_paths,candidate_paths,root=original.frozen.ROOT):
    ns=dict(original.__dict__);ns["derive"]=derive
    functions=cloned(original.variant,ns)(baseline_paths,candidate_paths,root)
    old=functions["prepare_case"].__globals__["block"]
    def block(name,namespace,root=root):
        result=old(name,namespace,root)
        if name=="scenario":namespace["r"].update(scope=SCOPE,divider_delta_ids=sorted(TARGETS),unique_resistor_changes_vs_original500=24)
        return result
    adapted=dict(functions["prepare_case"].__globals__);adapted["block"]=block
    return {k:cloned(v,adapted)for k,v in functions.items()}
def materialize(baseline_paths,candidate_directory,root=original.frozen.ROOT):
    ns=dict(original.__dict__);ns["derive"]=derive
    return cloned(original.materialize,ns)(baseline_paths,candidate_directory,root)
