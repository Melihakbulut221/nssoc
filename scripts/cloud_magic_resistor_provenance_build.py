#!/usr/bin/env python3
"""Runner-only full Magic rebuild and current500 trace equivalence; no PHY acceptance."""
import argparse,collections,contextlib,hashlib,json,math,os,re,shutil,signal,subprocess,sys,tarfile,threading,time,traceback
from pathlib import Path,PurePosixPath
import cloud_cdr_current_rc_contacts as frozen
import cdr_v59_tail_access_runtime as runtime
import cloud_cdr_current_access_overlay as lifecycle
import cloud_chunked_results as packing
import patch_magic_resistor_provenance as historical
ROOT=Path(__file__).resolve().parents[1]
BRANCH="codex/cdr-resistor-provenance-build"
GROUP="cdr-resistor-provenance-build"
CONFIG="scripts/cdr-resistor-provenance-build-inputs.json"
PINS="scripts/cdr-resistor-provenance-build-pins.json"
FLAGS=dict(geometry_changed=False,electrical_acceptance=False,physical_acceptance=False,
 full_phy_accepted=False,reduced_element_ownership_proved=False)
require=frozen.require
encode=frozen.encode
decode=frozen.decode
pin=frozen.file_pin
write=frozen.write_new

def source_guard(expected,root=ROOT):
    raw=frozen.regular(root,PINS).read_bytes()
    require(hashlib.sha256(raw).hexdigest()==expected,"build source manifest")
    m=decode(raw)
    require(m["schema"]=="magic-current500-build-pins-v1" and m["native_build_authorized"]is True
      and m["source_controls_authorized"]is True and m["scope"]==FLAGS,"build method scope")
    for name,value in m["files"].items():
        require(pin(frozen.regular(root,name))==value,"protected source: "+name)
    c=decode(frozen.regular(root,CONFIG).read_bytes())
    require(c["schema"]=="magic-current500-provenance-build-v1" and c["branch"]==BRANCH and
      c["group"]==GROUP and c["all_acceptance_false"]is True and c["physical_ownership_proved"]is False,"input identity")
    require(c["runtime"]==dict(seconds_per_command=1200,min_available_kib=2097152,max_group_rss_kib=10485760,
      extraction_address_space_bytes=4294967296,extraction_directory_bytes=1073741824),"unchanged extraction limits")
    require(len(c["source_producer"]["candidate"])==559 and c["source_producer"]["run"]==39486998309,"qualified producer")
    historical.source_guard(root)
    old=frozen.source_guard(root);data=frozen.metadata(old,root)
    require(c["current_rc"]==dict(run=40830441311,full_members=6647,devices=500,R=24356,C=15566,
      prefix="mim/precise/",library="1a44bd5c70af3800213419c2e3b2213285523a74fcc4b92bc9cf7314d93a592c"),"actual current capture")
    return c,old,data

def context(env):
    require(env.get("GITHUB_ACTIONS")=="true" and env.get("GITHUB_REPOSITORY")==frozen.REPOSITORY,"hosted repository")
    require(env.get("GITHUB_EVENT_NAME")=="workflow_dispatch" and env.get("GITHUB_RUN_ATTEMPT")=="1","manual first attempt")
    require(env.get("GITHUB_REF")=="refs/heads/"+BRANCH,"build branch")
    require(re.fullmatch("[0-9a-f]{40}",env.get("GITHUB_SHA","")) is not None,"exact source")
    require(re.fullmatch("[1-9][0-9]*",env.get("GITHUB_RUN_ID","")) is not None,"run identity")
    return dict(source=env["GITHUB_SHA"],run_id=int(env["GITHUB_RUN_ID"]),attempt=1,
      token=env["GITHUB_RUN_ID"]+"-1",group=GROUP)

def controls_binding(raw,ctx):
    r=decode(raw)
    require(r.get("status")=="PASS_MAGIC_CURRENT500_BUILD_SOURCE_CONTROLS" and r.get("passed")is True,"build controls")
    require(r.get("native_executed")is False and r.get("physical_acceptance")is False,"source-only controls")
    require(r.get("current_context")==dict(source=ctx["source"],run_id=ctx["run_id"],attempt=1,
      source_controls_only=True,native_executed=False),"same source controls")
    require(r["inherited_source_controls"]["positive_count"]==4 and r["inherited_source_controls"]["refusal_count"]==19,"historical controls preserved")
    require(r["counts"]==dict(positive=8,refusal=30,lifecycle=5),"complete build controls")
    return frozen.fingerprint(raw)

