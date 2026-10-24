#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Correct frozen role-size assumption from independent source and native topology."""
import ast,copy,hashlib,inspect,json,math,os,runpy,sys,traceback
from pathlib import Path
import bind_tx_output8088_native_clock_roles as frozen
import observe_tx_native_clock_role_p4_parameters as observer
import tx_native_clock_role_p4_history as history
ROOT=Path(__file__).resolve().parents[1]
FROZEN_SHA="9934a858863296be0d74369f84e22c87483b05e25c83520a9abb56053f2e4be0"
STATUS="PASS_NATIVE31_CLOCK_ROLE_BINDING_CANONICAL_SIZING_REQUIRES_REAL_DRIVER_LOADED_WAVES"
EDITS=[
 ("def bind(g):","def bind(g,canonical):"),
 ("    def nx(did):","    def nx(did,role):"),
 ("        assert p['nx']==8.0,'Actual selector/tail emitter multiplier changed'",
  "        stage_parameters(label,did,p,role,canonical)"),
 ("selector_emitters.add(cluster(did,'E'));parameters=nx(did)",
  "selector_emitters.add(cluster(did,'E'));parameters=nx(did,'selector')"),
 ("        for did in tails:nx(did)","        for did in tails:nx(did,'tail')"),
 ("tail_devices=[dict(native_id=d,parameters=nx(d),",
  "tail_devices=[dict(native_id=d,parameters=nx(d,'tail'),")]
def derive():
    assert frozen.sha(Path(frozen.__file__))==FROZEN_SHA
    before=inspect.getsource(frozen.bind);after=before
    for a,b in EDITS:
        assert after.count(a)==1,a
        after=after.replace(a,b,1)
    recovered=after
    for a,b in reversed(EDITS):
        assert recovered.count(b)==1,b
        recovered=recovered.replace(b,a,1)
    assert recovered==before
    ast.parse(after)
    ns=dict(vars(frozen),stage_parameters=stage_parameters)
    exec(compile(after,"<canonical-stage-sized-original-clock-binder>","exec"),ns)
    return ns["bind"],dict(frozen_sha256=FROZEN_SHA,
      original_bind_sha256=hashlib.sha256(before.encode()).hexdigest(),
      corrected_bind_sha256=hashlib.sha256(after.encode()).hexdigest(),
      exact_reversible_edits=EDITS,all_original_physical_and_role_checks_retained=True)
def stage_parameters(label,did,p,role,canonical):
    assert role in ("selector","tail")
    row=canonical[did]
    assert row["label"]==label and row["role"]==role and row["model"]=="npn13G2"
    kind=history.KINDS[label]
    assert row["kind"]==kind and row["parameters"]==p
    nx=p.get("nx")
    assert isinstance(nx,(int,float))and not isinstance(nx,bool)and math.isfinite(nx)
    assert nx==observer.ns["SPECS"][kind][role],"Native parameter disagrees with independent canonical stage"
def prove_old_failure(g,blocks):
    first=next({"macro":b["label"],**d}for b in blocks for d in b["devices"]
               if d["role"]=="selector"and d["parameters"]["nx"]!=8.0)
    try:frozen.bind(g)
    except AssertionError as e:
        original={"type":type(e).__name__,"message":str(e),"traceback":traceback.format_exc(),
          "frames":[{"function":x.name,"line":x.lineno,"file":Path(x.filename).name}
                    for x in traceback.extract_tb(e.__traceback__)]}
        frames=[];tb=e.__traceback__
        while tb is not None:frames.append(tb.tb_frame);tb=tb.tb_next
        assert frames[-1].f_code.co_name=="nx"and frames[-2].f_code.co_name=="bind"
        original["failing_device"]={"native_id":frames[-1].f_locals["did"],
          "parameters":copy.deepcopy(frames[-1].f_locals["p"])}
        original["bind_context"]={"macro":frames[-2].f_locals["label"],
                                 "clock_leg":frames[-2].f_locals["key"]}
        observer.verify_original_failure(original,first)
    else:raise AssertionError("Original blanket-size rejection did not reproduce")
    return original,first
def compare_projection(result,blocks):
    expected={}
    for b in blocks:
        for d in b["devices"]:
            if d["role"] in ("selector","tail"):expected[d["native_id"]]={"label":b["label"],"kind":b["kind"],**d}
    assert len(expected)==186
    seen=set()
    for key,c in result["clocks"].items():
        assert key==c["clock"]+c["leg"]
        for role,field in (("selector","selector_devices"),("tail","tail_devices")):
            for d in c[field]:
                did=d["native_id"];stage_parameters(c["macro"],did,d["parameters"],role,expected)
                original=expected[did]
                if role=="selector":assert original["clock_leg"]==key and original["bank"]==c["selected_bank"]
                for terminal,record in d["terminals"].items():
                    assert record["native_id"]==did and record["terminal"]==terminal
                    assert record["anchor"]["native_cluster"]==original["native_clusters"][terminal]
                    want=next(t for t in original["composed_terminals"]if t["terminal"]==terminal)
                    assert record["composed"]==want
                seen.add(did)
    assert seen==set(expected)
    return {"compared_distinct_selector_and_tail_devices":len(seen),"all_actual_C_B_E_S_and_composed_records_equal":True}
