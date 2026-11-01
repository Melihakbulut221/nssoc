#!/usr/bin/env python3
"""Four physical resistor parameter candidate; frozen original electrical tests.
Exploratory intrinsic-device change. Baseline interconnect remains unchanged;
this is NOT an extraction of a regenerated layout and cannot confer signoff.
"""
import copy, hashlib, json, re, types
from pathlib import Path
import cdr_via2_m3_loaded_core as frozen
TARGETS={184:("$99",22),185:("$98",21),222:("$652",122),223:("$651",121)}
def require(ok,message):
    if not ok:raise ValueError(message)
def digest(raw):return hashlib.sha256(raw).hexdigest()
def encode(value):return (json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+"\n").encode()
def rewrite(text,contract):
    """Change only four exact L tokens; keep all other SPICE bytes and JSON values."""
    rows=contract["device_records"]
    selected={d["native_id"]:d for d in rows if d["native_id"] in TARGETS}
    require(len(rows)==500 and len({d["native_id"] for d in rows})==500,"complete unique baseline device census")
    require(set(selected)==set(TARGETS),"four physical shunts")
    updated=copy.deepcopy(contract);changes=[];result=text
    for ident,(net,cluster) in TARGETS.items():
        d=selected[ident];name="XD"+format(ident,"04d")
        require(d["instance"]==name and d["model"]=="rppd","native resistor identity")
        require(d["parameters"]==dict(b="0",l="5u",m="1",ps="0u",sw_et="1",w="4u"),"exact original native resistor parameters")
        terminals=d["terminals"]
        require([(t["terminal"],t["native_net"],t["native_cluster"]) for t in terminals]==[
            ("rppd_1",net,cluster),("rppd_2","avss",23),("rppd_sub","$1",1)],"exact original shunt terminals")
        pattern=re.compile(r"(?mi)^"+re.escape(name)+r"[ \t][^\r\n]*(?:\r?\n\+[^\r\n]*)*")
        found=list(pattern.finditer(result));require(len(found)==1,"one original model card "+name)
        match=found[0];before=match.group()
        # Authenticate every token against the physical composition, not just L.
        words=re.sub(r"\r?\n\+"," ",before).split()
        require(words[:5]==[name,*[t["node"] for t in terminals],"rppd"],"ordered original native card")
        require(len(words[5:])==len(d["parameters"]) and set(words[5:])=={k+"="+v for k,v in d["parameters"].items()},"complete original card parameters")
        after,n=re.subn(r"(?<!\S)l=5u(?=\s|$)","l=7.4u",before)
        require(n==1,"one length replacement")
        result=result[:match.start()]+after+result[match.end():]
        target=next(x for x in updated["device_records"] if x["native_id"]==ident)
        target["parameters"]["l"]="7.4u"
        changes.append(dict(native_id=ident,instance=name,before=before,after=after,old_l_um=5,new_l_um=7.4,w_um=4))
    # Reverse exactly the four changes and demand identical original bytes.
    reverse=result
    for change in changes:
        require(reverse.count(change["after"])==1,"unique changed card")
        reverse=reverse.replace(change["after"],change["before"],1)
    require(reverse==text,"no unrelated SPICE mutation")
    undo=copy.deepcopy(updated)
    for d in undo["device_records"]:
        if d["native_id"] in TARGETS:d["parameters"]["l"]="5u"
    require(undo==contract,"no unrelated composition mutation")
    return result,updated,dict(changes=changes,original_model_sha256=digest(text.encode()),candidate_model_sha256=digest(result.encode()),
        original_composition_sha256=digest(encode(contract)),candidate_composition_sha256=digest(encode(updated)),
        wire_rc_recomputed=False,physical_acceptance=False,full_phy_accepted=False,final_timing_complete=False)
def variant(baseline_paths,candidate_paths,root=frozen.ROOT):
    """Clone unchanged original functions into an explicit candidate namespace.
    Original module globals, function bodies, stimulus, and acceptance predicates
    remain intact. Candidate input verification always authenticates the baseline
    first and then derives the exact four-token delta again.
    """
    require(set(baseline_paths)==set(candidate_paths)=={"model","composition","planes"},"explicit complete paths")
    require(all(Path(v).is_absolute() and Path(v).resolve()==Path(v) for v in [*baseline_paths.values(),*candidate_paths.values()]),"unaliased absolute paths")
    require(set(map(str,baseline_paths.values())).isdisjoint(set(map(str,candidate_paths.values()))),"original files cannot be overwritten")
    def verify(paths,root=root):
        require({k:str(v) for k,v in paths.items()}=={k:str(v) for k,v in candidate_paths.items()},"exact candidate paths")
        c,records,contract,planes=frozen.verify_current_inputs(baseline_paths,root)
        text=Path(baseline_paths["model"]).read_text()
        changed,updated,delta=rewrite(text,contract)
        require(Path(paths["model"]).read_bytes()==changed.encode(),"complete candidate model bytes")
        require(Path(paths["composition"]).read_bytes()==encode(updated),"complete candidate composition bytes")
        require(Path(paths["planes"]).read_bytes()==Path(baseline_paths["planes"]).read_bytes(),"unchanged native planes")
        return c,records,updated,planes
    def block(name,namespace,root=root):
        answer=frozen.block(name,namespace,root)
        if name=="scenario":
            namespace["r"].update(scope="Exploratory four-shunt intrinsic length candidate with baseline distributed RC; original whole-model electrical predicates. Not regenerated-layout PEX.",
                circuit_candidate=dict(native_ids=sorted(TARGETS),old_l_um=5,new_l_um=7.4,w_um=4),
                baseline_wire_rc_retained=True,wire_rc_recomputed=False,layout_regenerated=False,physical_acceptance=False)
        return answer
    ns=dict(frozen.__dict__)
    ns.update(verify_current_inputs=verify,block=block)
    result={}
    for name in ("prepare_case","measure_case"):
        original=getattr(frozen,name)
        clone=types.FunctionType(original.__code__,ns,original.__name__,original.__defaults__,original.__closure__)
        clone.__kwdefaults__=original.__kwdefaults__
        require(clone.__code__ is original.__code__,"identical frozen executable body")
        result[name]=clone
    return result
def materialize(baseline_paths,candidate_directory,root=frozen.ROOT):
    _,_,contract,_=frozen.verify_current_inputs(baseline_paths,root)
    text=Path(baseline_paths["model"]).read_text()
    changed,updated,delta=rewrite(text,contract)
    out=Path(candidate_directory);require(out.is_absolute() and out.resolve()==out,"owned candidate directory")
    out.mkdir(exist_ok=False)
    paths=dict(model=str(out/"model.spice"),composition=str(out/"composition.json"),planes=str(out/"planes.json"))
    for role,raw in (("model",changed.encode()),("composition",encode(updated)),("planes",Path(baseline_paths["planes"]).read_bytes())):
        with Path(paths[role]).open("xb") as stream:stream.write(raw)
    frozen.write_exclusive(out/"delta.json",delta)
    return paths,delta