def preflight(ctx,reserved,controls_raw,expected,root=ROOT,api_call=frozen.api):
    c,old,data=source_guard(expected,root)
    controls=controls_binding(controls_raw,ctx)
    tag="cloud-results-"+ctx["token"]+"-"+GROUP
    receipt=frozen.reservation(ctx,reserved,api_call("releases/tags/"+tag),api_call("git/ref/tags/"+tag))
    run=api_call("actions/runs/"+str(old["producer"]["id"]))
    jobs=api_call("actions/runs/"+str(old["producer"]["id"])+"/attempts/1/jobs?per_page=100")
    release=api_call("releases/"+str(old["release_id"]));ref=api_call("git/ref/tags/"+old["tag"])
    live=frozen.validate_live(old,run,jobs,release,ref)
    return c,old,data,dict(current_context=ctx,reservation=receipt,current_source_controls=controls,
      manifest_sha256=expected,producer=live,producer_run=run,producer_jobs=jobs,producer_release=release,producer_ref=ref)

def restore_source(archive,manifest,target,spec):
    """Verify every regular migration member; retain only the exact2057 source tree."""
    require(manifest["encoding"]=="tar-gzip" and manifest["parts"]==[dict(spec["part"],
      name="batch-000002.tar.gz",url="https://github.com/Melihakbulut221/nssoc/releases/download/cloud-migration-tools-20261013-000/batch-000002.tar.gz")],"source part join")
    records=manifest["records"];require(len(records)==spec["full_members"],"full migration count")
    expected={r["path"]:r for r in records}
    require(len(expected)==len(records),"duplicate source manifest")
    selected={n:r for n,r in expected.items()if n.startswith(spec["prefix"])}
    require(len(selected)==spec["members"],"selected source count")
    require(not target.exists(),"new source destination");target.mkdir()
    seen=set();observed={};total=0
    with tarfile.open(archive,"r|gz")as tar:
        for member in tar:
            name=member.name.removeprefix("./").rstrip("/")if member.isdir()else member.name.removeprefix("./")
            frozen.checked_path(name)
            require(name not in seen,"duplicate source member");seen.add(name)
            if member.isdir():
                require(any(p.startswith(name+"/")for p in expected),"unexpected source directory");continue
            require(member.isfile() and not member.issparse() and name in expected,"unexpected source/link/special")
            r=expected[name];require(member.size==r["bytes"],"source member size")
            total+=member.size;require(total<=16*1024**3,"source expansion bound")
            h=hashlib.sha256();count=0;out=None
            if name in selected:
                p=target/name[len(spec["prefix"]):];p.parent.mkdir(parents=True,exist_ok=True);out=p.open("xb")
            try:
                with tar.extractfile(member)as stream:
                    while block:=stream.read(1024*1024):
                        h.update(block);count+=len(block)
                        if out is not None:out.write(block)
            finally:
                if out is not None:out.close()
            require(count==r["bytes"] and h.hexdigest()==r["sha256"],"source member fingerprint")
            if name in selected:p.chmod(r["mode"]&0o777)
            observed[name]=dict(bytes=count,sha256=h.hexdigest())
    require(set(observed)==set(expected),"missing source member")
    return dict(full_count=len(observed),selected_count=len(selected),full_members=observed,
      source_members={n[len(spec["prefix"]):]:observed[n]for n in selected},all_members_verified=True)

def source_census(root):
    return {p.relative_to(root).as_posix():pin(p)["sha256"]for p in sorted(root.rglob("*"))
      if p.is_file()and p.suffix in (".c",".h")}