def controls():
    old=observer.controls();fn,derivation=derive();faults=[]
    def reject(name,call):
        try:call()
        except (AssertionError,KeyError,TypeError):faults.append(name)
        else:raise AssertionError("Accepted stage-size corruption "+name)
    for label in ("a","p8_0","f"):
        kind=history.KINDS[label]
        for role in ("selector","tail"):
            p={"nx":observer.ns["SPECS"][kind][role],"we":.07,"le":.9,"m":1.}
            rec={"label":label,"kind":kind,"role":role,"model":"npn13G2","parameters":copy.deepcopy(p)}
            stage_parameters(label,7,p,role,{7:rec})
            for field in ("nx","we","role","kind","label","model"):
                wrong=copy.deepcopy(rec);values=copy.deepcopy(p)
                if field=="nx":
                    wrong["parameters"]["nx"]=values["nx"]=8. if p["nx"]!=8. else 6.
                elif field=="we":values["we"]=.08
                elif field=="role":wrong["role"]="data"
                elif field=="kind":wrong["kind"]="final"if kind!="final"else"pre"
                elif field=="label":wrong["label"]="foreign"
                else:wrong["model"]="npn13G2L"
                reject(label+"."+role+"."+field,lambda w=wrong,v=values:stage_parameters(label,7,v,role,{7:w}))
            for value,name in ((True,"boolean"),(float("nan"),"nan")):
                wrong=copy.deepcopy(rec);values=copy.deepcopy(p);wrong["parameters"]["nx"]=values["nx"]=value
                reject(label+"."+role+"."+name,lambda w=wrong,v=values:stage_parameters(label,7,v,role,{7:w}))
    assert len(faults)==48
    return {"status":"PASS_CANONICAL_CORRECTED_BINDER_SOURCE_AND48_FAULTS_NOT_NATIVE",
      "original_catalog_and_failure_controls":old,"derivation":derivation,"stage_parameter_faults":faults,
      "native_role_accepted":False,"electrical_accepted":False,"full_phy_accepted":False}
def bind(g):
    catalog=observer.source_catalog()
    original_plan=copy.deepcopy(g["plan"]);normalized,transition=history.bind(g)
    blocks=observer.ns["inspect_native"](normalized)
    bad=observer.mismatches(blocks);assert not bad,bad
    assert sum(len(b["devices"])for b in blocks)==589
    assert sum(d["parameters"]["nx"]for b in blocks for d in b["devices"])==863
    old_failure,witness=prove_old_failure(g,blocks)
    canonical={d["native_id"]:{"label":b["label"],"kind":b["kind"],**d}for b in blocks for d in b["devices"]}
    assert len(canonical)==589
    fn,derivation=derive();result=fn(normalized,canonical)
    proof=compare_projection(result,blocks)
    assert g["plan"]==original_plan and frozen.sha(Path(frozen.__file__))==FROZEN_SHA
    assert len(result["role_controls"])==14 and len(result["actual_polarity_faults"])==31
    assert all(x["rejected"]for x in result["role_controls"])
    assert result["counts"]==dict(pairs=31,public_clock_legs=62,selector_HBT_bases=124,
                                tail_HBTs=62,original_native_terminals_rechecked=28620)
    result.update(status=STATUS,native_role_accepted=True,kind_transition=transition,
      catalog=catalog,all589_actual_devices=blocks,canonical_mismatches=bad,
      canonical_counts={"muxes":31,"HBTs":589,"emitters":863},
      original_failure=old_failure,first_legacy_selector_rejection=witness,
      original_binder_unchanged=True,derivation=derivation,canonical_projection=proof)
    return result
def main():
    assert os.environ.get("GITHUB_ACTIONS")=="true"and os.environ.get("RUNNER_ENVIRONMENT")=="github-hosted"
    assert os.environ["GITHUB_REPOSITORY"]=="Melihakbulut221/nssoc"and len(sys.argv)==4
    workspace,summary,out=map(Path,sys.argv[1:]);assert frozen.sha(summary)==frozen.SUMMARY
    s=json.loads(summary.read_text());assert s["source_head"]==frozen.SOURCE_HEAD
    assert s["status"]=="PASS_ACTUAL8088_NATIVE124_INPUTS372_BASES64_DRIVER_HANDOFFS_FOUR_OUTPUT_PORTS_REQUIRES_LOADED_WAVES"
    assert s["sources_unchanged"]and s["interfaces_sha256"]==frozen.PIN["interfaces.json"]
    for p,h in frozen.PIN.items():assert s["outputs"][p]==h and frozen.sha(workspace/p)==h
    top=json.loads((workspace/"topology.json").read_text())
    for kind,spec in observer.ns["SPECS"].items():
        assert top["outputs"]["inputs/"+kind+"/layout/schematic.cir"]==spec["schematic_sha256"]
    out.mkdir(parents=True,exist_ok=False);previous=sys.argv
    try:
        sys.argv=[str(workspace/"bind-native-interfaces.py"),str(workspace),str(out/"original-interfaces.json")]
        g=runpy.run_path(sys.argv[0],run_name="__main__")
    finally:sys.argv=previous
    assert frozen.sha(out/"original-interfaces.json")==frozen.PIN["interfaces.json"]
    result=bind(g)
    assert all(frozen.sha(workspace/p)==h for p,h in frozen.PIN.items())
    observer.source_catalog()
    result.update(qualified_inputs_unchanged=True,qualified_input_hashes=frozen.PIN,
                  original_interfaces_sha256=frozen.PIN["interfaces.json"])
    (out/"clock-roles.json").write_text(json.dumps(result,indent=2)+"\n")
    print(result["status"])
if __name__=="__main__":main()
