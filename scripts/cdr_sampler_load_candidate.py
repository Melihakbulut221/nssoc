#!/usr/bin/env python3
"""Explicit 50-origin/200-unit MOS adapter. Original electrical gates retained."""
import copy,json,re,types
from collections import Counter
from pathlib import Path
import cdr_via2_m3_loaded_core as frozen
import cdr_sampler_load_resistor_base as resistor
import mos_model_domain_audit as physical
require=physical.require
encode=physical.enc
digest=physical.sha
PHYSICAL="docs/evidence/cdr-mos-parallel-inputs/physical-locations.json"
PHYSICAL_SHA="26d2cba6544ae2d8a871f0fe81b504e085045af070a92d614dbe7c35a030d800"
CANDIDATE_SHA="7787330b1bd617a1da93ca6cce0c1b4b3d874a4299cde70733f32fd9fc0b4150"
def locations(root):
    p=Path(root)/PHYSICAL
    require(frozen.file_pin(p)==dict(bytes=686559,sha256=PHYSICAL_SHA),"exact complete physical locations")
    return json.loads(p.read_bytes())
def derive(original_text,original_contract,root=frozen.ROOT,native=True):
    text,contract,res_delta=resistor.rewrite(original_text,original_contract)
    joined=physical.joined_mos(contract,locations(root));plan=physical.make_plan(joined)
    candidate,expansion,deltas=physical.rewrite_parallel(text,contract,plan,joined)
    updated=copy.deepcopy(contract);updated["counts"]["devices"]=650;updated["device_records"]=[]
    for row in expansion:
        d=copy.deepcopy(row["device"])
        if row["source_native_id"]in {p["native_id"]for p in plan}:
            d["native_id"]=row["candidate_instance"];d["source_native_id"]=row["source_native_id"]
        updated["device_records"].append(d)
    require(len(updated["device_records"])==len({d["native_id"]for d in updated["device_records"]})==650,"unique explicit650 device identities")
    if native:
        require(digest(text.encode())=="4b5c155517c81990e528190b6ebd0405a876184da57224233fd1f05ae25d658b","actual mixed20 model byte identity")
        require(digest(candidate.encode())==CANDIDATE_SHA,"actual published parallel candidate identity")
    summary=dict(original_model_sha256=digest(original_text.encode()),mixed20_model_sha256=digest(text.encode()),
        candidate_model_sha256=digest(candidate.encode()),original_devices=500,mos_origins=50,mos_units=200,candidate_devices=650,
        original_resistor_delta=res_delta,mos_origin_to_units={str(p["native_id"]):[u["instance"]for u in p["units"]]for p in plan},
        original_composition_sha256=digest(encode(original_contract)),candidate_composition_sha256=digest(encode(updated)),
        all_other_model_bytes_preserved=True,wire_rc_recomputed=False,layout_regenerated=False,physical_acceptance=False,full_phy_accepted=False,final_timing_complete=False)
    return dict(baseline_text=text,baseline_contract=contract,text=candidate,contract=updated,plan=plan,summary=summary)
def expanded_bind(text,contract,planes,state,ns):
    require(text==state["text"]and contract==state["contract"],"complete derived candidate model and composition")
    baseline=ns["bind_native"](state["baseline_text"],state["baseline_contract"],planes)
    rows=ns["parser"].statements(text);cards={r[0].lower():r for r in rows[1:-1]}
    require(len(cards)==len(rows)-2 and rows[0]==[".subckt",ns["MODEL"],*contract["interface"]]and rows[-1]==[".ends",ns["MODEL"]],"complete candidate statements and interface")
    require(Counter(r[0][0]for r in rows[1:-1])==dict(X=650,R=contract["counts"]["R"],C=contract["counts"]["C"]),"complete unchanged RC and650 native card census")
    require({k for k in cards if k.startswith("x")}=={d["instance"].lower()for d in contract["device_records"]},"complete650 instance binding")
    for d in contract["device_records"]:
        f=cards[d["instance"].lower()];n=len(d["terminals"])
        require(f[1:n+1]==[t["node"]for t in d["terminals"]]and f[n+1]==d["model"],"every650 ordered terminal and model")
        p=dict(x.split("=")for x in f[n+2:]);require(len(p)==len(f[n+2:])and p==d["parameters"],"every650 exact parameter set")
    bound=copy.deepcopy(baseline);bound["groups"]["sg13_lv_nmos"]={};mapping={}
    for p in state["plan"]:
        old="xpd."+p["source_instance"].lower();origin=baseline["groups"]["sg13_lv_nmos"][old];mapping[old]=[]
        for i,u in enumerate(p["units"]):
            name="xpd."+u["instance"].lower()
            d=copy.deepcopy(origin);d.update(parameters=copy.deepcopy(u["parameters"]),native_id=u["instance"],source_native_id=p["native_id"],source_instance=p["source_instance"],unit_index=i)
            bound["groups"]["sg13_lv_nmos"][name]=d;mapping[old].append(name)
    require(set(mapping)==set(baseline["groups"]["sg13_lv_nmos"])and len(bound["groups"]["sg13_lv_nmos"])==200,"every50 origin mapped to all200 units")
    bound["mos_tail_names"]=[u for old in baseline["mos_tail_names"]for u in mapping[old]]
    bound["mos_tail_groups"]={k:[u for old in origins for u in mapping[old]]for k,origins in baseline["mos_tail_groups"].items()}
    require(len(bound["mos_tail_names"])==len(set(bound["mos_tail_names"]))==192 and len(bound["mos_tail_groups"])==16,"all192 unit tails and original16 groups")
    require(Counter(u for names in bound["mos_tail_groups"].values()for u in names)==Counter(bound["mos_tail_names"]),"each tail unit in exactly its original stage group")
    for k in baseline:
        if k not in ("groups","mos_tail_names","mos_tail_groups"):require(bound[k]==baseline[k],"unchanged original observation "+k)
    for k in baseline["groups"]:
        if k!="sg13_lv_nmos":require(bound["groups"][k]==baseline["groups"][k],"unchanged original device group "+k)
    bound["mos_origin_to_units"]=mapping
    bound["original_mos_tail_names"]=baseline["mos_tail_names"]
    bound["original_mos_tail_groups"]=baseline["mos_tail_groups"]
    return bound
