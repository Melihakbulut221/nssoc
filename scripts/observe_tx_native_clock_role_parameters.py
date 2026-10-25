#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Read actual role parameters and reproduce the frozen rejection; no acceptance."""
import copy,hashlib,json,math,os,runpy,sys,traceback
from pathlib import Path
import bind_tx_output8088_native_clock_roles as frozen
ROOT=Path(__file__).resolve().parents[1]
SOURCE_PINS={
 "scripts/bind_tx_output8088_native_clock_roles.py":"9934a858863296be0d74369f84e22c87483b05e25c83520a9abb56053f2e4be0",
 "scripts/cloud_tx_v5_timing_priority_assembly.py":"44f0528266658d26b86d9cdeccedb49acd19330675b5978b214cb7dab9c61478",
 "scripts/cloud_tx_tree32_budget.py":"52999bc99256be7e2c414324a097d869e9bce81bdd2762720e522de79d4230f4",
 "scripts/cloud_tx_tree32_balanced_v5.py":"000490fa0545e5c2ba034a1e4be31886d7fbd59774bc0a3c143ad02c0c1e5766",
 "scripts/cloud_tx_balanced_v5_physical.py":"e19e2568a8d654602f2b3a9557c2822017b657579663353ff3d4c567b83cf6e0",
 "hw/soc/analog/pcie/tx_mux2_hbt_cascade_v4.spice":"c24851159489e6947989738bc6859e6731326b77ca9e17acaac9f6bd2d7b1495",
 "hw/soc/analog/pcie/tx_mux2_final_drive_v10_layout_core.spice":"afca836aec7c57b13fb541afe7ba38b8d47f5cc27c65f0129842228b7f46ae6b",
 "docs/evidence/tx-pre-nx1-balanced-v5-physical-input-20261017.json":"2e7d808cdb63fc28e3617a076b867cfb285396455b41c1a9ccd63b230e361f10",
 "docs/evidence/tx-pre-nx3-balanced-v5-physical-input-20261017.json":"437138b16bcb004a348d967ce9876d04c6adbde6069e5c53a54878734dd90889"}
SPECS={
 "pre":{"data":3.0,"selector":3.0,"tail":3.0,"reference":1.0,"emitters":55,
  "cell":"nssoc_tx_mux2_cascade158_nx3_balanced_v5_layout_v1",
  "schematic_sha256":"66a16ecc8fe42c77934f9f8b5acc6664560229a4fb05a92ffd372cfdfe2c4242"},
 "pre_low":{"data":1.0,"selector":1.0,"tail":1.0,"reference":1.0,"emitters":19,
  "cell":"nssoc_tx_mux2_cascade158_nx1_balanced_v5_layout_v1",
  "schematic_sha256":"683cc9d674002a6af305e02bf6a41f73d421f2423436a7b8ec34948e3805cf85"},
 "final":{"data":3.0,"selector":6.0,"tail":8.0,"reference":1.0,"emitters":77,
  "cell":"nssoc_tx_mux2_final_drive_v10_layout_v1",
  "schematic_sha256":"b9794930470d765d2321d8e39b2c8d7c44e17c1b635c38ae3ade682078105f43"}}
KINDS={"a":"pre","b":"pre",**{f"p{stride}_{i}":"pre_low"for stride in (4,8,16)for i in range(stride)},"f":"final"}
COUNTS={"data":12,"selector":4,"tail":2,"reference":1}
def source_catalog():
    for p,h in SOURCE_PINS.items():assert frozen.sha(ROOT/p)==h,(p,"Independent expected source changed")
    # The original scaling replaces ALL eighteen nonreference Nx8 HBTs,
    # and balanced-v5 changes four resistor cards only. Physical receipts
    # bind those sources to the exact child layouts used by the native tree.
    for n,kind in [(3,"pre"),(1,"pre_low")]:
        p=ROOT/f"docs/evidence/tx-pre-nx{n}-balanced-v5-physical-input-20261017.json"
        r=json.loads(p.read_text())
        assert r["source_run"]==39063246309 and r["source_head"]=="3a48fc11b8af859bf8199416a23f653249429f5e"
        assert r["generated_outputs"]["schematic.cir"]==SPECS[kind]["schematic_sha256"]
        assert r["candidate_sha256"]=={3:"e41ee27d762dbdb2cbe658ac38168fcdcb7869b2195a64761fb38396cd2f0f76",1:"6ca409feb9337f2c960b6f15e7ee85c6885bf568e012cc484c5c059e43d26632"}[n]
    text=(ROOT/"hw/soc/analog/pcie/tx_mux2_final_drive_v10_layout_core.spice").read_text()
    cards=[l.split()for l in text.splitlines()if l.startswith("X")and"npn13G2"in l]
    assert len(cards)==19
    for row in cards:
        role="reference"if row[0]=="XREF"else"selector"if row[0].startswith(("XSA_","XSB_"))else"tail"if row[0].startswith("XT_")else"data"
        assert row[5]=="npn13G2"and row[6]==f"Nx={int(SPECS['final'][role])}"
    return {"pins":SOURCE_PINS,"kinds":KINDS,"specs":SPECS,
     "scope":"Independent canonical source and passed child physical receipts; actual extracted values are compared, never learned as expected values."}