def qualified_source(source,out,c):
    """Exactly reproduce the existing producer patches, not the historical upstream snapshots."""
    import patch_magic_hbt_contract_v2 as hbt
    import patch_magic_hbt_multiplicity_v3 as mult
    import patch_magic_finite_tap_v1 as tap
    import patch_magic_esd_v1 as esd
    import patch_magic_coupled_cap_v2 as coupled
    import patch_magic_cap_precision_v3 as precise
    import patch_magic_area_product_v4 as area
    target=out/"baseline-source";shutil.copytree(source,target)
    changes=[]
    def apply(path,fn):
        p=target/path;before=pin(p);p.write_bytes(fn(p.read_bytes()))
        changes.append(dict(path=path,before=before,after=pin(p)))
    apply("extract/ExtBasic.c",lambda b:hbt.patch("ExtBasic.c",b))
    apply("extract/ExtBasic.c",mult.patch)
    for name in ("ExtBasic.c","ExtTech.c"):apply("extract/"+name,lambda b,n=name:tap.patch(n,b))
    for name in ("CIFrdtech.c","CIFgen.c"):apply("cif/"+name,lambda b,n=name:esd.patch(n,b))
    for name in coupled.SOURCES:apply("resis/"+name,lambda b,n=name:coupled.patch(n,b))
    precise.patch(target,out/"patch3")
    for name in precise.EDITS:shutil.copyfile(out/"patch3"/name,target/name)
    area.patch(target,out/"patch4");shutil.copyfile(out/"patch4/ResMakeRes.c",target/"resis/ResMakeRes.c")
    header=target/"resis/resis.h";text=header.read_text()
    require(pin(header)["sha256"]=="f70ea5aac67a40a5cfcb73bb9485ab114a26655fe3f7c8abd10456810b6a7df6","qualified pre-double header")
    for a,b in [
      ("    float\trg_nodecap; /* Legacy total load, including coupling. */","    double\trg_nodecap; /* Legacy total load, including coupling. */"),
      ("    float\t\tcapacitance;\t/* Capacitance between node and   */","    double\t\tcapacitance;\t/* Capacitance between node and   */")]:
        require(text.count(a)==1,"existing double-total seam");text=text.replace(a,b)
    header.write_text(text)
    actual=source_census(target)
    require(actual==c["source_producer"]["candidate"],"complete actual559 qualified sources")
    write(out/"qualified-source.json",encode(dict(files=actual,historical_device_patches=changes,
      producer=c["source_producer"],historical_source_only_snapshots_are_not_this_baseline=True)))
    return target

def trace_sources(sources,expected,rules,payloads):
    """Only literal insertions; reverse must recover every qualified input byte."""
    require(set(sources)==set(expected),"complete five actual source inputs")
    require(all(hashlib.sha256(sources[n]).hexdigest()==h for n,h in expected.items()),"actual qualified pre-patch hashes")
    current=dict(sources)
    for r in rules:
        anchor=r["anchor"].encode();added=payloads[r["payload"]]if "payload"in r else r["insertion"].encode()
        require(r["position"]in ("before","after")and bool(anchor)and bool(added),"insertion shape")
        require(current[r["path"]].count(anchor)==1,"qualified unique insertion seam")
        joined=added+anchor if r["position"]=="before"else anchor+added
        current[r["path"]]=current[r["path"]].replace(anchor,joined)
    reverse=dict(current)
    for r in reversed(rules):
        anchor=r["anchor"].encode();added=payloads[r["payload"]]if "payload"in r else r["insertion"].encode()
        joined=added+anchor if r["position"]=="before"else anchor+added
        require(reverse[r["path"]].count(joined)==1,"unique reverse seam")
        reverse[r["path"]]=reverse[r["path"]].replace(joined,anchor)
    require(reverse==sources,"complete reverse byte equality")
    return current

def instrument_source(baseline,out,c,root=ROOT):
    spec=decode(frozen.regular(root,historical.SPEC).read_bytes())
    expected={n:c["source_producer"]["candidate"][n]for n in spec["files"]}
    sources={n:(baseline/n).read_bytes()for n in expected}
    payloads={r["payload"]:frozen.regular(root,r["payload"]).read_bytes()for r in spec["rules"]if "payload"in r}
    after=trace_sources(sources,expected,spec["rules"],payloads)
    target=out/"trace-source";shutil.copytree(baseline,target)
    for n,raw in after.items():(target/n).write_bytes(raw)
    final=source_census(target);initial=source_census(baseline)
    require(set(final)==set(initial)and {n for n in final if final[n]!=initial[n]}==set(expected),"only five diagnostic source changes")
    write(out/"trace-source-derivation.json",encode(dict(before=initial,after=final,rules=spec["rules"],
      all_original_bytes_reverse_exact=True,numerical_statements_changed=False,
      prior_three_upstream_snapshots_used_as_current=False,reduced_element_ownership_proved=False)))
    return target,final

def relocate_tcl(raw,old_dir,old_gds,new_dir,new_gds):
    text=raw.decode()
    edits=[("cd {"+old_dir+"}","cd {"+str(new_dir)+"}"),("gds read {"+old_gds+"}","gds read {"+str(new_gds)+"}")]
    for a,b in edits:
        require(text.splitlines().count(a)==1,"exact original Tcl path")
        text=text.replace(a,b)
    require("extresist tolerance 0.000001\nextresist simplify off\nextresist all\n"in text,"original native RC predicates")
    reverse=text
    for a,b in reversed(edits):require(reverse.count(b)==1,"reverse Tcl path");reverse=reverse.replace(b,a)
    require(reverse.encode()==raw,"all other Tcl bytes unchanged")
    return text.encode(),edits