def expansion_controls(text,contract,planes,state,ns):
    rejected=[]
    def reject(label,t,c):
        try:expanded_bind(t,c,planes,state,ns)
        except (ValueError,AssertionError):rejected.append(label)
        else:raise ValueError("accepted corrupt candidate "+label)
    first=state["plan"][0]["units"][0];name=first["instance"]
    line=next(l for l in text.splitlines()if l.startswith(name+" "))
    reject("missing unit",text.replace(line+"\n","",1),contract)
    reject("duplicate unit",text+line+"\n",contract)
    reject("changed unit terminal",text.replace(line,line.replace(first["terminals"][0]["node"],"wrong",1),1),contract)
    reject("changed unit width",text.replace(line,line.replace("w="+first["parameters"]["w"],"w=54u",1),1),contract)
    reject("stale junction area",text.replace(line,line+" as=18.1339p",1),contract)
    reject("extra native parameter",text.replace(line,line+" extra=1",1),contract)
    reject("changed original resistor",text.replace("XD0175 ","XD9999 ",1),contract)
    wrong=copy.deepcopy(contract);wrong["device_records"].pop();reject("missing composition device",text,wrong)
    wrong=copy.deepcopy(contract);wrong["counts"]["devices"]=500;reject("stale500 descriptor",text,wrong)
    wrong=copy.deepcopy(contract);d=next(x for x in wrong["device_records"]if x["instance"]==name);d["source_native_id"]=-1;reject("wrong origin",text,wrong)
    wrong=copy.deepcopy(contract);d=next(x for x in wrong["device_records"]if x["instance"]==name);d["terminals"][0]["native_cluster"]=-1;reject("wrong native cluster",text,wrong)
    wrong=copy.deepcopy(contract);d=next(x for x in wrong["device_records"]if x["instance"]==name);d["parameters"]["ng"]="4";reject("metadata-only finger change",text,wrong)
    require(len(rejected)==12,"all12 candidate binding corruptions")
    return dict(rejected=rejected,checks=12,failures=0,scope="all650 candidate model and composition binding")
BLOCK_CHANGES={
 "deck":[("len(mos)==50","len(mos)==200"),("NSSOC actual whole MIM-aware PD500","NSSOC actual whole MIM-aware PD650")],
 "measurement":[("len(mos_checks)==50 and len(mos_tails)==42","len(mos_checks)==200 and len(mos_tails)==192"),
 ("PASS_WHOLE_MIM_PD500_LOADED_SCREEN_NOT_CLOSED_LOOP_OR_PHY_SIGNOFF","PASS_WHOLE_MIM_PD650_LOADED_SCREEN_NOT_CLOSED_LOOP_OR_PHY_SIGNOFF"),
 ("REJECTED_WHOLE_MIM_PD500_LOADED","REJECTED_WHOLE_MIM_PD650_LOADED")]
}
def adapted_text(name,root=frozen.ROOT):
    record=frozen.catalog(root)["blocks"][name];text,_=frozen.extract(record,root,True);out=text
    for old,new in BLOCK_CHANGES.get(name,[]):
        require(out.count(old)==1 and new not in out,"one explicit cardinality or status substitution")
        out=out.replace(old,new)
    reverse=out
    for old,new in reversed(BLOCK_CHANGES.get(name,[])):reverse=reverse.replace(new,old)
    require(reverse==text,"every other executable gate and stimulus byte unchanged")
    return out
def expected_projection(bound,projection):
    old=[f"@n.{name}.nsg13_lv_nmos[ids]"for name in bound["mos_origin_to_units"]]
    require(projection["vectors"][-50:]==old and projection["counts"]==dict(voltage_nodes=977,hbt_currents=124,mos_currents=50,total=1151,composition_wire_map_entries=15489),"original measured1151 vector identity")
    return projection["vectors"][:-50]+[f"@n.{name}.nsg13_lv_nmos[ids]"for name in bound["groups"]["sg13_lv_nmos"]]
