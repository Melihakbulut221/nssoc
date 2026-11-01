#!/usr/bin/env python3
"""Original checks plus12-divider width and original compiled binding controls."""
import copy,json,shutil,tempfile,types
from pathlib import Path
import cdr_divider_width_candidate as candidate
import cloud_cdr_divider_width as host
import check_cdr_divider_drive as prior
import cdr_via2_m3_loaded_core as core
def main():
    ctx=host.source_gate();assert core.actual_context(ctx)==ctx
    # Run unchanged divider/original suites with the explicit current-source gate.
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
    cards += [".ends "+ns["MODEL"]]
    text="\n".join(cards)+"\n"
    before=(candidate.parent.derive,candidate.original.derive,candidate.original.variant,core.prepare_case.__globals__,host.original.source_gate)
    golden=candidate.parent.derive(text,contract,native=False)
    s=candidate.derive(text,contract,native=False)
    expected={i:"8u"for i in candidate.TARGETS}
    assert len(expected)==12
    oldrows={d["native_id"]:d for d in golden["contract"]["device_records"]}
    newrows={d["native_id"]:d for d in s["contract"]["device_records"]}
    assert len(newrows)==650 and s["plan"]==golden["plan"]
    assert {i for i in oldrows if oldrows[i]!=newrows[i]}==set(expected)
    for ident,value in expected.items():
        assert newrows[ident]["parameters"]["w"]==value
        restored=copy.deepcopy(newrows[ident]);restored["parameters"]["w"]=oldrows[ident]["parameters"]["w"]
        assert restored==oldrows[ident]
    assert [l for l in golden["text"].splitlines()if l[:1]in("R","C")]==[l for l in s["text"].splitlines()if l[:1]in("R","C")]
    rejected=[]
    def reject(label,t,c):
        try:candidate.rewrite(t,c)
        except ValueError:rejected.append(label)
        else:raise AssertionError("accepted "+label)
    for ident in expected:
        d=oldrows[ident];line=next(l for l in golden["text"].splitlines()if l.startswith(d["instance"]+" "))
        reject(str(ident)+":missing",golden["text"].replace(line+"\n","",1),golden["contract"])
        reject(str(ident)+":duplicate",golden["text"]+line+"\n",golden["contract"])
        reject(str(ident)+":terminal",golden["text"].replace(line,line.replace(d["terminals"][0]["node"],"wrong",1),1),golden["contract"])
        reject(str(ident)+":extra parameter",golden["text"].replace(line,line+" extra=1",1),golden["contract"])
        bad=copy.deepcopy(golden["contract"]);next(x for x in bad["device_records"]if x["native_id"]==ident)["parameters"]["w"]="8"
        reject(str(ident)+":width",golden["text"],bad)
        bad=copy.deepcopy(golden["contract"]);next(x for x in bad["device_records"]if x["native_id"]==ident)["terminals"][1]["native_cluster"]=-1
        reject(str(ident)+":cluster",golden["text"],bad)
    reject("repeat mutation",s["text"],s["contract"])
    bad=copy.deepcopy(golden["contract"]);bad["device_records"].pop();reject("missing device",golden["text"],bad)
    bad=copy.deepcopy(golden["contract"]);bad["counts"]["devices"]=500;reject("wrong census",golden["text"],bad)
    assert len(rejected)==75
    adapted=candidate.original.namespace_for_state(s)
    with tempfile.TemporaryDirectory(prefix="divider-width-controls-")as directory:
        model=Path(directory)/"synthetic.spice";model.write_text(s["text"])
        adapted.update(model=model,contract=s["contract"],planes=planes,r={},proof={"synthetic":True})
        core.block("binding",adapted)
    assert len(adapted["r"]["binding_controls"]["rejected"])==13
    assert adapted["r"]["binding_controls"]["candidate_expansion"]["checks"]==12
    assert len(adapted["bound"]["groups"]["npn13g2"])==124
    assert all(d["parameters"]["w"]=="8u"for d in s["contract"]["device_records"]if d["native_id"]in expected)
    assert len(adapted["bound"]["groups"]["sg13_lv_nmos"])==200 and len(adapted["bound"]["mos_tail_groups"])==16
    paths=lambda prefix:{k:"/"+prefix+"/"+k for k in("model","composition","planes")}
    variant=candidate.variant(paths("baseline"),paths("candidate"))
    assert all(f.__code__ is getattr(core,k).__code__ for k,f in variant.items())
    assert before==(candidate.parent.derive,candidate.original.derive,candidate.original.variant,core.prepare_case.__globals__,host.original.source_gate)
    scenario=core.numerical_namespace();scenario.update(args=types.SimpleNamespace(case="nominal_late"),out=Path("/unused-source-control"))
    variant["prepare_case"].__globals__["block"]("scenario",scenario)
    assert scenario["r"]["scope"]==candidate.SCOPE and scenario["r"]["divider_width_changes"]==12
    out=Path("cloud-sampler-load-controls")
    result=dict(status="PASS_DIVIDER_WIDTH_SOURCE_CONTROLS_ONLY",context=ctx,divider_corruptions_rejected=rejected,changed_width_descriptors_verified=12,all_original_and_divider_checks_executed=True,original_compiled_binding_checked=True,all_frozen_prepare_measure_bodies_identical=True,all_original_electrical_and_current_gates_retained=True,synthetic_model_not_native=True,simulation_executed=False,physical_acceptance=False,full_phy_accepted=False,final_timing_complete=False)
    (out/"divider-width-controls.json").write_bytes(candidate.encode(result))
    (out/"divider-width-synthetic-delta.json").write_bytes(candidate.encode(s["summary"]))
    pins=json.loads((host.ROOT/host.MANIFEST).read_bytes())
    for name in [*pins["files"],host.MANIFEST]:
        target=out/"supplemental-source"/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(host.ROOT/name,target)
    host.source_gate()
    print(json.dumps(result,sort_keys=True))
if __name__=="__main__":main()
