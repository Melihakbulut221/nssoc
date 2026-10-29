#!/usr/bin/env python3
"""Hosted-only actual source/controller controls. All archive/native-I/O fixtures are synthetic."""
import argparse,copy,hashlib,io,json,os,tarfile,tempfile,traceback
from pathlib import Path
from unittest.mock import patch
import cloud_magic_resistor_provenance_build as b
import check_magic_resistor_provenance as prior

def controls(expected):
    positive=[];refused=[];life=[]
    c,_,_=b.source_guard(expected);positive.append("actual_full_protected_source")
    ctx=b.context(os.environ);positive.append("actual_hosted_context")
    def reject(name,fn):
        try:fn()
        except (AssertionError,ValueError,KeyError,FileNotFoundError):refused.append(name)
        else:raise AssertionError("accepted refusal: "+name)
    for key,value in [("GITHUB_REF","refs/heads/main"),("GITHUB_EVENT_NAME","push"),("GITHUB_RUN_ATTEMPT","2"),
      ("GITHUB_SHA","not-a-sha"),("GITHUB_RUN_ID","0"),("GITHUB_ACTIONS","false")]:
        env=dict(os.environ);env[key]=value;reject("context:"+key,lambda env=env:b.context(env))
    reject("changed_source_manifest",lambda:b.source_guard("0"*64))
    pins,spec=b.historical.source_guard()
    before={n:b.historical.secure(b.ROOT,r["snapshot"]).read_bytes()for n,r in spec["files"].items()}
    expected_fixture={n:hashlib.sha256(v).hexdigest()for n,v in before.items()}
    payloads={r["payload"]:b.historical.secure(b.ROOT,r["payload"]).read_bytes()for r in spec["rules"]if "payload"in r}
    # These are historical source fixtures, not a claim that the three old inputs are qualified.
    after=b.trace_sources(before,expected_fixture,spec["rules"],payloads)
    assert after==b.historical.transform(before);positive.append("real_literal_insertions_reverse_historical_fixture")
    wrong=dict(before);wrong.pop(next(iter(wrong)));reject("missing_patch_input",lambda:b.trace_sources(wrong,expected_fixture,spec["rules"],payloads))
    wrong=dict(before);wrong[next(iter(wrong))]+=b"\n";reject("changed_patch_input",lambda:b.trace_sources(wrong,expected_fixture,spec["rules"],payloads))
    actual={n:c["source_producer"]["candidate"][n]for n in before}
    reject("old_upstream_snapshots_cannot_be_native_baseline",lambda:b.trace_sources(before,actual,spec["rules"],payloads))
    wrong=copy.deepcopy(spec["rules"]);wrong[0]["anchor"]="absent unique seam"
    reject("missing_literal_seam",lambda:b.trace_sources(before,expected_fixture,wrong,payloads))
    wrong=copy.deepcopy(spec["rules"]);wrong[0]["position"]="replace"
    reject("numeric_replacement_not_authorized",lambda:b.trace_sources(before,expected_fixture,wrong,payloads))
    tcl=b"cd {/old/out}\ngds read {/old/wires.gds}\nextresist tolerance 0.000001\nextresist simplify off\nextresist all\n"
    changed,edits=b.relocate_tcl(tcl,"/old/out","/old/wires.gds",Path("/new/out"),Path("/new/wires.gds"))
    assert changed.count(b"/new")==2 and len(edits)==2;positive.append("actual_Tcl_reversible_path_seams")
    for name,raw in [("missing",tcl.replace(b"cd ",b"wrong ")),("gate",tcl.replace(b"0.000001",b"1")),("duplicate",tcl+b"cd {/old/out}\n")]:
        reject("Tcl:"+name,lambda raw=raw:b.relocate_tcl(raw,"/old/out","/old/wires.gds",Path("/new/out"),Path("/new/wires.gds")))
    assert len(c["source_producer"]["candidate"])==559 and actual["resis/ResMain.c"]=="6d1ce0d1bb3750e5863400fc3fcccdcdc9c442c435f35f482064dd1a44110cdb"
    assert sum(actual[n]!=expected_fixture[n]for n in actual)==3;positive.append("three_actual_baseline_mismatches_explicit")
    with tempfile.TemporaryDirectory(prefix="magic-build-source-fixtures-")as tmp:
        root=Path(tmp);dirs={}
        synthetic={"pump_wires.ext":b'cap "a" "b" 1\n',
          "pump_wires.res.ext":b'rnode "a" 0 0 1 2 0\nrnode "b" 0 0 3 4 0\nresist "a" "b" 10\n',
          "baseline.spice":b".subckt pump_wires a b\nX1 a b cap_cmim w=1 l=1\n.ends\n",
          "wires.spice":b".subckt pump_wires a b\nR1 a b 10\nC1 a b 1f\n.ends\n"}
        for name in ("baseline","off","on"):
            d=root/name;d.mkdir();dirs[name]=d
            for n,raw in synthetic.items():(d/n).write_bytes(raw)
        assert b.compare_outputs(dirs)["status"]=="EXACT_NATIVE_RECORD_EQUIVALENCE";positive.append("actual_output_comparator_synthetic_records")
        for label,file,raw in [
          ("R","pump_wires.res.ext",synthetic["pump_wires.res.ext"].replace(b"b\" 10",b"b\" 11")),
          ("rnode","pump_wires.res.ext",synthetic["pump_wires.res.ext"].replace(b"1 2 0",b"1 3 0")),
          ("cap","pump_wires.ext",b'cap "a" "b" 2\n'),
          ("spice","wires.spice",synthetic["wires.spice"].replace(b"1f",b"2f")),
          ("ordered","pump_wires.res.ext",b'\n'.join(reversed(synthetic["pump_wires.res.ext"].splitlines()))+b'\n')]:
            (dirs["on"]/file).write_bytes(raw)
            reject("numeric_equivalence:"+label,lambda:b.compare_outputs(dirs))
            (dirs["on"]/file).write_bytes(synthetic[file])
        rows=[dict(schema=1,event="trace_start",instrumentation="nssoc_resistor_provenance_v1",resistor_footprint_is_not_inferred=True)]
        def add(event,**kw):rows.append(dict(schema=1,event=event,seq=len(rows),epoch=1,**kw))
        add("net_begin",net_name_hex="61",physical_ownership_proved=False)
        fields=dict(rr_value_milliohms_hex="0x1p+0",rr_tt=7,type_index_valid=True)
        add("create_tile",final_footprint_proved=False,**fields);add("create_contact",final_footprint_proved=False,**fields)
        add("net_end");add("snapshot_begin",phase="after_simplify")
        add("snapshot_resistor",phase="after_simplify",index=0,**fields)
        add("snapshot_end",phase="after_simplify",count=1)
        add("emitted_resistor",final_footprint_proved=False,node1=dict(name_hex="61"),node2=dict(name_hex="62"),ext_value_token="10",**fields)
        rows.append(dict(schema=1,event="trace_end",records_before_footer=8,epochs=1,net_still_open=False,physical_ownership_proved=False))
        trace=root/"trace.jsonl"
        # Production JSONL is one object per line; fixtures use the same single-line representation.
        def put(r):trace.write_bytes(b"".join((json.dumps(x,separators=(",",":"))+"\n").encode()for x in r))
        put(rows);assert b.validate_trace(trace,1,[b'resist "a" "b" 10'])["records"]==8;positive.append("actual_trace_complete_footer_and_native_line_join")
        for name in ("footer","seq","nan","ownership","emitted_count","epoch"):
            bad=copy.deepcopy(rows);count=1
            if name=="footer":bad.pop()
            if name=="seq":bad[3]["seq"]=99
            if name=="nan":bad[2]["rr_value_milliohms_hex"]="nan"
            if name=="ownership":bad[2]["final_footprint_proved"]=True
            if name=="emitted_count":count=2
            if name=="epoch":bad[3]["epoch"]=2
            put(bad);reject("trace:"+name,lambda count=count:b.validate_trace(trace,count))
        for label,key,value in [("endpoint","node1",dict(name_hex="63")),("value","ext_value_token","11")]:
            bad=copy.deepcopy(rows);bad[-2][key]=value;put(bad)
            reject("trace_native_join:"+label,lambda:b.validate_trace(trace,1,[b'resist "a" "b" 10']))
        speca=dict(prefix="source/",members=2,full_members=3,part=dict(id=635949809,bytes=1,sha256="0"*64))
        records=[dict(path=n,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),mode=0o644)
          for n,raw in [("source/a.c",b"a"),("source/b.h",b"b"),("other/c.c",b"c")]]
        ma=dict(encoding="tar-gzip",parts=[dict(speca["part"],name="batch-000002.tar.gz",
          url="https://github.com/Melihakbulut221/nssoc/releases/download/cloud-migration-tools-20261013-000/batch-000002.tar.gz")],records=records)
        archive=root/"source.tar.gz"
        def archive_write(link=False):
            with tarfile.open(archive,"w:gz")as tar:
                for r in records:
                    info=tarfile.TarInfo(r["path"]);info.size=1
                    if link and r["path"]=="source/b.h":info.type=tarfile.SYMTYPE;info.linkname="../outside";info.size=0
                    tar.addfile(info,None if info.issym()else io.BytesIO(r["path"].split("/")[-1][:1].encode()))
        archive_write();pr=b.restore_source(archive,ma,root/"restored",speca)
        assert pr["full_count"]==3 and pr["selected_count"]==2;positive.append("actual_full_archive_selector_synthetic_only")
        archive_write(True);reject("archive_link",lambda:b.restore_source(archive,ma,root/"bad-restored",speca))
        wrong=copy.deepcopy(ma);wrong["records"]=wrong["records"][:-1]
        reject("archive_incomplete_manifest",lambda:b.restore_source(archive,wrong,root/"missing",speca))
        tag="cloud-results-"+ctx["token"]+"-"+b.GROUP
        reserved=dict(release_id=7,tested_source=ctx["source"],tag=tag,externally_reserved=True,assets_overwritten=False)
        release=dict(id=7,tag_name=tag,target_commitish=ctx["source"],prerelease=True,draft=False,assets=[])
        ref=dict(ref="refs/tags/"+tag,object=dict(type="commit",sha=ctx["source"]))
        def exercise(case,raw):
            out=root/("pub-"+case);out.mkdir()
            if raw is not None:(out/"result.json").write_bytes(raw)
            (out/"native.stderr").write_bytes(b"");(out/"retained-wave.synthetic").write_bytes(b"\x00\x01\x02")
            assets=[];calls=[]
            def api(path):
                if path.startswith("git/"):return ref
                return dict(release,assets=list(assets))
            def upload(path):
                calls.append(path.name)
                if case=="upload_failure":raise RuntimeError("primary transport fixture")
                identity=b.pin(path);assets.append(dict(id=len(assets)+1,name=path.name,size=identity["bytes"],digest="sha256:"+identity["sha256"]))
            if case=="no_clobber":assets.append(dict(id=99,name="existing",size=1,digest="sha256:"+"f"*64))
            try:
                result=b.publication(ctx,reserved,out,root/("parts-"+case),api,upload)
                assert case not in ("upload_failure","no_clobber")
                assert result["native_accepted"]is False and "native.stderr"not in calls
                part=next((root/("parts-"+case)).glob("*.part0000"))
                with tarfile.open(part,"r:gz")as tar:
                    assert tar.extractfile(out.name+"/native.stderr").read()==b""
                    if raw is not None:assert tar.extractfile(out.name+"/result.json").read()==raw
                life.append(case)
            except RuntimeError as exc:
                assert case=="upload_failure"and str(exc)=="primary transport fixture"and out.exists();life.append(case)
            except AssertionError:
                assert case=="no_clobber"and not calls;life.append(case)
        exercise("empty_terminal",b"")
        exercise("malformed_terminal",b"{ malformed original")
        exercise("missing_terminal",None)
        exercise("upload_failure",b'{"status":"FAIL"}')
        exercise("no_clobber",b'{"status":"FAIL"}')
        primary=RuntimeError("primary source corruption")
        def failed(*args):
            (args[-1]/"available.stderr").write_bytes(b"original partial")
            raise primary
        def badwrite(*args):raise OSError("secondary final write")
        with patch.object(b,"write",badwrite),patch.object(b,"preserve_current_source",lambda *args:None):
            try:b.run(ctx,reserved,b"",expected,root/"primary",failed)
            except RuntimeError as exc:assert exc is primary
            else:raise AssertionError("primary error was lost")
        assert (root/"primary/available.stderr").read_bytes()==b"original partial"
        # Kept within lifecycle count: the upload failure case also verifies primary-finalizer isolation.
    assert len(positive)==8 and len(refused)==30 and len(life)==5,(positive,refused,life)
    inherited=prior.controls()
    assert inherited["positive_count"]==4 and inherited["refusal_count"]==19
    return dict(status="PASS_MAGIC_CURRENT500_BUILD_SOURCE_CONTROLS",passed=True,
      counts=dict(positive=len(positive),refusal=len(refused),lifecycle=len(life)),positive=positive,refusals=refused,
      lifecycle=life,inherited_source_controls=inherited,native_executed=False,c_compilation_executed=False,
      synthetic_archives_only=True,physical_acceptance=False,current_context=dict(source=ctx["source"],
      run_id=ctx["run_id"],attempt=1,source_controls_only=True,native_executed=False))

def main():
    p=argparse.ArgumentParser();p.add_argument("--pins-sha256",required=True);p.add_argument("--output",type=Path,required=True);a=p.parse_args()
    primary=None
    try:r=controls(a.pins_sha256)
    except BaseException as exc:
        primary=exc;r=dict(status="FAIL_MAGIC_CURRENT500_BUILD_SOURCE_CONTROLS",error=repr(exc),
          traceback=traceback.format_exc(),native_executed=False,physical_acceptance=False)
    raw=b.encode(r);print(raw.decode(),end="",flush=True)
    try:b.write(a.output,raw)
    except BaseException:
        if primary is None:raise
    if primary is not None:raise primary
if __name__=="__main__":main()
