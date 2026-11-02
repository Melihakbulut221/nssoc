#!/usr/bin/env python3
"""Current-parent explicit MOS adapter; no historical resistor derivation."""
import copy,json,types
from collections import Counter
from pathlib import Path
import cdr_via2_m3_loaded_core as frozen
import cdr_current_domain_partition as domain
require=frozen.require

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
    require(projection["vectors"][-50:]==old and projection["counts"]==dict(voltage_nodes=977,hbt_currents=124,mos_currents=50,total=1151),"original measured1151 vector identity")
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

SCOPE="Current-parent PD650 with explicit 200 model-range MOS units; original 98 resistors and distributed RC retained. Provisional electrical screen, not matching layout, fresh PEX, closed-loop CDR or serial PHY acceptance."
def verify_model_domain(runtime,state,root):
    proof=json.loads((Path(root)/"docs/evidence/cdr-current-domain-model-proof.json").read_bytes())
    checked=[]
    for row in proof["all_current_model_pins_equal_historical_audit"]:
        relative=Path(row["path"]).relative_to("source/model-sources")
        path=Path(runtime["lib"])/relative
        require(frozen.file_pin(path)==row["actual_current_pin"]==row["audited_pin"],"actual native audited MOS model "+str(relative))
        checked.append(dict(path=str(relative),**frozen.file_pin(path)))
    require(len(checked)==3,"all three audited native MOS files")
    domain.prior.validate_plan(state["plan"],state["joined"])
    units=[u for p in state["plan"]for u in p["units"]]
    require(len(units)==200 and all(domain.prior.scalar(u["parameters"]["w"])>=domain.prior.Decimal("0.15e-6")and domain.prior.scalar(u["parameters"]["w"])<=domain.prior.Decimal("10e-6")for u in units),"all actual200 unit widths in declared domain")
    return dict(status="PASS_ACTUAL_RUNTIME_WIDTH_MEMBERSHIP_NOT_MODEL_OR_PHYSICAL_QUALIFICATION",
                files=checked,units=200,matching_layout_verified=False,qualified_pex=False,full_phy_accepted=False)
def materialize(base,paths,runtime,out,root=frozen.ROOT):
    require(set(paths)=={"model","composition","planes"},"complete original path set")
    _,_,contract,_=base.verify_current_inputs(paths,root)
    mapping=json.loads((Path(root)/domain.MAP).read_bytes())
    state=domain.derive(Path(paths["model"]).read_text(),contract,mapping)
    domain_proof=verify_model_domain(runtime,state,root)
    out=Path(out);require(out.is_absolute()and out.resolve()==out,"owned unaliased candidate directory")
    out.mkdir(exist_ok=False)
    target={k:str(out/v)for k,v in dict(model="model.spice",composition="composition.json",planes="planes.json").items()}
    require(set(target.values()).isdisjoint(map(str,paths.values())),"do not overwrite current parent")
    for k,b in dict(model=state["text"].encode(),composition=domain.enc(state["contract"]),planes=Path(paths["planes"]).read_bytes()).items():
        with Path(target[k]).open("xb")as stream:stream.write(b)
    frozen.write_exclusive(out/"derivation.json",dict(summary=state["summary"],plan=state["plan"],deltas=state["deltas"],model_domain=domain_proof))
    return target,state
def variant(base,baseline_paths,candidate_paths,state,root=frozen.ROOT):
    def verify(paths,root=root):
        require({k:str(v)for k,v in paths.items()}==candidate_paths,"exact current candidate paths")
        c,records,contract,planes=base.verify_current_inputs(baseline_paths,root)
        fresh=domain.derive(Path(baseline_paths["model"]).read_text(),contract,json.loads((Path(root)/domain.MAP).read_bytes()))
        require(fresh==state,"derive entire unchanged current-parent candidate again")
        require(Path(paths["model"]).read_bytes()==state["text"].encode()and Path(paths["composition"]).read_bytes()==domain.enc(state["contract"]),"complete actual650 model and descriptor")
        require(Path(paths["planes"]).read_bytes()==Path(baseline_paths["planes"]).read_bytes(),"unchanged160 native planes")
        return c,records,state["contract"],planes
    def numerical(root=root,numpy=None):return namespace_for_state(state,root,numpy)
    def block(name,namespace,root=root):
        if name in BLOCK_CHANGES:exec(compile(adapted_text(name,root),"<current-domain-"+name+">","exec"),namespace)
        else:base.block(name,namespace,root)
        if name=="scenario":namespace["r"].update(scope=SCOPE,candidate_device_count=650,mos_units=200,mos_origins=50,baseline_wire_rc_retained=True,wire_rc_recomputed=False,layout_regenerated=False,**domain.FLAGS)
        return namespace
    ns=dict(base.__dict__);ns.update(verify_current_inputs=verify,numerical_namespace=numerical,block=block,verify_projection=verify_projection)
    for name in ("prepare_case","measure_case"):
        old=getattr(base,name);new=types.FunctionType(old.__code__,ns,old.__name__,old.__defaults__,old.__closure__);new.__kwdefaults__=old.__kwdefaults__
        require(new.__code__ is old.__code__,"original complete orchestration code")
        ns[name]=new
    return types.SimpleNamespace(**ns)
def source_controls(root=frozen.ROOT):
    import ast
    changes={}
    for name in ("deck","measurement"):
        text=adapted_text(name,root);ast.parse(text)
        changes[name]=dict(sha256=domain.digest(text.encode()),changes=BLOCK_CHANGES[name],exact_reversal_verified=True)
    bound=dict(mos_origin_to_units={f"xpd.origin{i}":[f"xpd.unit{4*i+j}"for j in range(4)]for i in range(50)},
               groups={"sg13_lv_nmos":{f"xpd.unit{i}":{}for i in range(200)}})
    projection=dict(vectors=[f"v(n{i})"for i in range(977)]+[f"i(hbt{i})"for i in range(124)]+[f"@n.xpd.origin{i}.nsg13_lv_nmos[ids]"for i in range(50)],
                    counts=dict(voltage_nodes=977,hbt_currents=124,mos_currents=50,total=1151))
    expected=expected_projection(bound,projection)
    require(len(expected)==1301 and expected[:1101]==projection["vectors"][:1101],"all current voltage/HBT prefix retained")
    refused=[]
    for label in ("stale-historical-count-schema","missing-original-current","reordered-original-current","missing-origin"):
        bad=copy.deepcopy(projection);b=copy.deepcopy(bound)
        if label=="stale-historical-count-schema":bad["counts"]["composition_wire_map_entries"]=15489
        elif label=="missing-original-current":bad["vectors"].pop()
        elif label=="reordered-original-current":bad["vectors"][-2:]=reversed(bad["vectors"][-2:])
        else:b["mos_origin_to_units"].pop("xpd.origin0")
        try:expected_projection(b,bad)
        except ValueError:refused.append(label)
        else:raise ValueError("accepted "+label)
    require(len(refused)==4,"all projection faults refused")
    return dict(status="PASS_CURRENT_DOMAIN_ADAPTER_SOURCE_CONTROLS",block_changes=changes,projection_faults=refused,
                native_binding_executed=False,transient_executed=False,**domain.FLAGS)
