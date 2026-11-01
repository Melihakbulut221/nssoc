#!/usr/bin/env python3
"""Cloud-only four-unit native geometry/DRC/LVS qualification; preserve failures."""
import argparse,base64,hashlib,json,os,shutil,subprocess,sys,tarfile,time,traceback
from pathlib import Path,PurePosixPath
from concurrent.futures import ThreadPoolExecutor
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"cloud-mos-unit-native"
DERIVED=ROOT/"cloud-mos-unit-derived"
REPO="Melihakbulut221/nssoc"
PINFILE=ROOT/"scripts/cdr-mos-unit-pins.json"
def sha(p):
    with Path(p).open("rb") as f:return hashlib.file_digest(f,"sha256").hexdigest()
def write(p,obj):
    p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(obj,indent=2)+"\n")
def api(path):
    return json.loads(subprocess.check_output(["gh","api","repos/"+REPO+"/"+path],text=True))
def validate_sources():
    pins=json.loads(PINFILE.read_text())
    for p,v in pins.items():
        q=ROOT/p
        assert q.stat().st_size==v["bytes"] and sha(q)==v["sha256"],p
    return pins
def controls():
    assert os.environ.get("GITHUB_ACTIONS")=="true"
    from cdr_mos_unit_geometry import controls as check
    pins=validate_sources()
    for name in pins:
        if name.endswith(".py"):compile((ROOT/name).read_text(),name,"exec")
    result=dict(status="PASS_SOURCE_CONTROLS_ONLY",source=os.environ["GITHUB_SHA"],
        pins=pins,manifest_sha256=sha(PINFILE),geometry_controls=check(),
        native_geometry_run=False,full_phy_accepted=False)
    write(DERIVED/"source-controls.json",result)
    return result
