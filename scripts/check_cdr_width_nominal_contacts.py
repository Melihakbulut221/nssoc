#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted source controls; all archive/waveform fixtures here are synthetic."""
import argparse,ast,base64,contextlib,copy,hashlib,io,json,os,struct,tarfile,tempfile,traceback,zlib
from pathlib import Path
from unittest.mock import patch
import cloud_cdr_width_nominal_contacts as r
def named_source(raw,name):
    tree=ast.parse(raw);node=next(x for x in tree.body if isinstance(x,ast.FunctionDef)and x.name==name)
    return "".join(raw.splitlines(keepends=True)[node.lineno-1:node.end_lineno])+"\n"
def controls():
    c=r.source_guard();core,rows=r.load_numeric();np=r.np
    positives=[];refusals=[];lifecycle=[]
    def good(label,fn):
        value=fn();positives.append(label);return value
    def bad(label,fn,message=None):
        try:fn()
        except (AssertionError,ValueError,KeyError,IndexError,TypeError,FileExistsError,tarfile.TarError,UnicodeError)as exc:
            if message is not None:assert message in str(exc),(label,str(exc))
            refusals.append(dict(case=label,error=type(exc).__name__,message=str(exc)));return
        raise AssertionError("required refusal absent: "+label)
    def mutated(obj,fn):
        v=copy.deepcopy(obj);fn(v);return v
    def noop_net(*args,**kwargs):raise AssertionError("SOURCE CONTROL ATTEMPTED NETWORK")
    authentic={}
    for case in r.CASES:
        authentic[case]=good("authentic metadata "+case,lambda case=case:r.metadata(c,case))
        e=c["cases"][case]
        snapshots=[r.decode(r.regular(r.ROOT,p).read_bytes())for p in
          (c["run_path"],c["jobs_path"],e["release_path"],e["ref_path"])]
        good("authentic failed live "+case,lambda case=case,s=snapshots:r.validate_live(c,case,*s))
    run,jobs,release,ref=snapshots=[r.decode(r.regular(r.ROOT,p).read_bytes())for p in
      (c["run_path"],c["jobs_path"],c["cases"]["nominal_early"]["release_path"],c["cases"]["nominal_early"]["ref_path"])]
    e=c["cases"]["nominal_early"];case="nominal_early"
    env=dict(GITHUB_ACTIONS="true",GITHUB_EVENT_NAME="workflow_dispatch",GITHUB_REPOSITORY=r.REPOSITORY,
      GITHUB_REF="refs/heads/"+r.BRANCH,GITHUB_RUN_ATTEMPT="1",GITHUB_RUN_ID="123",GITHUB_SHA="a"*40)
    ctx=good("hosted context",lambda:r.context(env,case))
    for key,val in [("GITHUB_ACTIONS","false"),("GITHUB_EVENT_NAME","push"),("GITHUB_REPOSITORY","other/repo"),
      ("GITHUB_REF","refs/heads/main"),("GITHUB_RUN_ATTEMPT","2"),("GITHUB_RUN_ID","0"),("GITHUB_SHA","a"*39)]:
        bad("context "+key,lambda key=key,val=val:r.context(dict(env,**{key:val}),case))
    bad("wrong case",lambda:r.context(env,"hot_early"),"case")
    tag="cloud-results-123-1-"+ctx["group"]
    info=dict(id=991,tag_name=tag,target_commitish=ctx["source"],prerelease=True,draft=False,assets=[])
    freshref=dict(ref="refs/tags/"+tag,object=dict(type="commit",sha=ctx["source"]))
    reserved=dict(tag=tag,tested_source=ctx["source"],release_id=991,target_verified=True,
      assets_overwritten=False,externally_reserved=True,creation_attempted=False,existing_assets=[])
    good("fresh exact reservation",lambda:r.reservation(ctx,reserved,info,freshref))
    for key,value in [("tested_source","b"*40),("release_id",992),("target_verified",False),
      ("assets_overwritten",True),("externally_reserved",False),("creation_attempted",True),("existing_assets",["x"])]:
        bad("reservation "+key,lambda key=key,value=value:r.reservation(ctx,dict(reserved,**{key:value}),info,freshref))
    bad("occupied release",lambda:r.reservation(ctx,reserved,dict(info,assets=[dict(id=1,name="old")]),freshref))
    for key,value in [("head_sha","b"*40),("run_attempt",2),("id",1),("path","wrong"),("head_branch","main")]:
        bad("live "+key,lambda key=key,value=value:r.validate_live(c,case,dict(run,**{key:value}),jobs,release,ref))
    bad("live asset hash",lambda:r.validate_live(c,case,run,jobs,mutated(release,lambda x:x["assets"][0].update(digest="sha256:"+"0"*64)),ref))
    bad("live missing asset",lambda:r.validate_live(c,case,run,jobs,mutated(release,lambda x:x["assets"].pop()),ref))
    def alter_job(x,key,value):
        next(j for j in x["jobs"]if j["id"]==e["job_id"])[key]=value
    bad("relabel failed job success",lambda:r.validate_live(c,case,run,mutated(jobs,lambda x:alter_job(x,"conclusion","success")),release,ref))
    bad("changed preservation step",lambda:r.validate_live(c,case,run,
      mutated(jobs,lambda x:next(j for j in x["jobs"]if j["id"]==e["job_id"])["steps"][6].update(conclusion="failure")),release,ref))
    bad("tag source",lambda:r.validate_live(c,case,run,jobs,release,dict(ref,object=dict(type="commit",sha="b"*40))))
    with tempfile.TemporaryDirectory()as temp:
        root=Path(temp)/"source";root.mkdir()
        for p in [r.CONFIG,*c["required_files"]]:
            q=root/p;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(r.regular(r.ROOT,p).read_bytes())
        good("complete protected projection",lambda:r.source_guard(root))
        target=root/e["report_path"];original=target.read_bytes()
        target.write_bytes(original+b" ")
        bad("changed actual report bytes",lambda:r.source_guard(root),"source/input bytes")
        bad("metadata authenticates independently",lambda:r.metadata(c,case,root),"pinned input bytes")
        target.write_bytes(original)
        target.unlink();bad("missing original report",lambda:r.source_guard(root),"missing regular file")
        target.write_bytes(original)
        target.write_bytes(r.regular(r.ROOT,e["summary_path"]).read_bytes())
        bad("raw-summary substitution",lambda:r.metadata(c,case,root),"pinned input bytes")
        target.write_bytes(original)
        wrongcase=copy.deepcopy(c)
        wrongcase["cases"][case]["report_path"]=c["cases"]["nominal_late"]["report_path"]
        bad("cross-case raw report",lambda:r.metadata(wrongcase,case,root),"native report binding")
        wrongwave=copy.deepcopy(c);wrongwave["cases"][case]["wave"]["sha256"]="0"*64
        bad("wrong full-map wave identity",lambda:r.metadata(wrongwave,case,root),"selected member joins")
        contract=r.decode(r.regular(r.ROOT,c["composition"]["path"]).read_bytes())
        report=authentic[case][2]
        good("actual current500 topology",lambda:r.topology(c,report,contract,core))
        for label,change in [
          ("historical collector",lambda x:next(t for d in x["device_records"]if d["native_id"]==115 for t in d["terminals"]if t["terminal"]=="C").update(native_cluster=136,native_net="$708")),
          ("missing device",lambda x:x["device_records"].pop()),
          ("RC count drift",lambda x:x["counts"].update(R=24616)),
          ("selector size",lambda x:next(d for d in x["device_records"]if d["native_id"]==61)["parameters"].update(nx="1"))]:
            bad(label,lambda change=change:r.topology(c,report,mutated(contract,change),core))
        records,branches,selected,names=r.topology(c,report,contract,core)
        t=np.linspace(0,rows.STOP,109601)
        d={n:np.broadcast_to(0.,t.shape)for n in names}
        focus=[61,62,115,116,60]
        locations={61:7000,62:8000,115:9000,116:10000,60:11000}
        fake=copy.deepcopy(report)
        for ident in focus:
            vc=core.vector(fake["binding"],ident,"C");vb=core.vector(fake["binding"],ident,"B");ve=core.vector(fake["binding"],ident,"E")
            d[vc]=np.full(t.shape,.9);d[vb]=np.broadcast_to(.8,t.shape);d[ve]=np.broadcast_to(.2,t.shape)
            d[core.current_vector(records[ident])]=np.broadcast_to(.001,t.shape)
            if ident==60:d[vc][locations[ident]]=-1.38
            else:
                d[vc][100]=.3 # inactive lower VCE must not become active minimum
                d[vc][locations[ident]]=.55
                if ident==61:d[vc][7001]=.55
            check=fake["device_checks"][core.name(ident)]
            check.update(minimum_active_vce_v=(-1.38-.2 if ident==60 else .55-.2),
              maximum_alltime_abs_vce_v=(abs(-1.38-.2)if ident==60 else .9-.2),
              maximum_alltime_abs_vbe_v=.8-.2,
              maximum_alltime_abs_ic_per_emitter_a=.001/fake["devices"][core.name(ident)]["nx"])
        diag=good("actual observer synthetic signals",lambda:r.observations(c,t,d,fake,contract,core,rows))
        assert all(diag["targets"][str(i)]["first_native_row"]==locations[i]for i in focus)
        assert diag["targets"]["61"]["all_exact_tie_rows"]==[7000,7001]
        assert diag["targets"]["60"]["signed_VCE_at_first_witness_v"]<0
        assert all(diag[k]is False for k in r.READBACK_FLAGS)
        framepath=Path(temp)/"frames.jsonl"
        proof=good("actual compact frame writer",lambda:r.write_frames(framepath,t,d,diag))
        parsed=[r.decode(x)for x in framepath.read_bytes().splitlines()]
        assert [x["row"]for x in parsed]==proof["row_indices"]and len(parsed)==proof["rows"]
        for frame in parsed:
            vals=struct.unpack("<"+"d"*len(frame["values"]),bytes.fromhex(frame["float64_le_hex"]))
            assert list(vals)==frame["values"]and vals[0]==t[frame["row"]]
        bad("frame no overwrite",lambda:r.write_frames(framepath,t,d,diag))
        bad("conflicting scalar replay",lambda:r.observations(c,t,d,
          mutated(fake,lambda x:x["device_checks"]["xpd.xd0061"].update(minimum_active_vce_v=.1)),contract,core,rows))
        bad("missing contact",lambda:r.observations(c,t,{k:v for k,v in d.items()if k!=names[0]},fake,contract,core,rows))
        bad("duplicate/shifted time",lambda:r.observations(c,np.zeros_like(t),d,fake,contract,core,rows))
        bad("nonfinite contact",lambda:r.observations(c,t,dict(d,**{names[0]:np.full(t.shape,np.nan)}),fake,contract,core,rows))
        flipped=dict(d);v=core.vector(fake["binding"],61,"C");flipped[v]=-d[v]
        bad("voltage sign error",lambda:r.observations(c,t,flipped,fake,contract,core,rows))
        goodd=dict(d);goodd[v]=d[v].copy();goodd[v][7000:7002]=.75
        goodreport=copy.deepcopy(fake)
        goodreport["device_checks"]["xpd.xd0061"]["minimum_active_vce_v"]=.75-.2
        no_violation=good("no invented violation interval",lambda:r.observations(c,t,goodd,goodreport,contract,core,rows))
        assert no_violation["targets"]["61"]["all_violation_intervals"]==[]
        # Strict actual raw-parser body on tiny synthetic binary files, no real wave acquired.
        vectors=["v(a)","@q.x[ic]"]
        header=("Title: synthetic fixture\nPlotname: Transient Analysis\nFlags: real\nNo. Variables: 3\nNo. Points: 3\nVariables:\n0 time time\n1 v(a) voltage\n2 i(@q.x[ic]) current\nBinary:\n").encode()
        array=np.array([[0,1,.001],[1e-9,2,.002],[2e-9,3,.003]],dtype="<f8")
        raw=header+array.tobytes();wave=Path(temp)/"toy.raw";wave.write_bytes(raw)
        tt,dd,cap=good("exact original binary parser synthetic",lambda:r.read_streamed_wave(wave,vectors,2e-9,1e-9))
        assert list(tt)==[0,1e-9,2e-9]and list(dd["@q.x[ic]"])==[.001,.002,.003]and cap["header_rows"]==3
        def raw_refusal(label,data):
            wave.write_bytes(data);bad(label,lambda:r.read_streamed_wave(wave,vectors,2e-9,1e-9))
        raw_refusal("raw truncated",raw[:-1]);raw_refusal("raw extra",raw+b"x")
        raw_refusal("raw duplicate field",raw.replace(b"Flags: real\n",b"Flags: real\nFlags: real\n"))
        raw_refusal("raw duplicate vector",raw.replace(b"2 i(@q.x[ic]) current",b"2 v(a) voltage"))
        raw_refusal("raw wrong kind",raw.replace(b"v(a) voltage",b"v(a) current"))
        broken=array.copy();broken[1,1]=np.nan;raw_refusal("raw nonfinite",header+broken.tobytes())
        broken=array.copy();broken[1,0]=0;raw_refusal("raw repeated time",header+broken.tobytes())
        raw_refusal("raw missing binary",raw.replace(b"Binary:\n",b"Absent:\n"))
        # Tar bodies and all fake cloud transport below are explicitly synthetic.
        archive=Path(temp)/"toy.tar.gz";archive_root="toy"
        def tar_bytes(entries):
            buf=io.BytesIO()
            with tarfile.open(fileobj=buf,mode="w:gz")as tf:
                for name,data,kind in entries:
                    ti=tarfile.TarInfo(name);ti.type=kind
                    if kind==tarfile.REGTYPE:ti.size=len(data);tf.addfile(ti,io.BytesIO(data))
                    else:
                        if kind==tarfile.SYMTYPE:ti.linkname="/tmp/forbidden"
                        tf.addfile(ti)
            return buf.getvalue()
        expected={"wave.raw":hashlib.sha256(b"synthetic").hexdigest(),"empty.stderr":hashlib.sha256(b"").hexdigest()}
        entries=[("toy",b"",tarfile.DIRTYPE),("toy/wave.raw",b"synthetic",tarfile.REGTYPE),("toy/empty.stderr",b"",tarfile.REGTYPE)]
        archive.write_bytes(tar_bytes(entries));targetdir=Path(temp)/"selected"
        census=good("full synthetic archive including empty",lambda:r.select_archive(archive,expected,["wave.raw"],archive_root,targetdir))
        assert census["full_member_count"]==2 and census["full_members"]["empty.stderr"]["bytes"]==0
        tar_cases=[
          ("tar traversal",entries+[("toy/../escape",b"x",tarfile.REGTYPE)]),
          ("tar duplicate",entries+[entries[1]]),("tar link",[entries[0],("toy/wave.raw",b"",tarfile.SYMTYPE),entries[2]]),
          ("tar unexpected",entries+[("toy/extra",b"x",tarfile.REGTYPE)]),
          ("tar missing",entries[:-1]),("tar changed bytes",[entries[0],("toy/wave.raw",b"wrong",tarfile.REGTYPE),entries[2]]),
          ("tar wrong root",[("other/wave.raw",b"synthetic",tarfile.REGTYPE)]),
          ("tar special",[entries[0],("toy/wave.raw",b"",tarfile.FIFOTYPE),entries[2]]),
          ("tar extra directory",entries+[("toy/unknown",b"",tarfile.DIRTYPE)])]
        for index,(label,ent)in enumerate(tar_cases):
            archive.write_bytes(tar_bytes(ent))
            bad(label,lambda index=index:r.select_archive(archive,expected,["wave.raw"],archive_root,Path(temp)/("bad"+str(index))))
        bad("selected nonexistent",lambda:r.select_archive(archive,expected,["not-present"],archive_root,Path(temp)/"badselected"))
        # actual acquire verifies each part and combined bytes, with a fake downloader.
        payload=b"synthetic gzip transport"
        pp=dict(parts=[dict(index=0,name="p0",bytes=len(payload),sha256=hashlib.sha256(payload).hexdigest())],
          bytes=len(payload),sha256=hashlib.sha256(payload).hexdigest())
        cc={"cases":{"nominal_early":{"assets":{"p0":dict(pp["parts"][0],id=1)}}}}
        acq=Path(temp)/"acq";acq.mkdir()
        def fake_fetch(pin,path):path.write_bytes(payload)
        ap,aproof=good("actual synthetic part acquisition",lambda:r.acquire(cc,case,pp,acq,fake_fetch))
        assert ap.read_bytes()==payload
        wrong=Path(temp)/"acqbad";wrong.mkdir()
        bad("combined hash refusal",lambda:r.acquire(cc,case,dict(pp,sha256="0"*64),wrong,fake_fetch))
        wrong2=Path(temp)/"acqbad2";wrong2.mkdir()
        bad("part hash refusal",lambda:r.acquire(cc,case,pp,wrong2,lambda pin,path:path.write_bytes(b"bad")))
        # Full output chunks reconstruct exact bytes, including empty files.
        emitted=Path(temp)/"emit";emitted.mkdir()
        (emitted/"x.json").write_bytes(b'{"a":1}\n');(emitted/"empty").write_bytes(b"")
        lines=[];good("complete output emitter",lambda:r.emit(emitted,writer=lambda x,**kw:lines.append(x)))
        index=r.decode(lines[0].split(" ",1)[1]);chunks={n:[]for n in index}
        for line in lines[1:]:
            prefix,body=line.split(" ",1);obj=r.decode(body)
            if prefix=="CDR_CONTACT_CHUNK":
                assert obj["index"]==len(chunks[obj["name"]]);chunks[obj["name"]].append(base64.b64decode(obj["data"]))
        for n,pin in index.items():assert r.fingerprint(zlib.decompress(b"".join(chunks[n])))==pin
        # Source corruption must fail before network, retain exact failure, and no acceptance.
        badtarget=root/"scripts/cdr_v59_headroom_rows.py";saved=badtarget.read_bytes();badtarget.write_bytes(saved+b"# tamper\n")
        log=io.StringIO();out=Path(temp)/"source-failure"
        with contextlib.redirect_stdout(log):
            try:r.run(ctx,reserved,b"{}",out,root,noop_net,noop_net)
            except AssertionError as exc:assert "source/input bytes"in str(exc)
            else:raise AssertionError("source corruption accepted")
        assert r.decode((out/"readback-failure.json").read_bytes())["accepted"]is False
        assert "CDR_CONTACT_END "in log.getvalue();lifecycle.append("actual run source failure before acquisition")
        badtarget.write_bytes(saved)
        control=r.encode(dict(status="PASS_CURRENT_WIDTH_CONTACT_SOURCE_CONTROLS",passed=True,
          current_context=dict(source=ctx["source"],run_id=ctx["run_id"],attempt=1,source_controls_only=True,native_executed=False),
          native_executed=False,physical_acceptance=False,counts=r.SOURCE_COUNTS))
        bad("current controls context",lambda:r.controls_binding(control,dict(ctx,source="b"*40)))
        bad("current controls failure",lambda:r.controls_binding(r.encode(dict(r.decode(control),passed=False)),ctx))
        bad("current controls incomplete counts",lambda:r.controls_binding(r.encode(dict(r.decode(control),counts={})),ctx))
        def fake_api(endpoint):
            if endpoint=="releases/tags/"+tag:return info
            if endpoint=="git/ref/tags/"+tag:return freshref
            if endpoint.startswith("actions/runs/")and "/jobs"in endpoint:return jobs
            if endpoint.startswith("actions/runs/"):return run
            if endpoint=="releases/"+str(e["release_id"]):return release
            if endpoint=="git/ref/tags/"+e["tag"]:return ref
            raise AssertionError("unexpected API")
        def transport_failure(pin,path):raise RuntimeError("PRIMARY_SYNTHETIC_TRANSPORT")
        for extra_failure in (False,True):
            out=Path(temp)/("transport-failure-"+str(extra_failure))
            real_temp=tempfile.TemporaryDirectory
            class BadCleanup:
                def __init__(self,*a,**kw):self.inner=real_temp(*a,**kw);self.name=self.inner.name
                def cleanup(self):self.inner.cleanup();raise OSError("SECONDARY_SYNTHETIC_CLEANUP")
            with patch.object(r.tempfile,"TemporaryDirectory",BadCleanup if extra_failure else real_temp),contextlib.redirect_stdout(io.StringIO()):
                try:r.run(ctx,reserved,control,out,root,fake_api,transport_failure)
                except RuntimeError as exc:assert str(exc)=="PRIMARY_SYNTHETIC_TRANSPORT"
                else:raise AssertionError("transport failure replaced")
            assert (out/"reservation.json").exists()and (out/"readback-failure.json").exists()
            if extra_failure:assert (out/"cleanup-error.json").exists()
            lifecycle.append("actual run transport failure"+(" plus cleanup"if extra_failure else""))
        # Failure-save and emission exceptions cannot replace a source primary exception.
        out=Path(temp)/"save-emit-failure"
        with patch.object(r,"source_guard",side_effect=RuntimeError("PRIMARY_SOURCE")),patch.object(r,"write_new",side_effect=OSError("SAVE")),patch.object(r,"emit",side_effect=OSError("EMIT")),contextlib.redirect_stdout(io.StringIO()):
            try:r.run(ctx,reserved,control,out,root,noop_net,noop_net)
            except RuntimeError as exc:assert str(exc)=="PRIMARY_SOURCE"
            else:raise AssertionError("primary lost")
        lifecycle.append("actual run primary survives save and emission failures")
        existing=Path(temp)/"exists";existing.mkdir()
        bad("actual run no overwrite",lambda:r.run(ctx,reserved,control,existing,root,noop_net,noop_net))
        lifecycle.append("actual run refuses preexisting output")
    original=r.regular(r.ROOT,"scripts/cloud_tx_stream.py").read_text()
    current=Path(r.__file__).read_text()
    assert named_source(original,"read_streamed_wave")==named_source(current,"read_streamed_wave")
    positives.append("exact original raw parser body")
    assert dict(positive=len(positives),refusal=len(refusals),lifecycle=len(lifecycle))==r.SOURCE_COUNTS
    return dict(status="PASS_CURRENT_WIDTH_CONTACT_SOURCE_CONTROLS",passed=True,
      positive_cases=positives,refusals=refusals,lifecycle_cases=lifecycle,
      counts=dict(positive=len(positives),refusal=len(refusals),lifecycle=len(lifecycle)),
      authentic_cases=list(r.CASES),synthetic_archive_and_waveforms_only=True,
      actual_source_guard_metadata_parser_observer_writer_acquire_and_finalizer_called=True,
      native_executed=False,physical_acceptance=False,all_real_native_archives_acquired=False)
def main():
    p=argparse.ArgumentParser();p.add_argument("--output",type=Path,required=True);args=p.parse_args()
    ctx=r.context(os.environ);primary=None;result=None
    try:
        result=controls();result["current_context"]=dict(ctx,source_controls_only=True,native_executed=False)
    except BaseException as exc:
        primary=exc
        result=dict(status="FAIL_CURRENT_WIDTH_CONTACT_SOURCE_CONTROLS",passed=False,error=repr(exc),
          traceback=traceback.format_exc(),current_context=dict(ctx,source_controls_only=True,native_executed=False),
          native_executed=False,physical_acceptance=False)
        raise
    finally:
        raw=r.encode(result)
        try:r.write_new(args.output,raw)
        except BaseException:
            try:print("UNSAVED_CONTACT_CONTROL_REPORT "+raw.decode(),flush=True)
            except BaseException:pass
            if primary is None:raise
        try:print(raw.decode(),flush=True)
        except BaseException:
            if primary is None:raise
if __name__=="__main__":main()
