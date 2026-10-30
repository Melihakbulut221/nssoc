#!/usr/bin/env python3
"""Hosted source/metadata and actual controller fixtures; synthetic native/archive I/O only."""
import argparse,ast,copy,hashlib,io,json,os,subprocess,sys,tarfile,tempfile,traceback,types,unittest
from pathlib import Path
from unittest.mock import patch
import cdr_drain_m1_fresh_rc_admission as e
import cdr_drain_m1_fresh_rc_legacy as stages
import cloud_cdr_drain_m1_fresh_rc as d
import check_cdr_selector_width_fresh_rc_lifecycle as old
import check_cdr_drain_m1_fresh_graph as prior
RECORDS=[]
def record(label,kind,**extra):RECORDS.append(dict(case=label,kind=kind,**extra))
class Harness(unittest.TestCase):
    def refuse(self,label,call,kind=AssertionError,contains=None):
        with self.assertRaises(kind)as caught:call()
        if contains:self.assertIn(contains,str(caught.exception))
        record(label,"refusal",error=repr(caught.exception));return caught.exception

def derivations():
    files={}
    for suffix in ("binding","wire_rc","mim_capture","mim_audit","mim_precision"):
        oldpath=e.ROOT/("scripts/cloud_cdr_selector_width_fresh_"+suffix+".py")
        path=e.ROOT/("scripts/cloud_cdr_drain_m1_fresh_"+suffix+".py")
        raw=path.read_bytes();before=oldpath.read_bytes()
        assert raw.replace(b"cdr_drain_m1_fresh_rc_legacy",b"cdr_selector_width_fresh_rc_legacy")==before
        files[str(path.relative_to(e.ROOT))]=dict(bytes=len(raw),sha256=e.sha(path),original_sha256=e.sha(oldpath),
          only_admission_import_changed=True)
    funcs=lambda t:{n.name:ast.get_source_segment(t,n)for n in ast.parse(t).body if isinstance(n,ast.FunctionDef)}
    a=funcs((e.ROOT/"scripts/cloud_cdr_selector_width_fresh_rc.py").read_text());b=funcs(Path(d.__file__).read_text())
    unchanged=("inventory","storage","tokenless","exception_record","output_map","fallback","save_result","execute",
      "pipeline_validator","validate_completed_pipeline","finalization","main_run","publication_result","publish","main")
    for name in unchanged:assert a[name]==b[name],name
    a=funcs((e.ROOT/"scripts/cdr_selector_width_fresh_rc_legacy.py").read_text());b=funcs(Path(stages.__file__).read_text())
    numerical=("binding_target_controls","finalize_rc_outputs","stage_report","stage_pin","binding_pin",
      "restore_inputs","handoff","verify_restored","project_for_capture","verify_projection","derived")
    for name in numerical:assert a[name]==b[name],name
    assert list(d.SECONDS.values())==[1200]*4
    assert e.BINDING_FILES==("wire/device-locations01.json","parent/layout/result.json","parent/layout/schematic.cir",
      "parent/physical/lvs_flat/extracted.cir","parent/physical/lvs_flat/audit.json","parent/physical/lvs_flat/result.lvsdb")
    return dict(workers=files,unchanged_host_functions=list(unchanged),unchanged_numerical_stage_functions=list(numerical),
      original_four_1200s_budgets=True)

def actual_controller_fixtures():
    # Rebind only the frozen fixture's e/d/record globals. Production bodies are real new modules.
    names=("test_original_controller_numerical_and_supervisor_boundaries",
      "test_actual_execute_timeout_stream_and_save_failures","test_actual_main_and_independent_finalization",
      "test_save_fallback_encode_emit_and_inventory_cannot_mask_primary","test_failed_envelopes_and_scope_refusals",
      "test_real_pack_publication_empty_failure_and_no_clobber")
    instance=Harness()
    for name in names:
        fn=getattr(old.Controls,name)
        namespace=dict(fn.__globals__,e=e,d=d,record=record)
        cloned=types.FunctionType(fn.__code__,namespace,fn.__name__,fn.__defaults__,fn.__closure__)
        assert cloned.__code__ is fn.__code__
        cloned(instance)
    return dict(exact_fixture_methods=list(names),actual_new_controller=True,
      synthetic_native_transport_only=True,native_payload_acquired=False)

