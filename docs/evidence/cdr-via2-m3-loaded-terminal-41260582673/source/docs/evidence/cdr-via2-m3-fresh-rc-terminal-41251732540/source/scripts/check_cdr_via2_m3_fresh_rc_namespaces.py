#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted synthetic current-binding/definition controls; no project native payload."""
import ast,copy,json,os,subprocess,sys,tempfile,traceback
from pathlib import Path
import cdr_via2_m3_fresh_rc_namespaces as n

ROOT=Path(__file__).resolve().parents[1]
BRANCH="codex/cdr-via2-m3-fresh-rc-namespace-source"
CONFIG="scripts/cdr-via2-m3-fresh-rc-namespace-inputs.json"
MANIFEST="scripts/cdr-via2-m3-fresh-rc-namespace-pins.json"
RECORDS=[]
FROZEN_BINDING_PIN={"bytes":19381,"sha256":"7b3cb1a93462be997d4379973b623ab57d29b6b6706a13eaa1d864bfefff80df"}

def source_guard():
    env=os.environ
    n.require(env.get("GITHUB_ACTIONS")=="true"and env.get("RUNNER_ENVIRONMENT")=="github-hosted"and env.get("GITHUB_JOB")=="source-controls","hosted source controls only")
    n.require(env.get("GITHUB_REPOSITORY")=="Melihakbulut221/nssoc"and env.get("GITHUB_EVENT_NAME")=="workflow_dispatch"and env.get("GITHUB_REF")=="refs/heads/"+BRANCH,"exact manual source branch")
    n.require(env.get("GITHUB_RUN_ATTEMPT")=="1"and env.get("APPROVED_SOURCE")==env.get("GITHUB_SHA"),"exact current source, no rerun")
    head=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()
    n.require(head==env["GITHUB_SHA"],"exact checked-out source")
    raw=n.regular(ROOT,MANIFEST).read_bytes()
    n.require(raw==subprocess.check_output(["git","show",head+":"+MANIFEST],cwd=ROOT),"immutable current manifest")
    manifest=n.decode(raw)
    n.require(manifest["schema"]=="cdr-via2-m3-fresh-rc-namespace-source-pins-v1"and manifest["native_authority"]is False,"source-only manifest")
    for path,pin in manifest["files"].items():n.require(n.pin(n.regular(ROOT,path).read_bytes())==pin,"source bytes changed: "+path)
    config=n.validate_config(n.decode(n.regular(ROOT,CONFIG).read_bytes()))
    return dict(source=head,run_id=int(env["GITHUB_RUN_ID"]),attempt=1),config

def record(name,kind,**proof):
    n.require(name not in {row["name"]for row in RECORDS},"duplicate test name")
    RECORDS.append(dict(name=name,kind=kind,passed=True,**proof))

def reject(name,call):
    try:call()
    except(ValueError,AssertionError,KeyError,TypeError,FileNotFoundError,SyntaxError)as error:record(name,"expected_refusal",error=repr(error))
    else:raise AssertionError("invalid fixture accepted: "+name)

def packet(source="a"*40,run=12345,width="2",length="3"):
    devices=[];ident=0
    for native_model,model,count in [("npn13G2","npn13g2",124),("sg13_lv_nmos","sg13_lv_nmos",50),("rppd","rppd",98),("cap_cmim","cap_cmim",7),("ptap1","ptap1",221)]:
        for _ in range(count):
            ident+=1;row=dict(native_id=ident,native_model=native_model,model=model)
            if model=="cap_cmim":row["native_parameters"]=dict(w=width,l=length)
            devices.append(row)
    report=dict(source_head=source,status=n.BINDING_PASS,sources_unchanged=True,explicit_synthetic_fixture=True,
      native_simulation_passed=False,qualified_pex=False,wire_rc_included=False,full_phy_accepted=False,closed_loop=False,
      binding=dict(census=n.CENSUS.copy(),devices=devices,native_ports=["fixture_port_"+str(i)for i in range(25)]),
      controls=[dict(name="synthetic_fault_"+str(i),rejected=True)for i in range(14)],
      target_length_controls=dict(actual_fresh_binding=True,rejected=["synthetic_target_"+str(i)for i in range(6)]),
      native_contact_comparisons=[dict(explicit_synthetic=True,index=i)for i in range(221)],
      contact_model_controls=dict(rejected_geometry=["synthetic"]*3,rejected_compact_models=["synthetic"]*3))
    summary=n.encode(report);descriptor=dict(run=run,source_head=source,summary_sha256=n.pin(summary)["sha256"],report=report)
    return dict(descriptor=n.encode(descriptor),summary=summary)