def native_records(directory):
    result={}
    for name in ("pump_wires.ext","pump_wires.res.ext"):
        lines=(directory/name).read_bytes().splitlines()
        for kind in (b"resist",b"rnode",b"cap"):
            selected=[x for x in lines if x.split(maxsplit=1)[:1]==[kind]]
            result[name+":"+kind.decode()]=selected
    for name in ("baseline.spice","wires.spice"):
        statements=[]
        for line in (directory/name).read_text().splitlines():
            line=line.strip()
            if not line or line.startswith("*"):continue
            if line.startswith("+"):
                require(bool(statements),"orphan SPICE continuation");statements[-1]+=" "+line[1:].strip()
            else:statements.append(line)
        result[name]=[" ".join(x.split()).encode()for x in statements]
    require(result["pump_wires.res.ext:resist"]and result["pump_wires.res.ext:rnode"]and
      result["pump_wires.ext:cap"],"complete native numerical records")
    return result

def compare_outputs(directories):
    rows={n:native_records(p)for n,p in directories.items()}
    first=next(iter(rows.values()))
    for n,r in rows.items():
        require(r==first,"native record/order/value mismatch: "+n)
    return dict(status="EXACT_NATIVE_RECORD_EQUIVALENCE",variants=list(directories),
      records={n:dict(count=len(v),sha256=hashlib.sha256(b"\n".join(v)+b"\n").hexdigest())for n,v in first.items()},
      equivalence="Exact ordered resist/rnode/cap bytes and all noncomment SPICE statements; complete raw files retained",
      output_geometry_or_electrical_acceptance=False)

def validate_trace(path,emitted_count,expected_lines=None):
    counts=collections.Counter();seq=0;epochs=0;active=False;footer=None;snapshot=None;seen_start=False;emitted=[]
    with path.open("rb")as stream:
        for line in stream:
            require(footer is None,"records after footer")
            r=decode(line);e=r.get("event");require(r.get("schema")==1,"trace schema");counts[e]+=1
            if e=="trace_start":
                require(not seen_start and seq==0 and counts[e]==1,"trace first record")
                require(r["instrumentation"]=="nssoc_resistor_provenance_v1"and r["resistor_footprint_is_not_inferred"]is True,"trace identity")
                seen_start=True;continue
            require(seen_start,"missing trace start")
            if e=="trace_end":
                require(r["records_before_footer"]==seq and r["epochs"]==epochs and r["net_still_open"]is False
                  and r["physical_ownership_proved"]is False and not active and snapshot is None,"complete trace footer")
                footer=r;continue
            seq+=1;require(r.get("seq")==seq,"contiguous trace sequence")
            if e=="net_begin":
                require(not active,"nested trace net");active=True;epochs+=1
                require(r["physical_ownership_proved"]is False and isinstance(r["net_name_hex"],str),"net provenance")
                bytes.fromhex(r["net_name_hex"])
            require(r.get("epoch")==epochs and epochs>0,"trace epoch")
            if e=="net_end":require(active,"net end without begin");active=False
            elif e=="snapshot_begin":
                require(snapshot is None and r["phase"]in ("before_simplify","after_simplify"),"snapshot begin")
                snapshot=[r["phase"],0]
            elif e=="snapshot_resistor":
                require(snapshot is not None and r["phase"]==snapshot[0]and r["index"]==snapshot[1],"snapshot sequence")
                snapshot[1]+=1
            elif e=="snapshot_end":
                require(snapshot==[r["phase"],r["count"]],"snapshot complete count");snapshot=None
            require(e in ("net_begin","net_end","create_tile","create_contact","snapshot_begin","snapshot_resistor",
              "snapshot_end","emitted_resistor","emitted_orphan_zero"),"unknown trace event")
            if "rr_value_milliohms_hex"in r:
                value=float.fromhex(r["rr_value_milliohms_hex"])
                require(math.isfinite(value)and value>=0,"finite native resistance observation")
                require(type(r["rr_tt"])is int and type(r["type_index_valid"])is bool,"typed material observation")
            if expected_lines is not None and e in ("emitted_resistor","emitted_orphan_zero"):
                first=r["node1"]["name_hex"]if e=="emitted_resistor"else r["node1_name_hex"]
                second=r["node2"]["name_hex"]if e=="emitted_resistor"else r["node2_name_hex"]
                emitted.append(b'resist "'+bytes.fromhex(first)+b'" "'+bytes.fromhex(second)+b'" '+r["ext_value_token"].encode())
            if e in ("create_tile","create_contact","emitted_resistor","emitted_orphan_zero"):
                require(r["final_footprint_proved"]is False,"no reduced footprint ownership")
    require(footer is not None and counts["trace_start"]==counts["trace_end"]==1,"trace complete")
    require(counts["create_tile"]>0 and counts["create_contact"]>0 and counts["snapshot_resistor"]>0,"actual constructor observations")
    require(counts["emitted_resistor"]+counts["emitted_orphan_zero"]==emitted_count,"all native resistor emissions observed")
    require(counts["net_begin"]==counts["net_end"]==epochs,"all construction epochs closed")
    if expected_lines is not None:require(emitted==expected_lines,"every trace emitted endpoint/value/order matches native file")
    return dict(status="PASS_COMPLETE_ACTUAL_RESISTOR_TRACE_NOT_REDUCED_OWNERSHIP",counts=dict(counts),
      trace=pin(path),epochs=epochs,records=seq,reduced_element_ownership_proved=False)