def synthetic_restore():
    # Full cardinality and real streaming selector, but every payload byte is an explicit synthetic fixture.
    real=e.contract();original=e.read_json(e.CONFIG)
    with tempfile.TemporaryDirectory()as temp:
        root=Path(temp);analysis=root/"canonical";out=root/"output";out.mkdir()
        c=copy.deepcopy(real);q=c["qualified_input"];q["fresh_graph_qualification"]["fresh_report_bindings"]={}
        values={n:("EXPLICIT_SYNTHETIC_NOT_NATIVE "+n).encode()for n in q["full"]}
        current={n:dict(bytes=len(values[q["view_prefix"]+n]),sha256=hashlib.sha256(values[q["view_prefix"]+n]).hexdigest())for n in q["current_files"]}
        q["current_files"]=current;q["fresh_graph_qualification"]["current_files"]=current
        report=q["report_prefix"]+"graph-qualification.json"
        values[report]=(json.dumps(q["fresh_graph_qualification"],sort_keys=True)+"\n").encode()
        q["full"]={n:hashlib.sha256(b).hexdigest()for n,b in values.items()}
        c["transport"]["expected_sha256"]=q["full"];c["canonical_candidate"]["expected_sha256"]={n:v["sha256"]for n,v in current.items()}
        fixture=root/"synthetic.tar.gz"
        with tarfile.open(fixture,"w:gz")as tar:
            for name,raw in values.items():
                item=tarfile.TarInfo(q["source_directory"]+"/"+name);item.size=len(raw);tar.addfile(item,io.BytesIO(raw))
        metadata={
          "actions/runs/"+str(e.GRAPH_RUN):e.read_json(e.ROOT/q["proof_prefix"]/"run.json"),
          "actions/runs/"+str(e.GRAPH_RUN)+"/attempts/1/jobs?per_page=100":e.read_json(e.ROOT/q["proof_prefix"]/"jobs.json"),
          "releases/"+str(q["release_id"]):e.read_json(e.ROOT/q["proof_prefix"]/"release.json"),
          "git/ref/tags/"+q["tag"]:e.read_json(e.ROOT/q["proof_prefix"]/"tag-ref.json")}
        def download(pin,path):path.write_bytes(fixture.read_bytes())
        with patch.object(e,"OUT",out),patch.object(e,"ANALYSIS",analysis),patch.object(e,"authorize",return_value={}),\
             patch.object(e,"methods",return_value={}),patch.object(e,"contract",return_value=c),\
             patch.object(e.release,"api",side_effect=lambda path:copy.deepcopy(metadata[path])),patch.object(e.graph.frozen,"download",download):
            result=e.restore()
            assert result["complete_graph_members"]==138 and result["current_members"]==75
            assert len(list(p for p in analysis.rglob("*")if p.is_file()))==75
            assert not(analysis/"result.json").exists()
            saved=out/"restore/graph-input"
            victim=saved/next(iter(q["full"]));victim.write_bytes(b"tamper")
            Harness().refuse("synthetic restored member drift",lambda:e.verify_saved(saved,c))
        return dict(actual_restore_and_selector=True,synthetic_archive_members=138,current_projection=75,
          native_archive_restoration_qualified=False,complete_raw_synthetic_files_preserved_until_fixture_cleanup=True)

def reservation_controls(method):
    harness=Harness();m=copy.deepcopy(method)
    for name in e.NATIVE:m[name]=True
    m["source_controls_authorized"]=m["controller_readiness"]=True
    tag,head=e.release.context(e.GROUP,os.environ)
    remote=dict(id=42,tag_name=tag,target_commitish=head,draft=False,prerelease=True,assets=[])
    ref=dict(ref="refs/tags/"+tag,object=dict(type="commit",sha=head))
    binding=dict(bytes=123,sha256="a"*64)
    with tempfile.TemporaryDirectory(dir=e.ROOT)as temp:
        path=Path(temp)/"reservation.json"
        with patch.object(e,"methods",return_value=m),patch.object(e,"RESERVATION",path),\
             patch.object(e,"controls_binding",return_value=binding),patch.object(e,"wait",return_value={}),\
             patch.object(e.release,"api",side_effect=lambda name:copy.deepcopy(remote if name.startswith("releases/")else ref)):
            result=e.preflight();value=e.read_json(path)
            with patch.dict(os.environ,{e.RESERVATION_ENV:e.sha(path)}):
                assert e.authorize()==m and result["sha256"]==e.sha(path)
                assert value["current_source_controls"]==binding
                harness.refuse("reservation no overwrite",e.preflight)
                path.write_bytes(path.read_bytes()+b" ")
                harness.refuse("reservation altered bytes",e.authorize)
    
    for label,mutate in (
      ("source",lambda r:r.update(source_head="b"*40)),
      ("attempt",lambda r:r.update(run_attempt=2)),
      ("manifest",lambda r:r.update(graph_manifest_sha256="b"*64)),
      ("controls",lambda r:r["current_source_controls"].update(bytes=0)),
      ("preexisting asset",lambda r:r["release"]["assets"].append(dict(id=1,name="old",size=1,digest="sha256:"+"b"*64)))):
        bad=copy.deepcopy(value);mutate(bad)
        harness.refuse("reservation "+label,lambda bad=bad:e.validate_reservation(bad,m))
    actual=e.sha;victim=e.ROOT/e.ENTRIES["binding"]
    with patch.object(e,"sha",side_effect=lambda path:"0"*64 if Path(path)==victim else actual(path)):
        harness.refuse("actual new worker source corruption",e.methods)
    record("actual current preflight and receipt validators","positive",remote_IO_synthetic=True,native_acquired=False)
    return dict(actual_production_preflight=True,refusals=8,synthetic_release_only=True)