def reader(value,source="a"*40,run=12345):
    return n.CurrentBinding(lambda:value,dict(source=source,run_id=run,attempt=1),n.pin(value["descriptor"]))

def mim_args(report):
    rows=[["parameters","cap_cmim","w=w","l=l"]];replacement=[];devices=[];mapping={};anchors=dict(rows=[])
    caps=[d for d in report["binding"]["devices"]if d["model"]=="cap_cmim"]
    for i,d in enumerate(caps):
        plus="synthetic_p_"+str(i);minus="synthetic_m_"+str(i);cp=2*i+1;cm=2*i+2
        mapping[plus]=cp;mapping[minus]=cm
        for terminal,component in(("mim_top",cp),("mim_btm",cm)):anchors["rows"].append(dict(device=d["native_id"],terminal=terminal,wire_component=component))
        w=n.Decimal(d["native_parameters"]["w"]);l=n.Decimal(d["native_parameters"]["l"])
        params=(("l",l*n.Decimal("1e-6")),("w",w*n.Decimal("1e-6")))
        devices.append(([plus,minus],"cap_cmim",params))
        box=list(map(str,(10*i,0,10*i+5,5)))
        rows.append(["device","csubckt","cap_cmim",*box,"w="+str(w/n.Decimal(".005")),"l="+str(l/n.Decimal(".005")),"None",plus,"0","0",minus,"0","0"])
        replacement.append(["device","csubckt","cap_cmim",*box,"None",plus,"0","0",minus,"0","0"])
    return rows,replacement,dict(devices=copy.deepcopy(devices)),dict(devices=copy.deepcopy(devices)),mapping.copy(),mapping.copy(),anchors

def real_schema_source_control():
    # Independent inspection of the unchanged producer, not implementation constants.
    path=ROOT/"scripts/cloud_cdr_current_eight_drain_fresh_binding.py"
    raw=path.read_bytes()
    n.require(n.pin(raw)==FROZEN_BINDING_PIN,"exact frozen binding producer")
    tree=ast.parse(raw);build=next(x for x in tree.body if isinstance(x,ast.FunctionDef)and x.name=="build")
    model_assign=[x for x in ast.walk(build)if isinstance(x,ast.Assign)and len(x.targets)==1 and isinstance(x.targets[0],ast.Name)and x.targets[0].id=="model"]
    expected=ast.parse('model="npn13g2"if kind=="npn13G2"else kind').body[0]
    n.require(len(model_assign)==1 and ast.dump(model_assign[0],include_attributes=False)==ast.dump(expected,include_attributes=False),"actual frozen producer compact model spelling")
    rows=[x for x in ast.walk(build)if isinstance(x,ast.Assign)and len(x.targets)==1 and isinstance(x.targets[0],ast.Name)and x.targets[0].id=="row"and isinstance(x.value,ast.Call)and isinstance(x.value.func,ast.Name)and x.value.func.id=="dict"]
    n.require(len(rows)==1,"actual frozen binding row schema")
    fields={x.arg:x.value for x in rows[0].value.keywords}
    n.require(ast.dump(fields["model"])==ast.dump(ast.Name(id="model",ctx=ast.Load()))and ast.dump(fields["native_model"])==ast.dump(ast.Name(id="kind",ctx=ast.Load())),"independent native and compact model fields")
    value=packet();report=reader(value).stage_report("binding")
    n.require(sum(d["native_model"]=="npn13G2"and d["model"]=="npn13g2"for d in report["binding"]["devices"])==124,"all actual-schema HBT conversions")
    record("actual_frozen_producer_schema_124_HBTs","source_bound_schema",producer_pin=FROZEN_BINDING_PIN,native_model="npn13G2",compact_model="npn13g2")