def execute(args,directory,name):
    directory.mkdir(parents=True,exist_ok=True)
    with (directory/(name+".log")).open("w") as f:
        p=subprocess.run([str(x) for x in args],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
    return p.returncode
def reserve():
    run=int(os.environ["GITHUB_RUN_ID"]);source=os.environ["GITHUB_SHA"]
    prior=api("actions/runs/"+os.environ["UNIT_CONTROLS_RUN"])
    assert prior["head_sha"]==source and prior["status"]=="completed" and prior["conclusion"]=="success"
    assert prior["event"]=="workflow_dispatch" and prior["id"]!=run
    jobs=api("actions/runs/"+str(prior["id"])+"/jobs?per_page=100")["jobs"]
    assert any(j["name"]=="source-controls" and j["conclusion"]=="success" for j in jobs)
    assert all(j["conclusion"]=="skipped" for j in jobs if j["name"]=="native-units")
    tag="cloud-results-"+str(run)+"-1-mos-unit-physical"
    for _ in range(90):
        r=subprocess.run(["gh","api","repos/"+REPO+"/releases/tags/"+tag],text=True,capture_output=True)
        if r.returncode==0:break
        if "404" not in r.stderr:raise RuntimeError(r.stderr)
        time.sleep(5)
    else:raise RuntimeError("Independent exact-source release reservation absent")
    release=json.loads(r.stdout)
    assert release["target_commitish"]==source and not release["assets"] and not release["draft"]
    assert api("git/ref/tags/"+tag)["object"]["sha"]==source
    result=dict(run=run,source=source,controls_run=prior["id"],tag=tag,release=release["id"],
        independent_empty_release_verified=True)
    write(DERIVED/"reservation.json",result);return result
def fetch(url,expected,dest):
    dest.parent.mkdir(parents=True,exist_ok=True)
    subprocess.run(["curl","--fail","--location","--retry","3",url,"-o",str(dest)],check=True)
    assert sha(dest)==expected,str(dest)
def prepare_runtime():
    work=Path(os.environ["RUNNER_TEMP"])/("mos-unit-"+os.environ["GITHUB_RUN_ID"])
    work.mkdir(exist_ok=False)
    spec=json.loads((ROOT/"docs/evidence/pcie-tx-layout-cloud-input-20261013.json").read_text())
    archive=work/"pdk.tar.gz"
    with archive.open("wb") as f:
        subprocess.run(["gh","api","repos/"+REPO+"/releases/assets/635047665","-H","Accept: application/octet-stream"],stdout=f,check=True)
    assert archive.stat().st_size==667167 and sha(archive)=="8caa4db1ae881af8fe57fa9d01df16bd57a2f31ece40fecd9bc4e8e139952ac2"
    runtime=work/"runtime";runtime.mkdir()
    with tarfile.open(archive) as tar:
        members=tar.getmembers();names=set()
        for m in members:
            p=PurePosixPath(m.name)
            assert not p.is_absolute() and ".." not in p.parts and m.name not in names
            assert m.isfile() or m.isdir()
            names.add(m.name)
        assert sum(m.size for m in members)<100000000
        tar.extractall(runtime,filter="data")
    manifest=json.loads((runtime/"manifest.json").read_text())
    for n,v in manifest["files"].items():
        p=PurePosixPath(n);assert not p.is_absolute() and ".." not in p.parts
        assert sha(runtime/n)==v["sha256"],n
    app=Path(os.environ["CLOUD_APPIMAGE"])
    assert sha(app)==spec["runtime_sha256"]
    locks={}
    for name in ("drc","lvs"):
        lock=json.loads((ROOT/("hw/soc/pnr/ihp-"+name+".lock.json")).read_text())
        assert lock["commit"]=="5e6d592e4002946a4616f798c357f0f3c06cf3b6"
        target=work/name;target.mkdir()
        def restore(row):
            p=PurePosixPath(row["path"]);assert not p.is_absolute() and ".." not in p.parts
            file=target/row["path"]
            fetch("https://raw.githubusercontent.com/IHP-GmbH/IHP-Open-PDK/"+lock["commit"]+"/"+row["path"],row["sha256"],file)
            assert file.stat().st_size==row["bytes"]
        with ThreadPoolExecutor(max_workers=6) as pool:list(pool.map(restore,lock["files"]))
        locks[name]=(target,lock)
    protected={str(runtime/n):v["sha256"] for n,v in manifest["files"].items()}
    for root,lock in locks.values():protected.update({str(root/r["path"]):r["sha256"] for r in lock["files"]})
    write(DERIVED/"runtime.json",dict(package_sha256=sha(archive),manifest_sha256=sha(runtime/"manifest.json"),
        appimage_sha256=sha(app),protected=protected))
    return app,runtime/"pdk",locks,protected
def run_native():
    assert os.environ.get("GITHUB_ACTIONS")=="true" and os.environ["GITHUB_RUN_ATTEMPT"]=="1"
    pins=validate_sources();reservation=reserve();OUT.mkdir(exist_ok=False)
    result=dict(status="RUNNING",source=os.environ["GITHUB_SHA"],reservation=reservation,steps=[],
        full_phy_accepted=False,full_pd650_generated=False,qualified_pex=False)
    def save():write(DERIVED/"result.json",result)
    save()
    try:
        app,pdk,locks,protected=prepare_runtime()
        geometry=ROOT/"scripts/cdr_mos_unit_geometry.py"; generated=OUT/"geometry"
        assert execute([app,"python",geometry,"--pdk",pdk,"--out",generated],OUT,"generation")==0
        record=json.loads((generated/"geometry.json").read_text())
        write(DERIVED/"geometry.json",record)
        sys.path.insert(0,str(ROOT/"hw/soc/flow"))
        from check_ihp_drc import record_result
        for unit in record["units"]:
            top=unit["top"];case=generated/top
            for kind in ("drc","lvs_deep","lvs_flat","wrong_width","physical_sd_short"):
                d=OUT/top/kind;d.mkdir(parents=True)
                isdrc=kind=="drc";negative=kind in ("wrong_width","physical_sd_short")
                root,lock=locks["drc" if isdrc else "lvs"]
                gds=case/("short-sd.gds" if kind=="physical_sd_short" else "unit.gds")
                reference=case/("wrong-width.cir" if kind=="wrong_width" else "reference.cir")
                protected_case={gds:sha(gds),reference:sha(reference)}
                opts=["input="+str(gds),"topcell="+top,"log="+str(d/"deck.log"),
                      "run_mode="+("flat" if kind=="lvs_flat" else "deep")]
                opts+=["report="+str(d/"drc.lyrdb"),"threads=2","no_recommended=False","precheck_drc=False"] if isdrc else [
                    "schematic="+str(reference),"report="+str(d/"result.lvsdb"),"target_netlist="+str(d/"extracted.cir"),
                    "thr=2","no_simplify=true","top_lvl_pins=true"]
                cmd=[app,"klayout","-b","-zz","-r",root/lock["entrypoint"]]
                for opt in opts:cmd+=["-rd",opt]
                code=execute(cmd,d,"run")
                step=dict(top=top,kind=kind,returncode=code,input_sha256={str(k):v for k,v in protected_case.items()})
                result["steps"].append(step);save()
                assert code==0,"Native deck execution failure"
                if isdrc:
                    measurement=record_result(d,top,code,protected_case)
                    step["measurement"]=measurement
                    assert measurement["category_count"]==560
                    assert "KLayout DRC run for tables 'main' completed" in (d/"run.log").read_text()
                    assert measurement["status"]=="PASS" and measurement["markers"]==0
                else:
                    auditcode=execute([app,"python",ROOT/"hw/soc/flow/audit_klayout_lvs.py",d/"result.lvsdb",
                        "--top",top,"--deck-log",d/"deck.log","--output",d/"audit.json"],d,"audit-run")
                    audit=json.loads((d/"audit.json").read_text());step["audit"]=audit
                    assert not audit["extraction_diagnostics"],"Extraction diagnostics invalidate comparison"
                    if negative:
                        assert auditcode==1 and audit["status"]=="FAIL" and audit["circuit_status_counts"].get("NoMatch",0)>=1
                    else:
                        assert auditcode==0 and audit["status"]=="PASS within comparison scope" and audit["circuit_status_counts"]=={"Match":1}
                        assert len(audit["circuits"])==1 and audit["circuits"][0]["layout_devices_recursive"]==2 and audit["circuits"][0]["schematic_devices_recursive"]==2
                        assert execute([app,"python",geometry,"--inspect",d/"result.lvsdb","--top",top,"--out",d/"devices.json"],d,"inspect")==0
                        native=json.loads((d/"devices.json").read_text())
                        assert len(native["devices"])==2
                        mos=[v for v in native["devices"] if v["model"].lower()=="sg13_lv_nmos"]
                        taps=[v for v in native["devices"] if v["model"].lower()=="ptap1"]
                        assert len(mos)==1 and len(taps)==1
                        params=mos[0]["parameters"]
                        # KLayout extracted geometrical parameters are um / um^2.
                        expected={"W":float(unit["width_um"]),"L":.3,
                            "AS":unit["expected_as_ad_um2"],"AD":unit["expected_as_ad_um2"],
                            "PS":unit["expected_ps_pd_um"],"PD":unit["expected_ps_pd_um"]}
                        step["native_devices"]=native
                        step["diffusion_parameter_comparison"]={k:dict(actual=params.get(k),expected=v,
                            matches=k in params and abs(params[k]-v)<=1e-8) for k,v in expected.items()}
                        assert all(v["matches"] for v in step["diffusion_parameter_comparison"].values()),"Proposed explicit-unit diffusion parameters differ from native extraction"
                assert all(sha(k)==v for k,v in protected_case.items())
                save()
        assert all(sha(k)==v for k,v in protected.items())
        validate_sources()
        assert len(result["steps"])==20
        result.update(status="PASS_FOUR_NATIVE_MOS_UNITS_DRC_UNSIMPLIFIED_LVS_AND_DIFFUSION_ONLY",
            runtime_sources_unchanged=True,source_files_unchanged=True)
    except BaseException as e:
        result.update(status="FAIL_OR_ERROR",error=repr(e),traceback=traceback.format_exc());raise
    finally:
        save()
        for p in OUT.rglob("*"):
            if p.is_file() and p.suffix in (".json",".log"):
                target=DERIVED/"native-reports"/p.relative_to(OUT)
                target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
def publish():
    assert os.environ.get("GITHUB_ACTIONS")=="true"
    DERIVED.mkdir(exist_ok=True)
    rfile=DERIVED/"reservation.json"
    if not rfile.exists():return
    r=json.loads(rfile.read_text());release=api("releases/"+str(r["release"]))
    assert release["target_commitish"]==os.environ["GITHUB_SHA"] and not release["assets"]
    OUT.mkdir(exist_ok=True)
    inventory={str(p.relative_to(OUT)):dict(bytes=p.stat().st_size,sha256=sha(p)) for p in OUT.rglob("*") if p.is_file()}
    write(DERIVED/"native-index.json",dict(source=os.environ["GITHUB_SHA"],files=inventory))
    archive=Path(os.environ["RUNNER_TEMP"])/"mos-unit-native.tar.gz"
    with tarfile.open(archive,"w:gz") as tar:
        for name in sorted(inventory):tar.add(OUT/name,arcname=name,recursive=False)
    assert archive.stat().st_size<200000000
    if not (DERIVED/"result.json").exists():write(DERIVED/"result.json",dict(status="FAIL_BEFORE_REPORT",full_phy_accepted=False))
    upload=[archive,DERIVED/"native-index.json",DERIVED/"result.json"]
    subprocess.run(["gh","release","upload",r["tag"],"--repo",REPO,*map(str,upload)],check=True)
    assets=api("releases/"+str(r["release"]))["assets"]
    assert len(assets)==3
    for p in upload:
        a=next(x for x in assets if x["name"]==p.name)
        assert a["size"]==p.stat().st_size and a["digest"]=="sha256:"+sha(p)
    write(DERIVED/"publication-result.json",dict(status="COMPLETE_NATIVE_PUBLICATION",**r,
        assets={p.name:dict(bytes=p.stat().st_size,sha256=sha(p)) for p in upload}))
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--controls",action="store_true");p.add_argument("--publish",action="store_true");a=p.parse_args()
    if a.controls:print(json.dumps(controls()))
    elif a.publish:publish()
    else:run_native()
