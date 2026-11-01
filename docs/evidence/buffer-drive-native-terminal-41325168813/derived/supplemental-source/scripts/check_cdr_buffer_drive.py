#!/usr/bin/env python3
"""Run inherited controls and exact six-device buffer drive refusal/binding checks."""
import copy,json,shutil,tempfile,types
from pathlib import Path
import cdr_buffer_drive_candidate as candidate
import cloud_cdr_buffer_drive as host
import check_cdr_divider_width as prior
import cdr_via2_m3_loaded_core as core
def main():
    ctx=host.source_gate();assert core.actual_context(ctx)==ctx
    pn=dict(prior.__dict__);pn["host"]=host
    candidate.cloned(prior.main,pn)()
    _,records=core.current_configuration()
    contract=records["readback/actual/mim/composition/composition.json"]
    planes=records["readback/actual/binding/inputs/native-planes.json"]
    ns=core.numerical_namespace()
    cards=[".subckt "+ns["MODEL"]+" "+" ".join(contract["interface"])]
    for d in contract["device_records"]:
        cards.append(" ".join([d["instance"],*[t["node"]for t in d["terminals"]],d["model"],*[k+"="+v for k,v in d["parameters"].items()]]))
    cards += [f"RTEST{i} fixture_node 0 1"for i in range(contract["counts"]["R"])]
    cards += [f"CTEST{i} fixture_node 0 1f"for i in range(contract["counts"]["C"])]
    cards += [".ends "+ns["MODEL"]];text="\n".join(cards)+"\n"
    before=(candidate.parent.derive,candidate.original.derive,candidate.original.variant,core.prepare_case.__globals__,host.original.source_gate)
    golden=candidate.parent.derive(text,contract,native=False)
    s=candidate.derive(text,contract,native=False)
    expected={126:("nx","4","8"),129:("nx","4","8"),232:("l","1.8u","0.9u"),233:("l","1.8u","0.9u"),243:("l","1.8u","0.9u"),244:("l","1.8u","0.9u")}
    assert candidate.CHANGES==expected
    oldrows={d["native_id"]:d for d in golden["contract"]["device_records"]}
    newrows={d["native_id"]:d for d in s["contract"]["device_records"]}
    assert len(newrows)==650 and s["plan"]==golden["plan"]
    assert {i for i in oldrows if oldrows[i]!=newrows[i]}==set(expected)
    for ident,(key,old,new)in expected.items():
        assert newrows[ident]["parameters"][key]==new
        restored=copy.deepcopy(newrows[ident]);restored["parameters"][key]=old
        assert restored==oldrows[ident]
    assert [l for l in golden["text"].splitlines()if l[:1]in("R","C")]==[l for l in s["text"].splitlines()if l[:1]in("R","C")]
    rejected=[]
    def reject(label,t,c,root=None):
        try:candidate.rewrite(t,c,**({}if root is None else {"root":root}))
        except ValueError:rejected.append(label)
        else:raise AssertionError("accepted "+label)
    for ident,(key,old,new)in expected.items():
        d=oldrows[ident];line=next(l for l in golden["text"].splitlines()if l.startswith(d["instance"]+" "))
        reject(str(ident)+":missing",golden["text"].replace(line+"\n","",1),golden["contract"])
        reject(str(ident)+":duplicate",golden["text"]+line+"\n",golden["contract"])
        reject(str(ident)+":terminal",golden["text"].replace(line,line.replace(d["terminals"][0]["node"],"wrong",1),1),golden["contract"])
        reject(str(ident)+":extra parameter",golden["text"].replace(line,line+" extra=1",1),golden["contract"])
        reject(str(ident)+":card parameter",golden["text"].replace(line,line.replace(key+"="+old,key+"="+new),1),golden["contract"])
        for field in ("parameter","cluster","node","model","terminal_order"):
            bad=copy.deepcopy(golden["contract"]);row=next(x for x in bad["device_records"]if x["native_id"]==ident)
            if field=="parameter":row["parameters"][key]=new
            elif field=="cluster":row["terminals"][1]["native_cluster"]=-1
            elif field=="node":row["terminals"][1]["node"]="wrong"
            elif field=="model":row["model"]="wrong"
            else:row["terminals"].reverse()
            reject(str(ident)+":"+field,golden["text"],bad)
    reject("repeat mutation",s["text"],s["contract"])
    bad=copy.deepcopy(golden["contract"]);bad["device_records"].pop();reject("missing device",golden["text"],bad)
    bad=copy.deepcopy(golden["contract"]);bad["counts"]["devices"]=500;reject("wrong census",golden["text"],bad)
    bad=copy.deepcopy(golden["contract"]);bad["device_records"][-1]=bad["device_records"][0];reject("duplicate identity",golden["text"],bad)
    spec=json.loads((host.ROOT/candidate.TARGET_FILE).read_bytes())
    with tempfile.TemporaryDirectory(prefix="buffer-target-controls-")as directory:
        p=Path(directory)/candidate.TARGET_FILE;p.parent.mkdir()
        for name in ("duplicate target","wrong parent","wrong target"):
            bad=copy.deepcopy(spec)
            if name=="duplicate target":bad["targets"][-1]=bad["targets"][0]
            elif name=="wrong parent":bad["parent_source"]="wrong"
            else:bad["targets"][0]["terminals"][0]["native_cluster"]=-1
            p.write_text(json.dumps(bad))
            reject(name,golden["text"],golden["contract"],directory)
    assert len(rejected)==67
    # Actual original compiled binding must use Nx8 in both current denominators.
    adapted=candidate.original.namespace_for_state(s)
    with tempfile.TemporaryDirectory(prefix="buffer-drive-controls-")as directory:
        model=Path(directory)/"synthetic.spice";model.write_text(s["text"])
        adapted.update(model=model,contract=s["contract"],planes=planes,r={},proof={"synthetic":True})
        core.block("binding",adapted)
    assert len(adapted["r"]["binding_controls"]["rejected"])==13
    assert adapted["r"]["binding_controls"]["candidate_expansion"]["checks"]==12
    assert len(adapted["bound"]["groups"]["npn13g2"])==124
    for ident in(126,129):assert adapted["bound"]["groups"]["npn13g2"]["xpd.xd"+format(ident,"04d")]["nx"]==8
    assert len(adapted["bound"]["groups"]["sg13_lv_nmos"])==200 and len(adapted["bound"]["mos_tail_groups"])==16
    assert all(newrows[i]["parameters"]["w"]=="2u"for i in candidate.parent.TARGETS)
    paths=lambda prefix:{k:"/"+prefix+"/"+k for k in("model","composition","planes")}
    variant=candidate.variant(paths("baseline"),paths("candidate"))
    assert all(f.__code__ is getattr(core,k).__code__ for k,f in variant.items())
    assert before==(candidate.parent.derive,candidate.original.derive,candidate.original.variant,core.prepare_case.__globals__,host.original.source_gate)
    scenario=core.numerical_namespace();scenario.update(args=types.SimpleNamespace(case="nominal_late"),out=Path("/unused-source-control"))
    variant["prepare_case"].__globals__["block"]("scenario",scenario)
    assert scenario["r"]["scope"]==candidate.SCOPE and scenario["r"]["buffer_drive_changes"]==6
    out=Path("cloud-sampler-load-controls")
    result=dict(status="PASS_BUFFER_DRIVE_SOURCE_CONTROLS_ONLY",context=ctx,buffer_corruptions_rejected=rejected,changed_physical_descriptors_verified=6,changed_emitter_bindings_verified=2,all_inherited_width2_checks_executed=True,original_compiled_binding_checked=True,all_frozen_prepare_measure_bodies_identical=True,all_original_electrical_and_current_gates_retained=True,synthetic_model_not_native=True,simulation_executed=False,physical_acceptance=False,full_phy_accepted=False,final_timing_complete=False)
    (out/"buffer-drive-controls.json").write_bytes(candidate.encode(result))
    (out/"buffer-drive-synthetic-delta.json").write_bytes(candidate.encode(s["summary"]))
    pins=json.loads((host.ROOT/host.MANIFEST).read_bytes())
    for name in [*pins["files"],host.MANIFEST]:
        target=out/"supplemental-source"/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(host.ROOT/name,target)
    host.source_gate()
    print(json.dumps(result,sort_keys=True))
if __name__=="__main__":main()