def definition_controls(config):
    scope={};text="raise RuntimeError('module main must not execute')\ndef safe():\n    return 17\n"
    node=next(x for x in ast.parse(text).body if isinstance(x,ast.FunctionDef))
    definition="".join(text.splitlines(keepends=True)[node.lineno-1:node.end_lineno]).rstrip()+"\n"
    loaded=n.select_definitions(text,dict(safe=n.pin(definition.encode())),scope,"explicit-synthetic-module")
    n.require(loaded["safe"]()==17 and scope=={},"only selected definition and isolated namespace")
    record("module_top_level_and_main_excluded","synthetic_source")
    for name,bad in [
      ("missing","def other():\n    pass\n"),
      ("duplicate","def safe():\n    pass\ndef safe():\n    pass\n"),
      ("decorator","@effect()\ndef safe():\n    pass\n"),
      ("default","def safe(x=effect()):\n    pass\n"),
      ("annotation","def safe(x:effect()):\n    pass\n"),
      ("import","def safe():\n    import historical_admission\n"),
      ("body","def safe():\n    return 18\n")]:
        reject("definition_"+name,lambda bad=bad:n.select_definitions(bad,dict(safe=n.pin(definition.encode())),{},"explicit-invalid-fixture"))
    reject("definition_global_collision",lambda:n.select_definitions(text,dict(safe=n.pin(definition.encode())),dict(safe=object()),"explicit-invalid-fixture"))
    current=reader(packet())
    with tempfile.TemporaryDirectory(prefix="synthetic-frozen-source-root-")as temp:
        root=Path(temp);path=root/n.FROZEN_PATH;path.parent.mkdir(parents=True)
        original=n.regular(ROOT,n.FROZEN_PATH).read_bytes();path.write_bytes(original+b"# altered frozen source\n")
        reject("changed_complete_frozen_source",lambda:n.intrinsic_namespace(root,config,current))
        path.unlink();path.symlink_to(n.regular(ROOT,n.FROZEN_PATH))
        reject("frozen_source_symlink",lambda:n.intrinsic_namespace(root,config,current))
    for name in(*n.NATIVE_FLAGS,"full_phy_accepted","electrical_accepted","timing_accepted"):
        bad=copy.deepcopy(config);bad[name]=True;reject("authority_"+name,lambda bad=bad:n.validate_config(bad))
    bad=copy.deepcopy(config);bad["candidate_view_producer"]=dict(run_id=1)
    reject("invented_candidate_view_binding",lambda:n.validate_config(bad))
    bad=copy.deepcopy(config);bad["source_pin"]["sha256"]="0"*64
    reject("changed_config_frozen_pin",lambda:n.validate_config(bad))
    reject("unconditional_native_entry",lambda:n.authorize_native(config))
    active=copy.deepcopy(config)
    for name in n.NATIVE_FLAGS:active[name]=True
    reject("native_entry_cannot_be_enabled_by_config",lambda:n.authorize_native(active))

