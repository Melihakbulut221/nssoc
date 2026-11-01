#!/usr/bin/env python3
"""Cloud-only source controls. Synthetic cards are never native simulation proof."""
import copy,hashlib,io,json,os,tarfile,tempfile
import cloud_cdr_sampler_load as host
from pathlib import Path
import cdr_sampler_load_candidate as candidate
import cdr_via2_m3_loaded_core as frozen
def main():
    assert os.environ.get("GITHUB_ACTIONS")=="true"
    host.source_gate()
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
    assert len(delta["changes"])==24
    loads={175,176,191,194,202,205,212,214};shunts={184,185,222,223};buffers={182,183,220,221}
    series={227,229,238,240};divider_shunts={228,230,239,241}
    assert {x["native_id"]for x in delta["changes"]}==loads|shunts|buffers|series|divider_shunts
    for x in delta["changes"]:
        if x["native_id"]in loads:
            assert x["old_l"]=="2.6u"and x["new_l"]=="1.5u"and x["w"]=="32u"
        elif x["native_id"]in shunts:
            assert x["old_l"]=="5u"and x["new_l"]=="3.4u"and x["w"]=="4u"
        elif x["native_id"]in buffers:
            assert x["old_l"]=="1.8u"and x["new_l"]=="1.0u"and x["w"]=="8u"
        elif x["native_id"]in series:
            assert x["old_l"]=="3.6u"and x["new_l"]=="1.8u"and x["w"]=="1u"
        else:
            assert x["native_id"]in divider_shunts and x["old_l"]=="21.6u"and x["new_l"]=="10.8u"and x["w"]=="1u"
    assert text.splitlines()[:3]==changed.splitlines()[:3]
    rejected=[]
    def reject(label,t,ct):
        try:candidate.rewrite(t,ct)
        except ValueError:rejected.append(label)
        else:raise AssertionError("accepted "+label)
    reject("missing card",text.replace(cards[0]+"\n",""),contract)
    reject("duplicate card",text+cards[0]+"\n",contract)
    reject("wrong model token",text.replace(" rppd "," npn13g2 ",1),contract)
    reject("wrong card terminal",text.replace("w_T184_rppd_1","wrong",1),contract)
    reject("already modified card",text.replace("l=5u","l=3.4u",1),contract)
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
    reject("already changed load",text.replace("l=2.6u","l=1.5u",1),contract)
    wrong=copy.deepcopy(contract)
    next(d for d in wrong["device_records"]if d["native_id"]==175)["parameters"]["w"]="16u"
    reject("wrong load width",text,wrong)
    wrong=copy.deepcopy(contract)
    next(d for d in wrong["device_records"]if d["native_id"]==175)["terminals"][1]["native_net"]="$70"
    reject("wrong load physical net",text,wrong)
    reject("wrong load card terminal",text.replace("w_T175_rppd_2","wrong",1),contract)
    wrong=copy.deepcopy(contract)
    wrong["device_records"][0]["native_id"]=wrong["device_records"][1]["native_id"]
    reject("duplicate physical identity",text,wrong)
    wrong=copy.deepcopy(contract)
    next(d for d in wrong["device_records"]if d["native_id"]==191)["parameters"]["m"]="2"
    reject("wrong selected multiplicity",text,wrong)
    wrong=copy.deepcopy(contract)
    next(d for d in wrong["device_records"]if d["native_id"]==182)["parameters"]["w"]="16u"
    reject("wrong buffer pullup width",text,wrong)
    wrong=copy.deepcopy(contract)
    next(d for d in wrong["device_records"]if d["native_id"]==182)["terminals"][1]["native_net"]="$98"
    reject("wrong buffer physical net",text,wrong)
    wrong=copy.deepcopy(contract)
    next(d for d in wrong["device_records"]if d["native_id"]==227)["parameters"]["w"]="2u"
    reject("wrong A divider width",text,wrong)
    wrong=copy.deepcopy(contract)
    next(d for d in wrong["device_records"]if d["native_id"]==241)["terminals"][1]["native_cluster"]=16
    reject("wrong C divider ground",text,wrong)
    reject("wrong divider native terminal",text.replace("w_T238_rppd_1","wrong",1),contract)
    reject("already modified divider",text.replace("l=21.6u","l=10.8u",1),contract)
    assert len(rejected)==21
    archive_controls=[]
    with tempfile.TemporaryDirectory(prefix="sampler-load-controls-") as directory:
        base=Path(directory);payload=b"source-control-only"
        expected={"record.txt":dict(bytes=len(payload),sha256=hashlib.sha256(payload).hexdigest())}
        def make(name,mode):
            p=base/(name+".tar.gz")
            with tarfile.open(p,"w:gz") as tar:
                info=tarfile.TarInfo("fixture/record.txt");info.size=len(payload)
                tar.addfile(info,io.BytesIO(payload))
                if mode=="duplicate":tar.addfile(info,io.BytesIO(payload))
                if mode=="link":
                    link=tarfile.TarInfo("fixture/link");link.type=tarfile.SYMTYPE;link.linkname="/tmp/escape";tar.addfile(link)
                if mode=="traversal":
                    bad=tarfile.TarInfo("fixture/../escape");bad.size=1;tar.addfile(bad,io.BytesIO(b"x"))
            return p
        good=make("good","good")
        proof=host.restore(good,"fixture",expected,set(expected),base/"positive")
        assert proof["full_member_count"]==1 and (base/"positive/record.txt").read_bytes()==payload
        cases=[("duplicate",make("duplicate","duplicate"),expected),
               ("link",make("link","link"),expected),
               ("traversal",make("traversal","traversal"),expected),
               ("wrong hash",good,{"record.txt":dict(bytes=len(payload),sha256="0"*64)}),
               ("missing member",good,dict(expected,missing=expected["record.txt"]))]
        for i,(label,archive,pins) in enumerate(cases):
            try:host.restore(archive,"fixture",pins,set(pins),base/("bad"+str(i)))
            except ValueError:archive_controls.append(label)
            else:raise AssertionError("accepted archive "+label)
    assert len(archive_controls)==5
    out=Path("cloud-sampler-load-controls");out.mkdir(exist_ok=False)
    result=dict(status="PASS_SOURCE_ONLY_SAMPLER_LOAD_CANDIDATE",source=os.environ["GITHUB_SHA"],run=os.environ["GITHUB_RUN_ID"],rejected=rejected,archive_rejected=archive_controls,
        original_prepare_measure_function_bodies_identical=True,original_module_not_mutated=True,frozen_catalog_checked=True,
        native_model_acquired=False,simulation_executed=False,physical_acceptance=False,full_phy_accepted=False)
    (out/"result.json").write_bytes(candidate.encode(result));(out/"synthetic-delta.json").write_bytes(candidate.encode(delta))
    print(json.dumps(result,sort_keys=True))
if __name__=="__main__":main()