@contextlib.contextmanager
def environment(values):
    names=set(values)|{"GH_TOKEN","GITHUB_TOKEN","PYTHONHOME","PYTHONPATH","PYTHONEXECUTABLE","LD_PRELOAD","NSSOC_MAGIC_RESISTOR_TRACE"}
    old={n:os.environ.get(n)for n in names}
    try:
        for n in names:os.environ.pop(n,None)
        for n,v in values.items():os.environ[n]=str(v)
        yield
    finally:
        for n,v in old.items():
            if v is None:os.environ.pop(n,None)
            else:os.environ[n]=v

def execute(supervisor,argv,label,cwd,gate,output=None):
    gate();stop=threading.Event();errors=[];primary=None;result=None
    def watch():
        while not stop.wait(.1):
            try:
                if output is not None and sum(p.stat().st_size for p in output.rglob("*")if p.is_file())>1073741824:
                    errors.append(AssertionError("original native scratch1024MiB limit"))
                    supervisor.stop_process(supervisor.ACTIVE);return
            except BaseException as exc:errors.append(exc);supervisor.stop_process(supervisor.ACTIVE);return
    watcher=threading.Thread(target=watch,daemon=True);watcher.start()
    try:
        result=supervisor.supervised(argv,label,seconds=1200,cwd=cwd,
          min_available_kib=2097152,max_group_rss_kib=10485760)
    except BaseException as exc:primary=exc
    finally:
        stop.set();watcher.join(timeout=5)
        if watcher.is_alive():errors.append(AssertionError("scratch watcher survived"))
    if primary is not None:raise primary
    if errors:raise errors[0]
    record=decode(frozen.regular(supervisor.TRACE,label+".command.json").read_bytes())
    require(record["argv"]==list(map(str,argv))and record["returncode"]==0 and record["supervision_failure"]is None
      and not record["process_group_cleanup"]["remaining_live"],"owned command outcome")
    for k in ("stdout","stderr"):
        require(pin(frozen.regular(supervisor.TRACE,label+"."+k))==dict(bytes=record[k+"_bytes"],sha256=record[k+"_sha256"]),"complete command stream")
    gate();return record

def rebuild(build,label,out,supervisor,gate,expected):
    for p in build.rglob("*"):
        if p.is_file()and(p.suffix in (".o",".a",".so")or p.name in ("config.cache","config.status")):p.unlink()
    require(not list(build.rglob("*.o"))and not list(build.rglob("*.so")),"clean full rebuild")
    records=[]
    for phase,argv in [("configure",["sh","configure","--prefix="+str(out/(label+"-install"))]),("make",["make","-j2"])]:
        with environment({}):records.append(execute(supervisor,argv,label+"-"+phase,build,gate))
    require(source_census(build)==expected,"build mutated protected C/H source")
    lib=build/"magic/tclmagic.so";require(lib.stat().st_size>1000000,"complete Magic library")
    with environment({}):records.append(execute(supervisor,["ldd",str(lib)],label+"-dependencies",out,gate))
    stdout=(supervisor.TRACE/(label+"-dependencies.stdout")).read_text()
    require("not found"not in stdout,"unresolved native library")
    return dict(library=str(lib),library_identity=pin(lib),commands=records,full_rebuild=True)

