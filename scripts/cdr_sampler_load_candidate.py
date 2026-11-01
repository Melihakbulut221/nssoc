#!/usr/bin/env python3
"""Mixed A/B output loads and original C/D output loads; eight A/C divider lengths; original gates.
Baseline distributed RC is retained. Not regenerated-layout PEX or signoff.
"""
import copy,hashlib,json,re,types
from pathlib import Path
import cdr_via2_m3_loaded_core as frozen
# id: old length, candidate length, unchanged width, ordered terminal net/cluster
TARGETS={
 191:("2.6u","1.5u","32u",("avdd",16),("$285",58)),
 194:("2.6u","1.5u","32u",("avdd",16),("$286",59)),
 202:("2.6u","1.5u","32u",("avdd",16),("$449",87)),
 205:("2.6u","1.5u","32u",("avdd",16),("$450",88)),
 182:("1.8u","1.0u","8u",("avdd",16),("$99",22)),
 183:("1.8u","1.0u","8u",("avdd",16),("$98",21)),
 220:("1.8u","1.0u","8u",("avdd",16),("$652",122)),
 221:("1.8u","1.0u","8u",("avdd",16),("$651",121)),
 184:("5u","3.4u","4u",("$99",22),("avss",23)),
 185:("5u","3.4u","4u",("$98",21),("avss",23)),
 222:("5u","3.4u","4u",("$652",122),("avss",23)),
 223:("5u","3.4u","4u",("$651",121),("avss",23)),
 227:("3.6u","1.8u","1u",("$450",88),("$787",139)),
 228:("21.6u","10.8u","1u",("$787",139),("avss",23)),
 229:("3.6u","1.8u","1u",("$449",87),("$788",140)),
 230:("21.6u","10.8u","1u",("$788",140),("avss",23)),
 238:("3.6u","1.8u","1u",("$623",118),("$869",152)),
 239:("21.6u","10.8u","1u",("$869",152),("avss",23)),
 240:("3.6u","1.8u","1u",("$622",117),("$870",153)),
 241:("21.6u","10.8u","1u",("$870",153),("avss",23)),
}
def require(ok,message):
    if not ok:raise ValueError(message)
def digest(raw):return hashlib.sha256(raw).hexdigest()
def encode(value):return(json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+"\n").encode()
def rewrite(text,contract):
    rows=contract["device_records"]
    require(len(rows)==500 and len({d["native_id"]for d in rows})==500,"complete unique original500 devices")
    selected={d["native_id"]:d for d in rows if d["native_id"]in TARGETS}
    require(set(selected)==set(TARGETS)and len(selected)==20,"exact20 physical resistor identities")
    updated=copy.deepcopy(contract);result=text;changes=[]
    for ident,(old,new,width,first,second)in TARGETS.items():
        d=selected[ident];name="XD"+format(ident,"04d")
        require(d["instance"]==name and d["model"]=="rppd","native resistor identity")
        require(d["parameters"]==dict(b="0",l=old,m="1",ps="0u",sw_et="1",w=width),"exact original resistor parameters")
        terminals=d["terminals"]
        require([(t["terminal"],t["native_net"],t["native_cluster"])for t in terminals]==[
          ("rppd_1",*first),("rppd_2",*second),("rppd_sub","$1",1)],"exact ordered native terminals")
        pattern=re.compile(r"(?mi)^"+re.escape(name)+r"[ \t][^\r\n]*(?:\r?\n\+[^\r\n]*)*")
        found=list(pattern.finditer(result));require(len(found)==1,"one exact native card "+name)
        match=found[0];before=match.group();words=re.sub(r"\r?\n\+"," ",before).split()
        require(words[:5]==[name,*[t["node"]for t in terminals],"rppd"],"complete ordered original card")
        require(len(words[5:])==len(d["parameters"])and set(words[5:])=={k+"="+v for k,v in d["parameters"].items()},"complete original parameter tokens")
        after,n=re.subn(r"(?<!\S)l="+re.escape(old)+r"(?=\s|$)","l="+new,before)
        require(n==1,"one length token only")
        result=result[:match.start()]+after+result[match.end():]
        next(x for x in updated["device_records"]if x["native_id"]==ident)["parameters"]["l"]=new
        changes.append(dict(native_id=ident,instance=name,before=before,after=after,old_l=old,new_l=new,w=width))
    reverse=result
    for change in changes:
        require(reverse.count(change["after"])==1,"unique changed card")
        reverse=reverse.replace(change["after"],change["before"],1)
    require(reverse==text,"all unrelated model bytes identical")
    undo=copy.deepcopy(updated)
    for d in undo["device_records"]:
        if d["native_id"]in TARGETS:d["parameters"]["l"]=TARGETS[d["native_id"]][0]
    require(undo==contract,"all unrelated composition values identical")
    return result,updated,dict(changes=changes,original_model_sha256=digest(text.encode()),candidate_model_sha256=digest(result.encode()),
      original_composition_sha256=digest(encode(contract)),candidate_composition_sha256=digest(encode(updated)),
      wire_rc_recomputed=False,layout_regenerated=False,physical_acceptance=False,full_phy_accepted=False,final_timing_complete=False)
def variant(baseline_paths,candidate_paths,root=frozen.ROOT):
    """Clone unchanged original functions into an explicit candidate namespace.
    Original module globals, function bodies, stimulus, and acceptance predicates
    remain intact. Candidate input verification always authenticates the baseline
    first and then derives the exact twenty-token delta again.
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
            namespace["r"].update(scope="Exploratory mixed A/B output loads with original C/D outputs and masters plus half-length A/C dividers with baseline distributed RC; original whole-model electrical predicates. Not regenerated-layout PEX.",
                circuit_candidate=dict(native_ids=sorted(TARGETS),four_ab_output_loads_l_um=[2.6,1.5],unchanged_cd_output_ids=[175,176,212,214],four_buffer_loads_l_um=[1.8,1.0],four_shunts_l_um=[5,3.4],ac_series_l_um=[3.6,1.8],ac_shunts_l_um=[21.6,10.8],unchanged_divider_width_um=1),
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