def mismatches(blocks):
    bad=[]
    def need(ok,where,expected,actual):
        if not ok:bad.append({"where":where,"expected":expected,"actual":actual})
    need(len(blocks)==31,"macro count",31,len(blocks))
    need({b["label"]for b in blocks}==set(KINDS),"macro labels",sorted(KINDS),sorted(b["label"]for b in blocks))
    seen=set();totals={k:0 for k in COUNTS};emitters=0
    for block in blocks:
        label=block["label"];kind=KINDS.get(label)
        need(kind==block["kind"],label+".kind",kind,block["kind"])
        if kind is None:continue
        ds=block["devices"]
        need(len(ds)==19,label+".HBT count",19,len(ds))
        for role,n in COUNTS.items():
            actual=sum(d["role"]==role for d in ds);need(actual==n,label+"."+role+".count",n,actual);totals[role]+=actual
        stage_total=0
        for d in ds:
            did=d["native_id"];role=d["role"]
            need(did not in seen,label+".device_unique",True,did not in seen);seen.add(did)
            need(d["model"]=="npn13G2",label+"."+str(did)+".model","npn13G2",d["model"])
            nx=d["parameters"].get("nx")
            finite=isinstance(nx,(int,float))and not isinstance(nx,bool)and math.isfinite(nx)
            want=SPECS[kind].get(role)
            need(finite and nx==want,label+"."+str(did)+"."+role+".Nx",want,nx)
            if finite:stage_total+=nx
        need(stage_total==SPECS[kind]["emitters"],label+".emitters",SPECS[kind]["emitters"],stage_total);emitters+=stage_total
    need(totals=={"data":372,"selector":124,"tail":62,"reference":31},"role census",{"data":372,"selector":124,"tail":62,"reference":31},totals)
    need(emitters==719,"actual mux emitters",719,emitters)
    return bad
def verify_original_failure(original,witness):
    assert original["type"]=="AssertionError"and original["message"]=="Actual selector/tail emitter multiplier changed"
    assert original["frames"][-2:]==[
     {"function":"bind","line":75,"file":"bind_tx_output8088_native_clock_roles.py"},
     {"function":"nx","line":31,"file":"bind_tx_output8088_native_clock_roles.py"}]
    assert original["failing_device"]=={"native_id":witness["native_id"],"parameters":witness["parameters"]}
    assert original["bind_context"]=={"macro":witness["macro"],"clock_leg":witness["clock_leg"]}
