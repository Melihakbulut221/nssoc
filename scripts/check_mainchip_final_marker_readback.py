#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted source controls. Every tar/transport fixture is synthetic, never native proof."""
import argparse
import base64
import copy
import io
import json
import os
from pathlib import Path
import tarfile
import tempfile
from unittest.mock import patch
import zlib
import cloud_mainchip_final_marker_readback as m

AUTHENTIC_JSON_FIXTURE = "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"

def tar_bytes(rows):
    output=io.BytesIO()
    with tarfile.open(fileobj=output,mode="w:gz")as tar:
        for name,raw,kind in rows:
            item=tarfile.TarInfo(name);item.mtime=0
            if kind=="file":
                item.size=len(raw);tar.addfile(item,io.BytesIO(raw))
            elif kind=="link":
                item.type=tarfile.SYMTYPE;item.linkname="../outside";tar.addfile(item)
            elif kind=="hard":
                item.type=tarfile.LNKTYPE;item.linkname="marker.json";tar.addfile(item)
            elif kind=="dir":
                item.type=tarfile.DIRTYPE;tar.addfile(item)
            else:
                item.type=tarfile.FIFOTYPE;tar.addfile(item)
    return output.getvalue()

def controls():
    positive=[];rejected=[];lifecycle=[]
    def reject(name,fn,fragment):
        try:fn()
        except (AssertionError,ValueError,KeyError,UnicodeError,tarfile.TarError,EOFError)as exc:
            assert fragment in str(exc),(name,type(exc).__name__,str(exc),fragment)
            rejected.append(dict(name=name,reason=str(exc)))
        else:raise AssertionError("accepted "+name)
    original=json.loads(zlib.decompress(base64.b64decode(AUTHENTIC_JSON_FIXTURE)))
    outputs=base64.b64decode(original["outputs_b64"]);parts=base64.b64decode(original["parts_b64"])
    files,manifest=m.metadata(outputs,parts)
    assert len(files)==145 and sum(x["bytes"]for x in files.values())==5763445029
    assert m.validate_live(**original["live"])["producer_workflow_success"]
    positive.append("authentic-full-JSON-and-seven-job-projection-no-archive")
    for label,key in (("outputs-byte-tamper","outputs"),("parts-byte-tamper","parts")):
        reject(label,lambda key=key:m.metadata(outputs+b" "if key=="outputs"else outputs,
          parts+b" "if key=="parts"else parts),key+" bytes")
    for label,change,reason in [
      ("wrong-source",lambda x:x["run"].__setitem__("head_sha","0"*40),"producer run"),
      ("wrong-run",lambda x:x["run"].__setitem__("id",1),"producer run"),
      ("failed-run",lambda x:x["run"].__setitem__("conclusion","failure"),"producer terminal"),
      ("missing-job",lambda x:x["jobs"]["jobs"].pop(),"complete producer jobs"),
      ("failed-audit",lambda x:x["jobs"]["jobs"][-2].__setitem__("conclusion","failure"),"producer job"),
      ("wrong-tag",lambda x:x["ref"]["object"].__setitem__("sha","0"*40),"tag object"),
      ("asset-digest",lambda x:next(a for a in x["release"]["assets"]if a["id"]==689123081).__setitem__("digest","sha256:"+"0"*64),"producer asset"),
      ("duplicate-asset",lambda x:x["release"]["assets"].append(copy.deepcopy(x["release"]["assets"][0])),"duplicate release asset")]:
        v=copy.deepcopy(original["live"]);change(v)
        reject(label,lambda v=v:m.validate_live(**v),reason)
    env=dict(GITHUB_ACTIONS="true",GITHUB_EVENT_NAME="workflow_dispatch",GITHUB_REPOSITORY=m.REPOSITORY,
      GITHUB_REF="refs/heads/"+m.BRANCH,GITHUB_RUN_ATTEMPT="1",GITHUB_RUN_ID="123",GITHUB_SHA="a"*40)
    ctx=m.context(env)
    tag="cloud-results-123-1-"+m.GROUP
    info=dict(id=9,tag_name=tag,target_commitish=ctx["source"],draft=False,prerelease=True,assets=[])
    ref=dict(ref="refs/tags/"+tag,object=dict(type="commit",sha=ctx["source"]))
    proof=dict(tag=tag,tested_source=ctx["source"],release_id=9,existing_assets=[],
      target_verified=True,assets_overwritten=False,externally_reserved=True,creation_attempted=False)
    assert m.reservation(ctx,proof,info,ref)["verified_before_acquisition"]
    positive.append("typed-current-context-and-fresh-reservation")
    for key,value,reason in [
      ("GITHUB_ACTIONS","false","hosted"),("GITHUB_EVENT_NAME","push","manual"),
      ("GITHUB_REF","refs/heads/main","branch"),("GITHUB_RUN_ATTEMPT","2","attempt")]:
        e=dict(env);e[key]=value;reject("context-"+key,lambda e=e:m.context(e),reason)
    for label,change,reason in [
      ("reservation-source",lambda p:p.__setitem__("tested_source","b"*40),"reservation identity"),
      ("reservation-not-external",lambda p:p.__setitem__("externally_reserved",False),"externally reserved"),
      ("reservation-clobber",lambda p:p.__setitem__("assets_overwritten",True),"reservation verification")]:
        p=copy.deepcopy(proof);change(p);reject(label,lambda p=p:m.reservation(ctx,p,info,ref),reason)
    dirty=copy.deepcopy(info);dirty["assets"]=[dict(id=1,name="partial.json")]
    reject("nonempty-reservation",lambda:m.reservation(ctx,proof,dirty,ref),"fresh reservation")
    for name in ("../bad","/bad","a/../bad","a//bad","a/./bad","a\\bad"):
        reject("unsafe-path-"+name,lambda name=name:m.checked_path(name),"archive path")
    reject("duplicate-JSON",lambda:m.decode(b'{"x":1,"x":2}'),"duplicate JSON")
    with tempfile.TemporaryDirectory()as td:
        root=Path(td)
        rows=[("marker.json",b'{"marker":1}\n',"file"),("empty.stderr",b"","file"),
              ("native.odb",b"SYNTHETIC-NOT-A-NATIVE-DATABASE","file")]
        expected={n:m.digest(raw)for n,raw,k in rows};selected={"marker.json":expected["marker.json"],"empty.stderr":expected["empty.stderr"]}
        def run_tar(label,newrows=rows,newmap=None,newselected=None):
            archive=root/(label+".tar.gz");archive.write_bytes(tar_bytes(newrows))
            return m.select_archive(archive,expected if newmap is None else newmap,
              selected if newselected is None else newselected,root/(label+"-selected"))
        receipt=run_tar("valid")
        assert receipt["full_members"]==expected and receipt["native_members_extracted"]is False
        assert (root/"valid-selected/empty.stderr").read_bytes()==b""
        assert not (root/"valid-selected/native.odb").exists()
        positive.append("actual-streaming-selector-complete-hashes-zero-text-native-not-extracted")
        for label,newrows,reason in [
          ("traversal",[("../escape",b"x","file")],"archive path"),
          ("absolute",[("/escape",b"x","file")],"archive path"),
          ("symlink",[("marker.json",b"","link")],"link/special"),
          ("hardlink",[("marker.json",b"","hard")],"link/special"),
          ("fifo",[("marker.json",b"","fifo")],"link/special"),
          ("duplicate",rows+[rows[0]],"duplicate archive"),
          ("unexpected",rows+[("extra",b"x","file")],"unexpected archive"),
          ("unexpected-dir",rows+[("extra",b"","dir")],"unexpected archive directory"),
          ("missing",rows[:-1],"missing archive"),
          ("tamper",[("marker.json",b'{"marker":2}\n',"file")]+rows[1:],"member fingerprint")]:
            reject(label,lambda label=label,newrows=newrows:run_tar(label,newrows),reason)
        nul=[("marker.json",b"\x00","file")]
        reject("text-NUL",lambda:run_tar("nul",nul,{"marker.json":m.digest(b"\x00")},{"marker.json":{}}),"text NUL")
        bad=[("marker.json",b"\xff","file")]
        reject("text-UTF8",lambda:run_tar("utf8",bad,{"marker.json":m.digest(b"\xff")},{"marker.json":{}}),"utf-8")
        # Complete production acquisition path with explicit synthetic cloud transport
        # and a tiny synthetic tar; actual metadata validator/select_archive are used.
        synthetic_outputs=dict(mode="on",stage="audit",source=m.PRODUCER_SOURCE,
          physical_acceptance=False,files=expected)
        output_raw=m.encode(synthetic_outputs)
        tar_rows=rows+[("outputs.json",output_raw,"file")]
        archive_raw=tar_bytes(tar_rows);half=len(archive_raw)//2
        chunks=[archive_raw[:half],archive_raw[half:]]
        synthetic_assets=copy.deepcopy(m.ASSETS)
        synthetic_assets["outputs.json"].update(m.digest(output_raw))
        part_rows=[]
        for i,raw in enumerate(chunks):
            name="route-tail-evidence.tar.gz.part%03d"%i
            synthetic_assets[name].update(m.digest(raw));part_rows.append(dict(name=name,**m.digest(raw)))
        manifest=dict(archive=m.digest(archive_raw),parts=part_rows);part_raw=m.encode(manifest)
        synthetic_assets["parts.json"].update(m.digest(part_raw))
        payloads={"outputs.json":output_raw,"parts.json":part_raw,**{p["name"]:b for p,b in zip(part_rows,chunks)}}
        live=copy.deepcopy(original["live"])
        for asset in live["release"]["assets"]:
            if asset["name"]in synthetic_assets:
                pin=synthetic_assets[asset["name"]];asset.update(size=pin["bytes"],digest="sha256:"+pin["sha256"])
        calls=[]
        def read(path):
            calls.append(("api",path))
            if path=="releases/9":return copy.deepcopy(info)
            if path=="git/ref/tags/"+tag:return copy.deepcopy(ref)
            if path=="actions/runs/"+str(m.PRODUCER_RUN):return copy.deepcopy(live["run"])
            if "/attempts/"in path:return copy.deepcopy(live["jobs"])
            if path=="releases/"+str(m.PRODUCER_RELEASE):return copy.deepcopy(live["release"])
            if path=="git/ref/tags/"+m.PRODUCER_TAG:return copy.deepcopy(live["ref"])
            raise AssertionError("unexpected API "+path)
        def fetch(pin,path):
            calls.append(("fetch",pin["name"]));m.write_new(path,payloads[pin["name"]])
            assert m.file_digest(path)=={k:pin[k]for k in ("bytes","sha256")}
        with patch.dict(os.environ,{"RUNNER_TEMP":str(root)}),patch.multiple(m,
          ASSETS=synthetic_assets,SELECTED=selected,ARCHIVE=m.digest(archive_raw),
          MEMBER_COUNT=4,MEMBER_BYTES=sum(x["bytes"]for x in expected.values())+len(output_raw)):
            out=root/"perform";out.mkdir()
            result=m.perform(ctx,proof,out,read,fetch)
            assert result["full_archive_verified"] and (out/"readback-result.json").is_file()
            assert calls[:2]==[("api","releases/9"),("api","git/ref/tags/"+tag)]
            assert [v for k,v in calls if k=="fetch"]==list(payloads)
            assert not list(root.glob("mainchip-final-marker-*"))
            lifecycle.append("actual-perform-reservation-before-four-downloads-complete-cleanup")
            m.write_new(out/"multi-chunk.txt",b"x"*(2*m.CHUNK_BYTES+3))
            lines=[];index=m.emit(out,lambda text,**kwargs:lines.append(text))
            chunks_by={}
            for line in lines:
                if line.startswith("FINAL_MARKER_READBACK_CHUNK "):
                    row=json.loads(line.split(" ",1)[1]);chunks_by.setdefault(row["name"],[]).append(row)
            for name,pin in index.items():
                records=chunks_by[name];assert [r["index"]for r in records]==list(range(len(records)))
                raw=b"".join(base64.b64decode(r["base64"])for r in records)
                assert m.digest(raw)==pin
            assert chunks_by["selected/empty.stderr"][0]["base64"]==""
            positive.append("actual-full-chunk-roundtrip-including-empty-stream")
            calls.clear();out=root/"denied";out.mkdir();p=dict(proof,tested_source="b"*40)
            reject("acquisition-blocked-before-fetch",lambda:m.perform(ctx,p,out,read,fetch),"reservation identity")
            assert not [x for x in calls if x[0]=="fetch"]
            lifecycle.append("reservation-refusal-no-download")
            error=RuntimeError("synthetic transport primary")
            def failed_fetch(pin,path):
                m.write_new(path,b"partial")
                raise error
            real_temp=tempfile.TemporaryDirectory
            class CleanupFault:
                def __init__(self,*a,**kw):self.inner=real_temp(*a,**kw);self.name=self.inner.name
                def cleanup(self):
                    self.inner.cleanup()
                    raise RuntimeError("synthetic cleanup secondary")
            out=root/"failed";out.mkdir()
            with patch.object(m.tempfile,"TemporaryDirectory",CleanupFault):
                try:m.perform(ctx,proof,out,read,failed_fetch)
                except RuntimeError as actual:assert actual is error
                else:raise AssertionError("lost transport failure")
            assert (out/"cleanup-error.json").is_file() and not (out/"readback-result.json").exists()
            lifecycle.append("actual-transport-primary-survives-cleanup-failure")
            out=root/"cleanup-only";out.mkdir()
            with patch.object(m.tempfile,"TemporaryDirectory",CleanupFault):
                try:m.perform(ctx,proof,out,read,fetch)
                except RuntimeError as actual:assert str(actual)=="synthetic cleanup secondary"
                else:raise AssertionError("cleanup failure passed")
            assert (out/"extraction-receipt.json").is_file() and not (out/"readback-result.json").exists()
            lifecycle.append("cleanup-only-failure-retains-complete-selection-no-terminal-PASS")
            # Actual CLI failure envelope and emitter failure cannot replace transport primary.
            reservation_file=root/"reservation.json";reservation_file.write_bytes(m.encode(proof))
            real_perform=m.perform
            def cli_perform(c,p,o):return real_perform(c,p,o,read,failed_fetch)
            def denied_emit(*a,**kw):raise RuntimeError("synthetic emitter secondary")
            def git_only(argv,**kw):
                assert argv==["git","rev-parse","HEAD"]
                return ctx["source"]+"\n"
            out=root/"main-failure"
            with patch.dict(os.environ,env),patch.object(m,"perform",cli_perform),patch.object(m,"emit",denied_emit),                  patch.object(m.subprocess,"check_output",git_only),                  patch.object(m.sys,"argv",["reader","--output",str(out),"--reservation",str(reservation_file)]):
                try:m.main()
                except RuntimeError as actual:assert actual is error
                else:raise AssertionError("CLI lost primary")
            failure=json.loads((out/"readback-failure.json").read_text())
            assert failure["status"]=="FAIL_FINAL_MARKER_TEXT_READBACK"
            assert failure["error"]["message"]=="synthetic transport primary"
            assert not (out/"readback-result.json").exists()
            lifecycle.append("actual-CLI-failure-envelope-preserves-transport-primary-over-emitter")
        # Actual part combiner, including incomplete/changed archive refusals.
        paths=[]
        for i,raw in enumerate(chunks):
            p=root/("part"+str(i));p.write_bytes(raw);paths.append(p)
        m.combine_parts(paths,manifest,root/"combined.gz")
        positive.append("actual-combine-all-parts-and-archive-hash")
        broken=copy.deepcopy(manifest);broken["parts"][0]["sha256"]="0"*64
        reject("part-hash",lambda:m.combine_parts(paths,broken,root/"badpart.gz"),"part fingerprint")
        broken=copy.deepcopy(manifest);broken["archive"]["sha256"]="0"*64
        reject("archive-hash",lambda:m.combine_parts(paths,broken,root/"badarchive.gz"),"archive fingerprint")
        reject("part-no-clobber",lambda:m.combine_parts(paths,manifest,root/"combined.gz"),"no overwrite")
    return dict(status="PASS_FINAL_MARKER_READBACK_SOURCE_CONTROLS",positive_cases=positive,
      refusal_cases=rejected,lifecycle_cases=lifecycle,positive_count=len(positive),
      refusal_count=len(rejected),lifecycle_count=len(lifecycle),
      authentic_producer_json_projection=True,all_archives_and_transport_synthetic=True,
      native_archive_acquired=False,native_executed=False,physical_acceptance=False)

def main():
    parser=argparse.ArgumentParser();parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args();ctx=m.context(os.environ)
    report=controls();report["current_context"]=dict(ctx,source_controls_only=True)
    m.write_new(args.output,m.encode(report))
    print(json.dumps(report,sort_keys=True),flush=True)

if __name__=="__main__":
    main()