def extraction(selected,variant,library,out,supervisor,gate,trace=False):
    current=selected/"mim/precise";base=out/variant;base.mkdir()
    rt=base/"precision-runtime";shutil.copytree(current/"precision-runtime",rt)
    target=rt/"lib/magic/tcl/tclmagic.so";shutil.copyfile(library,target)
    native=base/"rc03";native.mkdir()
    old="/home/runner/work/nssoc/nssoc/hw/soc/out/cloud-cdr-selector-width-fresh-rc/"
    original=(current/"wire/rc03/native.tcl").read_bytes()
    text,edits=relocate_tcl(original,old+"mim/precise/wire/rc03",old+"mim/precise/wire/native05/wires.gds",
      native,current/"wire/native05/wires.gds")
    write(native/"native.tcl",text)
    write(base/"derivation.json",encode(dict(original=pin(current/"wire/rc03/native.tcl"),derived=pin(native/"native.tcl"),
      edits=edits,all_other_Tcl_bytes_equal=True,runtime_library=pin(target))))
    values=dict(CAD_ROOT=rt/"lib")
    if trace:values["NSSOC_MAGIC_RESISTOR_TRACE"]=base/"resistor-physical-trace.jsonl"
    argv=["/usr/bin/prlimit","--as=4294967296","--core=0","--","/usr/bin/tclsh8.6",
      str(rt/"lib/magic/tcl/magic.tcl"),"-dnull","-noconsole","-rcfile",
      str(current/"ngspice-mim-tech/ihp-sg13g2.magicrc"),str(native/"native.tcl")]
    with environment(values):record=execute(supervisor,argv,"extract-"+variant,native,gate,output=native)
    logs=(supervisor.TRACE/("extract-"+variant+".stdout")).read_bytes()+(supervisor.TRACE/("extract-"+variant+".stderr")).read_bytes()
    require(b"NSSOC_WIRE_RC_COMPLETE"in logs and b"NSSOC_RESISTOR_TRACE_ERROR"not in logs,"complete native extraction/trace")
    require((base/"resistor-physical-trace.jsonl").exists()==trace,"trace environment isolation")
    require(pin(target)==pin(library),"runtime library unchanged")
    write(base/"command-proof.json",encode(record));return native