def verify_projection(ns,projection):
    expected=expected_projection(ns["bound"],projection);vectors=ns["vectors"]
    require(vectors==expected and len(vectors)==len(set(vectors))==1301,"complete1301 projected vectors including200 actual currents")
    require(ns["bound"]["aliases"]=={name:row["loaded_node"]for name,row in projection["aliases"].items()},"all original actual collector aliases")
    require(ns["r"]["vector_census"]==dict(total=1301,voltage_nodes=977,hbt_collector_currents=124,mos_drain_currents=200,save_commands=len(ns["native_save_commands"](vectors))),"expanded exact census")
def namespace_for_state(state,root=frozen.ROOT,numpy=None):
    # Frozen definitions retain their ORIGINAL globals dictionary. Never update it.
    original=frozen.numerical_namespace(root,numpy)
    original_bind=original["bind_native"]
    require(original["binding_controls"].__globals__ is original,"original control namespace ownership")
    ns=dict(original)
    def bind(text,contract,planes):
        require(original["bind_native"] is original_bind,"baseline binder was not replaced")
        return expanded_bind(text,contract,planes,state,original)
    def controls(text,contract,planes):
        require(original["bind_native"] is original_bind,"baseline control binder remains original")
        base=original["binding_controls"](state["baseline_text"],state["baseline_contract"],planes)
        base.update(original_baseline_only=True,candidate_expansion=expansion_controls(text,contract,planes,state,original))
        return base
    ns.update(bind_native=bind,binding_controls=controls)
    require(ns is not original and original["bind_native"] is original_bind,"separate candidate namespace")
    return ns

def variant(baseline_paths,candidate_paths,root=frozen.ROOT):
    require(set(baseline_paths)==set(candidate_paths)=={"model","composition","planes"},"complete explicit paths")
    require(all(Path(v).is_absolute()and Path(v).resolve()==Path(v)for v in [*baseline_paths.values(),*candidate_paths.values()]),"unaliased absolute paths")
    require(set(map(str,baseline_paths.values())).isdisjoint(set(map(str,candidate_paths.values()))),"baseline cannot be overwritten")
    def state():
        c,records,contract,planes=frozen.verify_current_inputs(baseline_paths,root)
        return c,records,derive(Path(baseline_paths["model"]).read_text(),contract,root),planes
    def verify(paths,root=root):
        require({k:str(v)for k,v in paths.items()}=={k:str(v)for k,v in candidate_paths.items()},"exact candidate path set")
        c,records,s,planes=state()
        require(Path(paths["model"]).read_bytes()==s["text"].encode()and Path(paths["composition"]).read_bytes()==encode(s["contract"]),"actual published native model and full650 descriptor")
        require(Path(paths["planes"]).read_bytes()==Path(baseline_paths["planes"]).read_bytes(),"all original160 planes unchanged")
        return c,records,s["contract"],planes
    def numerical(root=root,numpy=None):
        _,_,s,_=state()
        return namespace_for_state(s,root,numpy)
    def block(name,namespace,root=root):
        if name in BLOCK_CHANGES:exec(compile(adapted_text(name,root),"<qualified-parallel-"+name+">","exec"),namespace)
        else:frozen.block(name,namespace,root)
        if name=="scenario":
            namespace["r"].update(scope="Exploratory PD650 explicit200MOS expansion of authenticated mixed20. Original total W/L and terminal connectivity; original distributed RC retained. Not regenerated layout, fresh PEX, closed loop or full PHY acceptance.",candidate_device_count=650,mos_units=200,mos_origins=50,baseline_wire_rc_retained=True,wire_rc_recomputed=False,layout_regenerated=False,physical_acceptance=False)
        return namespace
    ns=dict(frozen.__dict__);ns.update(verify_current_inputs=verify,numerical_namespace=numerical,block=block,verify_projection=verify_projection)
    result={}
    for name in ("prepare_case","measure_case"):
        old=getattr(frozen,name);new=types.FunctionType(old.__code__,ns,old.__name__,old.__defaults__,old.__closure__);new.__kwdefaults__=old.__kwdefaults__
        require(new.__code__ is old.__code__,"identical original orchestration body");result[name]=new
    return result
def materialize(baseline_paths,candidate_directory,root=frozen.ROOT):
    _,_,contract,_=frozen.verify_current_inputs(baseline_paths,root)
    s=derive(Path(baseline_paths["model"]).read_text(),contract,root);out=Path(candidate_directory)
    require(out.is_absolute()and out.resolve()==out,"owned exclusive candidate directory");out.mkdir(exist_ok=False)
    paths=dict(model=str(out/"model.spice"),composition=str(out/"composition.json"),planes=str(out/"planes.json"))
    for role,raw in (("model",s["text"].encode()),("composition",encode(s["contract"])),("planes",Path(baseline_paths["planes"]).read_bytes())):
        with Path(paths[role]).open("xb")as stream:stream.write(raw)
    frozen.write_exclusive(out/"delta.json",s["summary"])
    return paths,s["summary"]