def controls():
    source_catalog();blocks=[];did=1
    for label,kind in KINDS.items():
        ds=[]
        for role,count in COUNTS.items():
            for _ in range(count):
                ds.append({"native_id":did,"role":role,"model":"npn13G2","parameters":{"nx":SPECS[kind][role]}});did+=1
        blocks.append({"label":label,"kind":kind,"devices":ds})
    assert not mismatches(blocks)
    faults=[]
    for name in ("blanket8","wrong_high_selector","wrong_low_tail","wrong_final_selector","wrong_final_tail","wrong_data","wrong_reference","wrong_kind","missing_macro","duplicate_macro","duplicate_device","wrong_model","missing_selector","wrong_role","nan","boolean"):
        b=copy.deepcopy(blocks)
        def dev(label,role):return next(d for q in b if q["label"]==label for d in q["devices"]if d["role"]==role)
        if name=="blanket8":
            for q in b:
                for d in q["devices"]:
                    if d["role"]in("selector","tail"):d["parameters"]["nx"]=8.0
        elif name=="wrong_high_selector":dev("a","selector")["parameters"]["nx"]=8.
        elif name=="wrong_low_tail":dev("p4_0","tail")["parameters"]["nx"]=8.
        elif name=="wrong_final_selector":dev("f","selector")["parameters"]["nx"]=8.
        elif name=="wrong_final_tail":dev("f","tail")["parameters"]["nx"]=6.
        elif name=="wrong_data":dev("a","data")["parameters"]["nx"]=1.
        elif name=="wrong_reference":dev("a","reference")["parameters"]["nx"]=3.
        elif name=="wrong_kind":b[0]["kind"]="pre_low"
        elif name=="missing_macro":b.pop()
        elif name=="duplicate_macro":b[-1]=copy.deepcopy(b[0])
        elif name=="duplicate_device":b[0]["devices"][1]["native_id"]=b[0]["devices"][0]["native_id"]
        elif name=="wrong_model":dev("a","selector")["model"]="npn13G2L"
        elif name=="missing_selector":b[0]["devices"].remove(dev("a","selector"))
        elif name=="wrong_role":dev("a","selector")["role"]="data"
        elif name=="nan":dev("a","selector")["parameters"]["nx"]=float("nan")
        else:dev("a","selector")["parameters"]["nx"]=True
        errors=mismatches(b);assert errors,("Missed source catalog fault",name)
        faults.append({"name":name,"rejected":True})
    witness={"native_id":17,"parameters":{"nx":3.0},"macro":"a","clock_leg":"sap"}
    original={"type":"AssertionError","message":"Actual selector/tail emitter multiplier changed",
     "frames":[{"function":"bind","line":75,"file":"bind_tx_output8088_native_clock_roles.py"},{"function":"nx","line":31,"file":"bind_tx_output8088_native_clock_roles.py"}],
     "failing_device":{"native_id":17,"parameters":{"nx":3.0}},"bind_context":{"macro":"a","clock_leg":"sap"}}
    verify_original_failure(original,witness);failure_faults=[]
    for name in ("type","message","callsite","device","parameters","owner"):
        wrong=copy.deepcopy(original)
        if name=="type":wrong["type"]="RuntimeError"
        elif name=="message":wrong["message"]="Unrelated assertion"
        elif name=="callsite":wrong["frames"][-2]["line"]=95
        elif name=="device":wrong["failing_device"]["native_id"]+=1
        elif name=="parameters":wrong["failing_device"]["parameters"]["nx"]=8.
        else:wrong["bind_context"]["clock_leg"]="san"
        try:verify_original_failure(wrong,witness)
        except AssertionError:failure_faults.append({"name":name,"rejected":True})
        else:raise AssertionError("Accepted wrong original failure "+name)
    return {"status":"PASS_CANONICAL_STAGE_CATALOG_AND16_CORRUPTIONS_NOT_NATIVE_PROOF","faults":faults,"original_failure_faults":failure_faults,"native_execution":False}
def inspect_native(g):
    pya=g["pya"];rows=g["rows"];ds=g["devices"];records=g["records"]
    def cl(d,t):return rows[d,t]["native_cluster"]
    blocks=[]
    for macro in g["plan"]["nodes"]:
        label=macro["label"];kind=macro["kind"];placement=g["cm"]["placements"][label]
        assert kind==KINDS[label]==placement["kind"],"Native child kind disagrees with pinned plan"
        box=g["shifted"](placement["bbox_um"])
        local={d for d,b in g["hbts"].items()if(b&box)==b};assert len(local)==19
        used=set();items=[];selector_emitters=set();banks={}
        def add(d,role,bank=None,leg=None):
            assert d not in used;used.add(d);obj=ds[d];cls=obj.device_class()
            ps={p.name.lower():obj.parameter(p.id())for p in cls.parameter_definitions()}
            terminals={t:cl(d,t)for t in ("C","B","E","S")}
            items.append({"native_id":d,"instance":records[d]["instance"],"role":role,"bank":bank,"clock_leg":leg,
             "model":cls.name,"parameters":ps,"native_clusters":terminals,
             "composed_terminals":records[d]["terminals"]})
        for leg,bank,inp in zip("pn",("a","b"),macro["inputs"],strict=True):
            endpoint=g["endpoint"](label+".s"+leg);port=macro["clock"]+leg
            assert endpoint["native_cluster"]==g["public"][port]
            pi=g["integration"]["external_ports"][port];point=pya.Box.from_s(pi["box_dbu"]).center()
            assert g["probe"](pi["layer"],point).cluster_id==g["public"][port]
            data=sorted(t["native_id"]for suffix in "pn"for t in g["expected"][inp+suffix]["terminals"])
            assert len(set(data))==6 and set(data)<=local
            emitters={cl(d,"E")for d in data};assert len(emitters)==1;collector=next(iter(emitters));banks[bank]=collector
            sels=sorted(d for d in local if cl(d,"B")==endpoint["native_cluster"]);assert len(sels)==2
            for d in data:add(d,"data",bank)
            for d in sels:
                assert cl(d,"C")==collector
                selector_emitters.add(cl(d,"E"));add(d,"selector",bank,port)
        assert banks["a"]!=banks["b"]and len(selector_emitters)==1
        tail=next(iter(selector_emitters));iref=g["endpoint"](label+".iref")["native_cluster"];avss=g["endpoint"](label+".avss")["native_cluster"]
        tails=sorted(d for d in local if cl(d,"C")==tail and cl(d,"B")==iref and cl(d,"E")==avss);assert len(tails)==2
        for d in tails:add(d,"tail")
        refs=local-used;assert len(refs)==1;ref=next(iter(refs))
        assert cl(ref,"C")==cl(ref,"B")==iref and cl(ref,"E")==avss;add(ref,"reference")
        assert used==local
        blocks.append({"label":label,"kind":kind,"clock":macro["clock"],"bbox_um":placement["bbox_um"],"devices":items,
         "bank_clusters":banks,"tail_cluster":tail,"iref_cluster":iref,"avss_cluster":avss})
    return blocks