def perform(ctx,reserved,controls_raw,expected,out,root=ROOT,api_call=frozen.api,fetch=frozen.download):
    c,old,data,admission=preflight(ctx,reserved,controls_raw,expected,root,api_call)
    write(out/"admission.json",encode(admission));write(out/"source-controls.json",controls_raw)
    work=out/"work";work.mkdir()
    require(shutil.disk_usage(out).free>20*1024**3,"runner free space20GiB")
    # Complete current6647 capsule is authenticated; no suffix-based historical selection.
    archive,transport=frozen.acquire(old,data["parts"],work,fetch)
    write(out/"current-transport.json",encode(transport))
    selected=work/"current";census=frozen.select_archive(archive,data["full"],list(data["full"]),data["parts"]["source_directory"],selected)
    write(out/"current-full-census.json",encode(census));archive.unlink()
    for n,h in data["full"].items():require(pin(frozen.regular(selected,n))["sha256"]==h,"current restored member")
    # Direct authenticated JSON and source migration. Native bytes stay only on this runner.
    summary=work/"qualified-producer-summary.json";fetch(c["source_producer"]["summary"],summary)
    actual=decode(summary.read_bytes())
    require(actual["status"]==c["source_producer"]["status"]and actual["source_head"]==c["source_producer"]["source"]and
      actual["source_changes"]["candidate"]==c["source_producer"]["candidate"],"authentic complete559 producer map")
    mp=work/"migration-manifest.json";fetch(c["source_archive"]["manifest"],mp)
    manifest=decode(mp.read_bytes());package=work/"migration-source.tar.gz";fetch(c["source_archive"]["part"],package)
    source=work/"archived-source";source_proof=restore_source(package,manifest,source,c["source_archive"])
    write(out/"migration-full-census.json",encode(source_proof));package.unlink()
    baseline=qualified_source(source,work,c)
    write(out/"qualified-source-snapshots.json",encode({n:(baseline/n).read_text()for n in decode(frozen.regular(root,historical.SPEC).read_bytes())["files"]}))
    candidate,after=instrument_source(baseline,work,c,root)
    gate=lambda:source_guard(expected,root)
    supervisor=None;heartbeat=None;previous={};primary=None;result=None
    try:
        supervisor=runtime.supervisor(root,out,out/"supervision",gate,runtime.SAMPLER_SHA);supervisor.TRACE.mkdir()
        for sig in (signal.SIGINT,signal.SIGTERM):
            previous[sig]=signal.getsignal(sig);signal.signal(sig,supervisor.interrupted)
        heartbeat=threading.Thread(target=supervisor.heartbeat,daemon=True);heartbeat.start()
        built={}
        built["baseline"]=rebuild(baseline,"baseline",work,supervisor,gate,c["source_producer"]["candidate"])
        built["instrumented"]=rebuild(candidate,"instrumented",work,supervisor,gate,after)
        write(out/"builds.json",encode(built))
        original=selected/"mim/precise/precision-runtime/lib/magic/tcl/tclmagic.so"
        require(pin(original)["sha256"]==c["current_rc"]["library"],"actual archived library")
        captures={"saved_current":selected/"mim/precise/wire/rc03"}
        for name,lib,traced in [
          ("archived",original,False),("rebuilt_baseline",Path(built["baseline"]["library"]),False),
          ("trace_off",Path(built["instrumented"]["library"]),False),("trace_on",Path(built["instrumented"]["library"]),True)]:
            captures[name]=extraction(selected,name,lib,work,supervisor,gate,traced)
        equivalent=compare_outputs(captures);write(out/"equivalence.json",encode(equivalent))
        trace=validate_trace(work/"trace_on/resistor-physical-trace.jsonl",equivalent["records"]["pump_wires.res.ext:resist"]["count"],native_records(captures["trace_on"])["pump_wires.res.ext:resist"])
        write(out/"trace-summary.json",encode(trace))
        shutil.copyfile(work/"trace_on/resistor-physical-trace.jsonl",out/"resistor-physical-trace.jsonl")
        require(all(pin(frozen.regular(selected,n))["sha256"]==h for n,h in data["full"].items()),"entire current input mutation")
        require(source_census(baseline)==c["source_producer"]["candidate"]and source_census(candidate)==after,"source mutation after extraction")
        gate()
        result=dict(status="PASS_FULL_MAGIC_BUILD_CURRENT500_TRACE_EQUIVALENCE_NOT_RC_OR_PHYSICAL_ACCEPTANCE",
          current_context=ctx,builds=built,equivalence=equivalent,trace=trace,complete_current_members=6647,
          complete_migration_members=14454,qualified_source_files=559,original500_lineage=True,
          native_build_executed=True,native_extraction_executed=True,**FLAGS)
    except BaseException as exc:primary=exc
    finally:
        actions,errors=lifecycle.finish(supervisor,heartbeat,previous)
        try:write(out/"lifecycle.json",encode(dict(primary_error=None if primary is None else repr(primary),actions=actions)))
        except BaseException as exc:
            errors.append(exc)
            try:print("MAGIC_BUILD_LIFECYCLE_FALLBACK "+encode(dict(primary_error=None if primary is None else repr(primary),actions=actions)).decode(),flush=True)
            except BaseException:pass
        if primary is None and errors:primary=errors[0]
    if primary is not None:raise primary
    return result

def preserve_current_source(out,expected,root=ROOT):
    destination=out/"execution-source";destination.mkdir()
    raw=frozen.regular(root,PINS).read_bytes()
    write(destination/"manifest.json",raw)
    m=decode(raw);records={};errors=[]
    for name in m["files"]:
        try:
            source=frozen.regular(root,name);target=destination/name
            target.parent.mkdir(parents=True,exist_ok=True);write(target,source.read_bytes())
            records[name]=pin(target)
        except BaseException as exc:errors.append(dict(path=name,error=repr(exc)))
    write(out/"execution-source-census.json",encode(dict(files=records,errors=errors,
      expected_manifest_sha256=expected,actual_manifest=pin(destination/"manifest.json"))))
    require(not errors,"execution source preservation incomplete")

def run(ctx,reserved,controls_raw,expected,out,perform_fn=perform):
    require(not out.exists()and not out.is_symlink(),"new owned output");out.mkdir(parents=True)
    primary=None;result=None
    try:
        preserve_current_source(out,expected)
        result=perform_fn(ctx,reserved,controls_raw,expected,out)
    except BaseException as exc:
        primary=exc;result=dict(status="FAIL_MAGIC_BUILD_OR_TRACE_EQUIVALENCE",current_context=ctx,
          error=dict(type=type(exc).__name__,message=str(exc)),traceback=traceback.format_exc(),**FLAGS)
    try:write(out/"result.json",encode(result))
    except BaseException as exc:
        try:print("MAGIC_BUILD_RESULT_FALLBACK "+encode(result).decode(),flush=True)
        except BaseException:pass
        if primary is None:primary=exc
    if primary is not None:raise primary
    return result

