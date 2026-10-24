#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted source/placement controls only; no PCell, CAD, simulator or physical claim."""
import ast,copy,hashlib,json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"hw/soc/flow"))
import make_pcie_tx_phase_reset244_v1 as g
OUT=ROOT/"hw/soc/out/phase-reset244-source-controls"
def digest(b):return hashlib.sha256(b).hexdigest()
def main():
    assert os.environ.get("GITHUB_ACTIONS")=="true"and os.environ.get("RUNNER_ENVIRONMENT")=="github-hosted"
    assert os.environ.get("GITHUB_REPOSITORY")=="Melihakbulut221/nssoc"
    method=json.loads((ROOT/"scripts/tx-phase-reset244-physical-source-methods.json").read_text())
    for p,h in method["protected"].items():assert digest((ROOT/p).read_bytes())==h,p
    receipt=json.loads((ROOT/"docs/evidence/tx-phase-assert-offset244-intrinsic-pass-20261024.json").read_text())
    assert receipt["run"]==dict(id=40114254950,head_sha="e2598de52f2190ee0e3eddf8095c3fffe640b62f",status="completed",conclusion="success",run_attempt=1)
    assert receipt["summary"]==dict(asset=672855429,bytes=395763,sha256="80597ce7b874d56a2e9b5d6a0daaf3863e63c94395bbba74f33772da7eb15bd9")
    report=receipt["verified_small_report"]
    assert report["flags"]["all_four_diagnostic_screens_passed"] is True and len(report["cases"])==4
    assert all(v["complete"] and v["passed"] and not v["errors"] for v in report["cases"])
    assert all(report["flags"][key] is False for key in ("layout_RC_included","reset_hardware_qualified","all31_clock_tree_accepted","PLL_connected","full_PHY_accepted"))
    exact=g.derivations();[ast.parse(s)for s in exact]
    result={"status":"RUNNING","native_execution":False,"physical_accepted":False,"real_selector_load_accepted":False,"all31_clock_tree_accepted":False,"PLL_connected":False,"full_PHY_accepted":False,"polarity":{}}
    failures=[]
    def reject(name,fn):
        try:fn()
        except (AssertionError,KeyError,ValueError):failures.append({"name":name,"rejected":True})
        else:raise AssertionError("Accepted corrupt source/placement "+name)
    for polarity in ("p","n"):
        old=g.flatten_source((ROOT/g.OLD).read_text(),polarity)
        new=g.source_rows(ROOT,polarity);proof=g.validate_delta(old,new)
        g.configure(polarity);assert g.devices(ROOT)==new
        plan,starts,nets=g.placement_plan(new)
        reference=g.m.physical_reference(ROOT)
        lines=reference.splitlines();assert lines[2]==".subckt "+g.m.TOP+" "+" ".join(g.PORTS)
        assert len([s for s in lines if s.startswith("QPHASE__")])==106
        assert len([s for s in lines if s.startswith("RPHASE__")])==130
        assert len([s for s in lines if s.startswith("CPHASE__")])==8
        assert len([s for s in lines if s.startswith("RTAP")])==90
        target=[s for s in lines if s.startswith("R"+g.TARGET+" ")];assert len(target)==1 and target[0].endswith("rppd w=1u l=20u b=0 m=1")
        assert len(plan)==244 and set(starts)==set(nets)==set(range(15))
        assert tuple(sum(p[0]==rid for p in plan.values())for rid in range(15))==g.GROUP_CENSUS
        actual=set().union(*(set(ns)for ns in nets.values()))
        crossing=sorted(n for n in actual if sum(n in ns for ns in nets.values())>1)
        taps=[g.substrate_tap_position(i,starts)for i in range(g.TAPS)];assert len(set(taps))==90
        assert all(x in (330.,450.,570.,690.,810.,930.)for x,y in taps)
        assert all(g.use_direction(n)[1]=="OUTPUT"for n in ("MP","MN","QP","QN"))
        assert all(g.use_direction(n)[1]=="INPUT"for n in ("CLKP","CLKN","ARM_P","ARM_N"))
        result["polarity"][polarity]={"proof":proof,"source_device_map":new,"row_placement":plan,"row_starts_um":starts,"row_nets":nets,
          "crossing_nets":crossing,"finite_contacts":taps,"expected_native_LVS_count":334,
          "reference_sha256":digest(reference.encode()),"source_model_sha256":g.CIRCUIT_SHA}
        for name in ("target_L","target_W","target_net","other_Nx","other_resistor","other_MIM","missing","duplicate","source_instance","source_kind"):
            bad=copy.deepcopy(new);t=next(r for r in bad if r["name"]==g.TARGET)
            if name=="target_L":t["length_um"]=32.
            elif name=="target_W":t["width_um"]=2.
            elif name=="target_net":t["nets"][0]="AVSS"
            elif name=="other_Nx":next(r for r in bad if r["kind"]=="hbt")["nx"]=8
            elif name=="other_resistor":next(r for r in bad if r["kind"]=="resistor"and r["name"]!=g.TARGET)["length_um"]+=1
            elif name=="other_MIM":next(r for r in bad if r["kind"]=="capacitor")["width_um"]+=.1
            elif name=="missing":bad.pop()
            elif name=="duplicate":bad[-1]=copy.deepcopy(bad[0])
            elif name=="source_instance":t["source_instance"]="XOTHER"
            else:t["kind"]="capacitor"
            reject(polarity+"_"+name,lambda bad=bad:g.validate_delta(old,bad))
    text=(ROOT/g.CIRCUIT).read_text()
    reject("parser_ideal_internal_source",lambda:g.flatten_source(text.replace("XBIAS avdd ref sub rppd w=1u l=11.5u b=0 sw_et=1","VBIAS ref avss 1",1),"p"))
    reject("parser_missing_port",lambda:g.flatten_source(text.replace("CLKP CLKN MP MN QP QN ARM_P ARM_N DIV_AVDD AVSS SUB","CLKP MP MN QP QN ARM_P ARM_N DIV_AVDD AVSS SUB",1),"p"))
    reject("parser_unsupported_Nx",lambda:g.flatten_source(text.replace("Nx=1","Nx=8",1),"p"))
    bad=copy.deepcopy(new);bad[0]["name"]="UNASSIGNED"
    reject("unassigned_placement",lambda:g.placement_plan(bad))
    reject("tap_out_of_range",lambda:g.substrate_tap_position(90,starts))
    reject("missing_native_tap_row",lambda:g.substrate_tap_position(0,{k:v for k,v in starts.items()if k!=14}))
    reject("ambiguous_derivation",lambda:g.exact_replace("same same",[("same","new")]))
    assert len(failures)==27,len(failures)
    for p,h in method["protected"].items():assert digest((ROOT/p).read_bytes())==h,p
    result.update(status="PASS_TWO244_SOURCE_VARIANTS_AND27_FAULTS_NO_NATIVE_PHYSICAL_PROOF",faults=failures,method=method,
      generator_derivations_sha256=[digest(s.encode())for s in exact],
      inherited_native_methods_unchanged=True,new_layout_RC_or_reset_accepted=False)
    OUT.mkdir(parents=True,exist_ok=False);raw=(json.dumps(result,indent=2)+"\n").encode();(OUT/"result.json").write_bytes(raw)
    print(json.dumps({"status":result["status"],"faults":failures,"result_sha256":digest(raw),
      "polarity":{k:{"compact_devices":len(v["source_device_map"]),"rows":len(v["row_nets"]),"crossing_nets":len(v["crossing_nets"]),"finite_contacts":len(v["finite_contacts"]),"expected_native_LVS_count":334}for k,v in result["polarity"].items()},
      "native_execution":False,"physical_accepted":False,"full_PHY_accepted":False},indent=2))
if __name__=="__main__":main()
