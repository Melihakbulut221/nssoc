#!/usr/bin/env python3
"""Cloud source qualification, synthetic full500 fixture is never native evidence."""
import copy,json,os
from pathlib import Path
import check_cdr_sampler_resistor_base as legacy
import cloud_cdr_sampler_load as host
import cdr_sampler_load_candidate as candidate
import cdr_via2_m3_loaded_core as frozen
def main():
    assert os.environ.get("GITHUB_ACTIONS")=="true"
    legacy.main()
    ctx=host.source_gate();c,records=frozen.current_configuration();ns=frozen.numerical_namespace()
    contract=records["readback/actual/mim/composition/composition.json"]
    planes=records["readback/actual/binding/inputs/native-planes.json"]
    projection=records["derived-loaded-vector-projection.json"]
    cards=[".subckt "+ns["MODEL"]+" "+" ".join(contract["interface"])]
    for d in contract["device_records"]:
        cards.append(" ".join([d["instance"],*[t["node"]for t in d["terminals"]],d["model"],*[k+"="+v for k,v in d["parameters"].items()]]))
    cards += [f"RTEST{i} fixture_node 0 1"for i in range(contract["counts"]["R"])]
    cards += [f"CTEST{i} fixture_node 0 1f"for i in range(contract["counts"]["C"])]
    cards += [".ends "+ns["MODEL"]]
    text="\n".join(cards)+"\n"
    s=candidate.derive(text,contract,native=False)
    base=ns["bind_native"](s["baseline_text"],s["baseline_contract"],planes)
    base_controls=ns["binding_controls"](s["baseline_text"],s["baseline_contract"],planes)
    assert len(base_controls["rejected"])==13 and base_controls["equivalent_unit_spellings"]==2
    bound=candidate.expanded_bind(s["text"],s["contract"],planes,s,ns)
    controls=candidate.expansion_controls(s["text"],s["contract"],planes,s,ns)
    assert len(bound["groups"]["sg13_lv_nmos"])==200 and len(bound["mos_tail_names"])==192
    assert len(bound["original_mos_tail_names"])==42 and len(bound["mos_tail_groups"])==16
    expected=candidate.expected_projection(bound,projection)
    nodes={n for group in bound["groups"].values()for d in group.values()for n in d["nodes"]}|set(bound["ports"])|set(bound["aliases"].values());nodes.discard("0")
    actual=["v("+n+")"for n in sorted(nodes)]+["@q."+n+".qnpn13g2[ic]"for n in bound["groups"]["npn13g2"]]+["@n."+n+".nsg13_lv_nmos[ids]"for n in bound["groups"]["sg13_lv_nmos"]]
    assert actual==expected and len(nodes)==977 and len(actual)==1301
    report=dict(vector_census=dict(total=1301,voltage_nodes=977,hbt_collector_currents=124,mos_drain_currents=200,save_commands=len(ns["native_save_commands"](actual))))
    check=dict(bound=bound,vectors=actual,r=report,native_save_commands=ns["native_save_commands"])
    candidate.verify_projection(check,projection)
    refused=[]
    for label,kind in [("missing unit current","missing"),("duplicated unit current","duplicate"),("wrong original alias","alias"),("stale50 current count","count")]:
        bad=copy.deepcopy(check)
        if kind=="missing":bad["vectors"].pop()
        if kind=="duplicate":bad["vectors"][-1]=bad["vectors"][-2]
        if kind=="alias":bad["bound"]["aliases"][next(iter(bad["bound"]["aliases"]))]="wrong"
        if kind=="count":bad["r"]["vector_census"]["mos_drain_currents"]=50
        try:candidate.verify_projection(bad,projection)
        except ValueError:refused.append(label)
        else:raise AssertionError("accepted projection corruption "+label)
    changes={}
    for name in candidate.BLOCK_CHANGES:
        updated=candidate.adapted_text(name);compile(updated,"<qualified-block>","exec")
        changes[name]=dict(substitutions=candidate.BLOCK_CHANGES[name],sha256=candidate.digest(updated.encode()),all_other_executable_bytes_preserved=True)
    before=(frozen.verify_current_inputs,frozen.block,frozen.prepare_case.__globals__)
    v=candidate.variant({k:"/baseline/"+k for k in ("model","composition","planes")},{k:"/candidate/"+k for k in ("model","composition","planes")})
    assert all(v[k].__code__ is getattr(frozen,k).__code__ for k in v)
    assert before==(frozen.verify_current_inputs,frozen.block,frozen.prepare_case.__globals__)and v["prepare_case"].__globals__["verify_runtime"]is frozen.verify_runtime
    out=Path("cloud-sampler-load-controls")
    result=dict(status="PASS_PARALLEL_MOS_BINDING_SOURCE_CONTROLS_NOT_NATIVE_SIMULATION",context=ctx,original_baseline_binding_controls=base_controls,candidate_expansion_controls=controls,projection_corruptions_refused=refused,baseline_groups={k:len(v)for k,v in base["groups"].items()},candidate_groups={k:len(v)for k,v in bound["groups"].items()},candidate_vectors=report["vector_census"],original_tail_origins=42,expanded_tail_units=192,unchanged_stage_tail_groups=16,executable_changes=changes,original_prepare_measure_function_bodies_identical=True,native_model_acquired=False,simulation_executed=False,physical_acceptance=False,full_phy_accepted=False,final_timing_complete=False)
    (out/"parallel-controls.json").write_bytes(candidate.encode(result))
    (out/"parallel-binding.json").write_bytes(candidate.encode(bound))
    (out/"parallel-projection.json").write_bytes(candidate.encode(dict(vectors=actual,source_projection_sha256=c["records"]["derived-loaded-vector-projection.json"]["sha256"],native_capture=False)))
    for p in ("scripts/cdr_sampler_load_candidate.py","scripts/cdr_sampler_load_resistor_base.py","scripts/check_cdr_sampler_load_candidate.py","scripts/check_cdr_sampler_resistor_base.py","scripts/mos_model_domain_audit.py",candidate.PHYSICAL):
        dest=out/"parallel-source"/p;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(Path(p).read_bytes())
    print(json.dumps(result,sort_keys=True))
if __name__=="__main__":main()
