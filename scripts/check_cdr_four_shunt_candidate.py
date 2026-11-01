#!/usr/bin/env python3
"""Cloud-only source controls. Synthetic cards are never native simulation proof."""
import copy,json,os
from pathlib import Path
import cdr_four_shunt_candidate as candidate
import cdr_via2_m3_loaded_core as frozen
def main():
    assert os.environ.get("GITHUB_ACTIONS")=="true"
    c,records=frozen.current_configuration()
    frozen.catalog()
    ns=frozen.numerical_namespace()
    assert ns["UI"]==125e-12 and ns["STEP"]==.3125e-12
    contract=records["readback/actual/mim/composition/composition.json"]
    # Original physical JSON is authenticated above. Synthetic card formatting
    # isolates mutation logic without acquiring a model or running a simulator.
    cards=[]
    for d in contract["device_records"]:
        if d["native_id"] in candidate.TARGETS:
            cards.append(" ".join([d["instance"],*[t["node"] for t in d["terminals"]],d["model"],*[k+"="+v for k,v in d["parameters"].items()]]))
    text="* exact unrelated bytes\nR_keep a b 42\nC_keep a 0 1f\n"+"\n".join(cards)+"\n.end\n"
    changed,updated,delta=candidate.rewrite(text,contract)
    assert len(delta["changes"])==4 and all("l=7.4u" in x["after"] for x in delta["changes"])
    assert text.splitlines()[:3]==changed.splitlines()[:3]
    rejected=[]
    def reject(label,t,ct):
        try:candidate.rewrite(t,ct)
        except ValueError:rejected.append(label)
        else:raise AssertionError("accepted "+label)
    reject("missing card",text.replace(cards[0]+"\n",""),contract)
    reject("duplicate card",text+cards[0]+"\n",contract)
    reject("wrong model token",text.replace("rppd","npn13g2",1),contract)
    reject("wrong card terminal",text.replace("w_T184_rppd_1","wrong",1),contract)
    reject("already modified card",text.replace("l=5u","l=7.4u",1),contract)
    reject("extra parameter",text.replace(cards[0],cards[0]+" extra=1"),contract)
    wrong=copy.deepcopy(contract)
    next(d for d in wrong["device_records"] if d["native_id"]==184)["parameters"]["w"]="8u"
    reject("wrong physical width",text,wrong)
    wrong=copy.deepcopy(contract)
    next(d for d in wrong["device_records"] if d["native_id"]==184)["terminals"][0]["native_cluster"]=999
    reject("wrong physical cluster",text,wrong)
    wrong=copy.deepcopy(contract);wrong["device_records"].pop()
    reject("incomplete physical census",text,wrong)
    wrapped=text.replace(cards[0],cards[0].replace(" rppd ","\n+ rppd "))
    candidate.rewrite(wrapped,contract)
    before=(frozen.verify_current_inputs,frozen.block,frozen.prepare_case.__globals__)
    v=candidate.variant({k:"/baseline/"+k for k in ("model","composition","planes")},{k:"/candidate/"+k for k in ("model","composition","planes")})
    assert all(v[k].__code__ is getattr(frozen,k).__code__ for k in v)
    assert before==(frozen.verify_current_inputs,frozen.block,frozen.prepare_case.__globals__)
    assert v["prepare_case"].__globals__ is not frozen.prepare_case.__globals__
    assert v["prepare_case"].__globals__["verify_runtime"] is frozen.verify_runtime
    assert len(rejected)==9
    out=Path("cloud-four-shunt-controls");out.mkdir(exist_ok=False)
    result=dict(status="PASS_SOURCE_ONLY_FOUR_SHUNT_CANDIDATE",source=os.environ["GITHUB_SHA"],run=os.environ["GITHUB_RUN_ID"],rejected=rejected,
        original_prepare_measure_function_bodies_identical=True,original_module_not_mutated=True,frozen_catalog_checked=True,
        native_model_acquired=False,simulation_executed=False,physical_acceptance=False,full_phy_accepted=False)
    (out/"result.json").write_bytes(candidate.encode(result));(out/"synthetic-delta.json").write_bytes(candidate.encode(delta))
    print(json.dumps(result,sort_keys=True))
if __name__=="__main__":main()