def controls():
    RECORDS.clear();m=e.methods();assert m["source_controls_authorized"] is True;actual=e.contract()
    record("actual new138/75 source metadata","positive",graph=e.GRAPH_RUN,physical=e.PHYSICAL_RUN)
    derivation=derivations();record("reversible numerical derivation","positive")
    harness=Harness()
    for active in (False,True):
        base=copy.deepcopy(m)
        for k in e.NATIVE:base[k]=active
        base["controller_readiness"]=active
        e.validate_authorizations(base)
        for key in e.NATIVE+e.FALSE+("source_controls_authorized","controller_readiness"):
            bad=copy.deepcopy(base);bad[key]=1
            harness.refuse("typed "+str(active)+" "+key,lambda bad=bad:e.validate_authorizations(bad))
        bad=copy.deepcopy(base);bad[e.NATIVE[0]]=not active
        harness.refuse("split "+str(active),lambda bad=bad:e.validate_authorizations(bad))
        bad=copy.deepcopy(base);bad["physical_accepted"]=True
        harness.refuse("acceptance "+str(active),lambda bad=bad:e.validate_authorizations(bad))
    record("both typed authority baselines","positive",native_functions_called=False)
    original=e.read_json(e.CONFIG);reader=e.read_json
    for label,mutate in (
      ("old graph run",lambda c:c["producer"].update(id=40808550817)),
      ("old graph source",lambda c:c["producer"].update(head_sha="0"*40)),
      ("wrong GDS",lambda c:c["fresh_graph_qualification"]["candidate_gds"].update(sha256="0"*64)),
      ("wrong LVS",lambda c:c["fresh_graph_qualification"]["candidate_lvs"].update(sha256="0"*64)),
      ("missing current",lambda c:c["current_files"].pop(next(iter(c["current_files"])))),
      ("missing full member",lambda c:c["full"].pop(next(iter(c["full"])))),
      ("member hash",lambda c:c["full"].__setitem__(next(iter(c["full"])),"0"*64)),
      ("old physical",lambda c:c["physical_producer"].update(run_id=40800207491)),
      ("wrong terminal join",lambda c:c["terminal_join"]["T003_D"].update(new_component=-1)),
      ("wrong receipt",lambda c:c.update(receipt_sha256="0"*64))):
        bad=copy.deepcopy(original);mutate(bad)
        with patch.object(e,"read_json",side_effect=lambda p,bad=bad:bad if Path(p)==e.CONFIG else reader(p)):
            harness.refuse(label,e.contract)
    restored=synthetic_restore();record("actual restore synthetic boundary","positive")
    reservation_result=reservation_controls(m)
    lifecycle=actual_controller_fixtures()
    return dict(status="PASS_DRAIN_M1_FRESH_RC_SOURCE_CONTROLS",passed=True,
      positive=sum(r["kind"]=="positive"for r in RECORDS),refusal=sum(r["kind"]=="refusal"for r in RECORDS),
      records=copy.deepcopy(RECORDS),derivation=derivation,synthetic_restore=restored,reservation_controls=reservation_result,actual_controller_fixtures=lifecycle,
      native_executed=False,electrical_acceptance=False,physical_acceptance=False,actual_native_graph_restore_not_tested=True)

def main():
    p=argparse.ArgumentParser();p.add_argument("--output",required=True,type=Path);args=p.parse_args()
    # Source-only context is independent of native activation and performs no acquisition.
    assert os.environ["GITHUB_ACTIONS"]=="true"and os.environ["GITHUB_EVENT_NAME"]=="workflow_dispatch"
    assert os.environ["GITHUB_RUN_ATTEMPT"]=="1"and os.environ["GITHUB_REF"]=="refs/heads/"+e.BRANCH
    current=dict(source=os.environ["GITHUB_SHA"],run_id=int(os.environ["GITHUB_RUN_ID"]),attempt=1,source_controls_only=True,native_executed=False)
    primary=None
    try:r=controls();r["current_context"]=current
    except BaseException as error:
        primary=error;r=dict(status="FAIL_DRAIN_M1_FRESH_RC_SOURCE_CONTROLS",passed=False,error=repr(error),
          traceback=traceback.format_exc(),current_context=current,native_executed=False,electrical_acceptance=False)
    prior.previous.old.finish_report(args.output,r,primary)
if __name__=="__main__":main()