def binding_controls(config):
    value=packet();provider=reader(value);original=copy.deepcopy(value)
    historical="cdr_v59_mim_admission"
    n.require(historical not in sys.modules,"historical admission was unexpectedly imported")
    namespace=n.intrinsic_namespace(ROOT,config,provider)
    n.require(historical not in sys.modules and namespace.validate_mim.__globals__["admission"]is provider,"old admission excluded and explicit current provider installed")
    n.require(namespace.native_authority is False and provider.identity()["native_authority"]is False,"no native authority")
    report=provider.stage_report("binding");proof=namespace.validate_mim(*mim_args(report))
    n.require(proof["devices"]==7 and proof["full_pex_qualified"]is False,"actual frozen intrinsic validator on seven synthetic devices")
    record("frozen_intrinsic_current_binding","synthetic_mim_records",devices=7,source_pin=namespace.source_identity["pin"])
    changed=provider.stage_report("binding");changed["binding"]["devices"].clear()
    n.require(len(provider.stage_report("binding")["binding"]["devices"])==500,"returned report aliases live binding")
    record("returned_binding_copy_isolated","synthetic_binding")
    reject("wrong_stage_not_readable",lambda:provider.stage_report("rc"))
    stale=reader(value,source="b"*40);reject("stale_source_binding",lambda:stale.stage_report("binding"))
    stale=reader(value,run=12346);reject("stale_run_binding",lambda:stale.stage_report("binding"))
    value["descriptor"]+=b" "
    reject("changed_current_descriptor_bytes",lambda:provider.stage_report("binding"))
    value.update(original);value["summary"]+=b" "
    reject("changed_current_summary_bytes",lambda:provider.stage_report("binding"))
    value.update(original)
    cases=[
      ("duplicate_native_id",lambda r:r["binding"]["devices"][-1].update(native_id=1)),
      ("wrong_model_census",lambda r:r["binding"]["devices"][0].update(model="cap_cmim")),
      ("old_uppercase_compact_HBT",lambda r:r["binding"]["devices"][0].update(model="npn13G2")),
      ("wrong_native_model_census",lambda r:r["binding"]["devices"][0].update(native_model="cap_cmim")),
      ("missing_native_model_field",lambda r:r["binding"]["devices"][0].pop("native_model")),
      ("same_censuses_wrong_row_pairing",lambda r:(r["binding"]["devices"][0].update(model="rppd"),r["binding"]["devices"][174].update(model="npn13g2"))),
      ("missing_port",lambda r:r["binding"]["native_ports"].pop()),
      ("missing_fault_control",lambda r:r["controls"].pop()),
      ("accepted_fault_control",lambda r:r["controls"][0].update(rejected=False)),
      ("missing_contact_oracle",lambda r:r["native_contact_comparisons"].pop()),
      ("old_source_report",lambda r:r.update(source_head="b"*40)),
      ("incomplete_result",lambda r:r.update(status="RUNNING")),
      ("electrical_acceptance",lambda r:r.update(native_simulation_passed=True)),
    ]
    for label,mutate in cases:
        bad_report=n.decode(original["summary"]);mutate(bad_report);bad_summary=n.encode(bad_report)
        bad_descriptor=n.decode(original["descriptor"]);bad_descriptor["report"]=bad_report;bad_descriptor["summary_sha256"]=n.pin(bad_summary)["sha256"]
        bad_packet=dict(descriptor=n.encode(bad_descriptor),summary=bad_summary)
        reject(label,lambda bad_packet=bad_packet:reader(bad_packet).stage_report("binding"))
    other_packet=packet(source="b"*40,run=23456,width="4",length="5")
    other=reader(other_packet,source="b"*40,run=23456)
    other_namespace=n.intrinsic_namespace(ROOT,config,other)
    n.require(namespace.validate_mim.__globals__ is not other_namespace.validate_mim.__globals__,"namespaces must be independent")
    n.require(other_namespace.validate_mim(*mim_args(other.stage_report("binding")))["devices"]==7,"second exact current binding")
    reject("stale_cross_namespace_intrinsic",lambda:other_namespace.validate_mim(*mim_args(provider.stage_report("binding"))))
    n.require(namespace.validate_mim(*mim_args(provider.stage_report("binding")))["devices"]==7,"first namespace changed")
    record("two_current_namespaces_no_global_cross_talk","synthetic_mim_records")
    n.require(historical not in sys.modules and value==original,"historical admission loaded or original fixture changed")
    record("historical_module_never_imported","source_module_inventory",historical_admission_loaded=False)
    reject("duplicate_JSON_key",lambda:n.decode(b'{"x":1,"x":2}'))
    reject("nonfinite_JSON",lambda:n.decode(b'{"x":NaN}'))

def main():
    out=ROOT/"namespace-source-controls";out.mkdir(exist_ok=False);primary=None
    try:
        context,config=source_guard();definition_controls(config);real_schema_source_control();binding_controls(config);source_guard()
        result=dict(status="PASS_CURRENT_BINDING_NAMESPACE_SOURCE_ONLY",context=context,passed=True,tests=len(RECORDS),
          records=RECORDS,source_only=True,native_acquisition=False,native_execution=False,RC_executed=False,electrical_simulation=False,
          actual_view_binding=None,full_phy_accepted=False,actual_production_binding_qualified=False)
    except BaseException as error:
        primary=error;result=dict(status="FAIL_CURRENT_BINDING_NAMESPACE_SOURCE_ONLY",passed=False,error=repr(error),traceback=traceback.format_exc(),records=RECORDS,native_execution=False)
    (out/"result.json").write_bytes(n.encode(result));print(json.dumps(result,sort_keys=True))
    if primary is not None:raise primary
if __name__=="__main__":main()