def main():
    assert os.environ.get("GITHUB_ACTIONS")=="true"and os.environ.get("RUNNER_ENVIRONMENT")=="github-hosted"
    assert os.environ["GITHUB_REPOSITORY"]=="Melihakbulut221/nssoc"
    workspace,summary,out=map(Path,sys.argv[1:]);assert frozen.sha(summary)==frozen.SUMMARY
    catalog=source_catalog()
    for p,h in frozen.PIN.items():assert frozen.sha(workspace/p)==h
    top=json.loads((workspace/"topology.json").read_text())
    for kind,spec in SPECS.items():assert top["outputs"]["inputs/"+kind+"/layout/schematic.cir"]==spec["schematic_sha256"]
    out.mkdir(parents=True,exist_ok=False)
    previous=sys.argv
    try:
        sys.argv=[str(workspace/"bind-native-interfaces.py"),str(workspace),str(out/"original-interfaces.json")]
        g=runpy.run_path(sys.argv[0],run_name="__main__")
    finally:sys.argv=previous
    assert frozen.sha(out/"original-interfaces.json")==frozen.PIN["interfaces.json"]
    blocks=inspect_native(g);bad=mismatches(blocks)
    legacy_first=next({"macro":b["label"],**d}for b in blocks for d in b["devices"]if d["role"]=="selector"and d["parameters"]["nx"]!=8.0)
    try:frozen.bind(g)
    except AssertionError as e:
        original={"type":type(e).__name__,"message":str(e),"traceback":traceback.format_exc(),
         "frames":[{"function":x.name,"line":x.lineno,"file":Path(x.filename).name}for x in traceback.extract_tb(e.__traceback__)]}
        frames=[];tb=e.__traceback__
        while tb is not None:
            frames.append(tb.tb_frame);tb=tb.tb_next
        nx_frame=frames[-1];bind_frame=frames[-2]
        assert nx_frame.f_code.co_name=="nx"and bind_frame.f_code.co_name=="bind"
        original["failing_device"]={"native_id":nx_frame.f_locals["did"],"parameters":copy.deepcopy(nx_frame.f_locals["p"])}
        original["bind_context"]={"macro":bind_frame.f_locals["label"],"clock_leg":bind_frame.f_locals["key"]}
        verify_original_failure(original,legacy_first)
    else:raise AssertionError("Frozen original rejection did not reproduce")
    assert all(frozen.sha(workspace/p)==h for p,h in frozen.PIN.items());source_catalog()
    report={"status":"PASS_EXACT_STAGE_ROLE_PARAMETER_DIAGNOSIS_ORIGINAL_BINDER_REJECTION_REMAINS"if not bad else"FAIL_ACTUAL_STAGE_ROLE_PARAMETER_MISMATCH",
     "catalog":catalog,"blocks":blocks,"mismatches":bad,"original_failure":original,"first_legacy_selector_rejection":legacy_first,
     "counts":{"muxes":len(blocks),"HBTs":sum(len(b["devices"])for b in blocks),"emitters":sum(d["parameters"]["nx"]for b in blocks for d in b["devices"])},
     "qualified_inputs_unchanged":True,"original_interfaces_sha256":frozen.sha(out/"original-interfaces.json"),
     "original_binder_unchanged":True,"native_role_accepted":False,"electrical_accepted":False,"full_phy_accepted":False,
     "no_new_extraction_or_simulation":True}
    (out/"parameter-diagnosis.json").write_text(json.dumps(report,indent=2)+"\n")
    assert not bad,("Actual parameters disagree with independent canonical source",bad)
    print(report["status"])
if __name__=="__main__":main()