def publication(ctx,reserved,out,destination,api_call=frozen.api,uploader=None,pack_fn=packing.pack):
    """Publication remains possible after source/refusal/final-record failures; never qualifies them."""
    require(out.is_dir()and not out.is_symlink(),"owned output available")
    tag="cloud-results-"+ctx["token"]+"-"+GROUP
    info=api_call("releases/tags/"+tag);ref=api_call("git/ref/tags/"+tag)
    assets=frozen.release_binding(info,ref,tag,ctx["source"])
    require(reserved["release_id"]==info["id"]and reserved["tested_source"]==ctx["source"]and
      reserved["tag"]==tag and reserved["externally_reserved"]is True and reserved["assets_overwritten"]is False,"publication reservation")
    require(not assets,"no overwrite or resume existing publication")
    files={p.relative_to(out).as_posix():pin(p)for p in sorted(out.rglob("*"))if p.is_file()and not p.is_symlink()}
    require(all(not p.is_symlink()for p in out.rglob("*")),"publication source symlink")
    write(out/"publication-inventory.json",encode(files))
    direct={n:v for n,v in files.items()if "/"not in n and n.endswith((".json",".jsonl"))}
    plan={n:dict(v,disposition="archive_only_empty"if v["bytes"]==0 else"direct",archive_member=out.name+"/"+n)for n,v in direct.items()}
    write(out/"direct-publication-plan.json",encode(dict(files=plan,native_accepted=False,source_validation_not_bypassed_for_execution=True)))
    destination.mkdir(parents=True,exist_ok=False)
    stem=GROUP+"-"+ctx["token"];m=pack_fn(out,stem,destination)
    if uploader is None:
        def uploader(path):
            subprocess.run(["gh","release","upload",tag,str(path),"--repo",frozen.REPOSITORY],check=True)
    payloads=[destination/x["name"]for x in m["parts"]]+[destination/(stem+".parts.json")]
    payloads += [out/n for n,v in direct.items()if v["bytes"]>0]+[out/"direct-publication-plan.json",out/"publication-inventory.json"]
    uploaded=[]
    for p in payloads:
        uploader(p);uploaded.append(dict(name=p.name,**pin(p)))
    observed=frozen.release_binding(api_call("releases/tags/"+tag),api_call("git/ref/tags/"+tag),tag,ctx["source"])
    require(set(observed)=={x["name"]for x in uploaded},"complete publication asset names")
    for x in uploaded:
        a=observed[x["name"]];require(a["size"]==x["bytes"]and a.get("digest")=="sha256:"+x["sha256"],"published asset bytes")
    return dict(status="COMPLETE_BYTE_PRESERVATION_NOT_NATIVE_ACCEPTANCE",assets=uploaded,parts=m,native_accepted=False)

def main():
    p=argparse.ArgumentParser();p.add_argument("--mode",choices=("preflight","native","publish"),required=True)
    p.add_argument("--pins-sha256",required=True);p.add_argument("--reservation",type=Path,required=True)
    p.add_argument("--controls",type=Path,required=True);p.add_argument("--output",type=Path,required=True)
    a=p.parse_args();a.output=a.output.resolve();ctx=context(os.environ)
    require(subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()==ctx["source"],"checkout source")
    reserved=decode(a.reservation.read_bytes())
    if a.mode=="preflight":
        _,_,_,proof=preflight(ctx,reserved,a.controls.read_bytes(),a.pins_sha256)
        print(encode(proof).decode(),end="")
    elif a.mode=="native":run(ctx,reserved,a.controls.read_bytes(),a.pins_sha256,a.output)
    else:
        if not a.output.exists():
            a.output.mkdir(parents=True)
            write(a.output/"result.json",encode(dict(status="FAIL_NATIVE_CONTROLLER_NOT_STARTED_OR_OUTPUT_MISSING",
              current_context=ctx,**FLAGS)))
        result=publication(ctx,reserved,a.output,a.output.parent/(a.output.name+"-parts"))
        print("MAGIC_BUILD_PUBLICATION "+encode(result).decode(),flush=True)

if __name__=="__main__":main()
