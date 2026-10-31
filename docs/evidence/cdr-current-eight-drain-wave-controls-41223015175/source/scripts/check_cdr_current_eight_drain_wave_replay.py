#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted-only source controls. Synthetic arrays/archives are not real capture replay."""
import argparse,ast,base64,copy,gzip,io,json,os,shutil,struct,tarfile,tempfile,traceback,zlib,unittest
from pathlib import Path
from unittest import mock
import cloud_cdr_current_eight_drain_wave_replay as r

def controls(root=r.ROOT):
    c=r.source_guard(root);refusals=[];completed=[];lifecycle=[]
    def function_bytes(path,name):
        text=r.regular(root,path).read_text()
        found=[n for n in ast.parse(text).body if isinstance(n,ast.FunctionDef)and n.name==name]
        assert len(found)==1
        node=found[0]
        return "".join(text.splitlines(keepends=True)[node.lineno-1:node.end_lineno]).encode()
    for name in ("checked_path","release_binding","reservation","acquire","select_archive"):
        assert function_bytes("scripts/cloud_cdr_current_eight_drain_wave_replay.py",name)==function_bytes("scripts/cloud_cdr_width_nominal_contacts.py",name)
    def refuse(name,call):
        try:call()
        except (AssertionError,ValueError,KeyError,OSError,RuntimeError) as error:
            refusals.append(dict(name=name,type=type(error).__name__,message=str(error)));return
        raise AssertionError("did not refuse: "+name)
    def record(name):completed.append(name)
    def put(path,raw):
        path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
    with tempfile.TemporaryDirectory(prefix="cdr-wave-controls-") as td:
        work=Path(td);project=work/"project";project.mkdir()
        for name in [r.CONFIG,*r.NEW_SOURCES,*c["required_files"]]:
            put(project/name,r.regular(root,name).read_bytes())
        assert r.source_guard(project)==c
        original=(project/r.CONFIG).read_bytes()
        put(project/r.CONFIG,original+b" ")
        refuse("source_tamper",lambda:r.source_guard(project))
        put(project/r.CONFIG,original)
        helper="scripts/cdr_v59_headroom_rows.py";saved=(project/helper).read_bytes();(project/helper).unlink()
        refuse("missing_helper",lambda:r.source_guard(project));put(project/helper,saved)
        env=dict(GITHUB_ACTIONS="true",GITHUB_EVENT_NAME="workflow_dispatch",GITHUB_REPOSITORY=r.REPOSITORY,GITHUB_REF="refs/heads/"+r.BRANCH,GITHUB_RUN_ATTEMPT="1",GITHUB_RUN_ID="123",GITHUB_SHA="a"*40)
        ctx=r.context(env,"nominal_early")
        refuse("context_branch",lambda:r.context(dict(env,GITHUB_REF="refs/heads/main")))
        refuse("attempt",lambda:r.context(dict(env,GITHUB_RUN_ATTEMPT="2")))
        disabled=copy.deepcopy(c);disabled.update(source_controls_authorized=True,readback_authorized=False)
        refuse("disabled_readback",lambda:r.perform(ctx,{},b"{}",work/"disabled",disabled,project))
        record("source")
        reports={}
        for case in r.CASES:
            _,_,reports[case]=r.metadata(c,case,project)
        assert reports["nominal_late"]["data_passed"] is False and reports["nominal_late"]["devices_passed"] is False and reports["nominal_late"]["vi"]["passed"] is False
        assert reports["nominal_early"]["devices_passed"] is False
        case="nominal_early";e=c["cases"][case]
        def changed(name,path,change):
            raw=(project/path).read_bytes();obj=r.decode(raw);change(obj)
            value=r.encode(obj);cp=copy.deepcopy(c);cp["required_files"][path]=r.fingerprint(value)
            put(project/path,value)
            try:refuse(name,lambda:r.metadata(cp,case,project))
            finally:put(project/path,raw)
        changed("wrong_case",e["report_path"],lambda x:x.update(case="constant_one"))
        changed("wrong_source",e["report_path"],lambda x:x.update(source_head="b"*40))
        changed("wrong_native_status",e["report_path"],lambda x:x.update(status="PASS"))
        changed("raw_summary_swap",e["report_path"],lambda x:(x.clear(),x.update(r.decode(r.pinned(c,project,e["summary_path"])))))
        changed("missing_member",e["map_path"],lambda x:x.pop(e["wave_member"]))
        changed("parts_duplicate",e["parts_path"],lambda x:x["parts"].__setitem__(1,copy.deepcopy(x["parts"][0])))
        changed("parts_missing",e["parts_path"],lambda x:x["parts"].pop())
        changed("parts_digest",e["parts_path"],lambda x:x["parts"][0].update(sha256="0"*64))
        changed("vectors_missing",e["report_path"],lambda x:x["vectors"].pop())
        changed("vectors_duplicate",e["report_path"],lambda x:x["vectors"].__setitem__(1,x["vectors"][0]))
        changed("vector_order",e["report_path"],lambda x:x["raw_capture"]["logical_vector_order"].reverse())
        changed("wrong_lineage",e["report_path"],lambda x:x["composition_source"].update(run=40830441311))
        record("metadata")
        run=r.decode(r.pinned(c,project,c["run_path"]));jobs=r.decode(r.pinned(c,project,c["jobs_path"]))
        rel=r.decode(r.pinned(c,project,e["release_path"]));ref=r.decode(r.pinned(c,project,e["ref_path"]))
        r.validate_current_case_live(c,case,run,jobs,rel,ref)
        for name,target,key,value in [("live_source","run","head_sha","0"*40),("live_release","release","id",1),("live_ref","ref","ref","refs/tags/wrong")]:
            objects={"run":copy.deepcopy(run),"jobs":copy.deepcopy(jobs),"release":copy.deepcopy(rel),"ref":copy.deepcopy(ref)}
            objects[target][key]=value
            refuse(name,lambda o=objects:r.validate_current_case_live(c,case,o["run"],o["jobs"],o["release"],o["ref"]))
        badjobs=copy.deepcopy(jobs);badjobs["jobs"][0]["conclusion"]="failure"
        refuse("live_job",lambda:r.validate_current_case_live(c,case,run,badjobs,rel,ref))
        tag="cloud-results-"+ctx["token"]+"-"+ctx["group"]
        fresh=dict(id=987,tag_name=tag,target_commitish=ctx["source"],prerelease=True,draft=False,assets=[])
        freshref=dict(ref="refs/tags/"+tag,object=dict(type="commit",sha=ctx["source"]))
        reserved=dict(tag=tag,tested_source=ctx["source"],release_id=987,target_verified=True,assets_overwritten=False,externally_reserved=True,creation_attempted=False,existing_assets=[])
        r.reservation(ctx,reserved,fresh,freshref)
        refuse("reservation_assets",lambda:r.reservation(ctx,reserved,dict(fresh,assets=[dict(id=1,name="already",size=1)]),freshref))
        refuse("reservation_source",lambda:r.reservation(ctx,dict(reserved,tested_source="0"*40),fresh,freshref))
        record("live")
        # Current adapter admits a terminal case while other immutable matrix jobs run.
        for status,conclusion in [('queued',None),('in_progress',None),('completed','failure')]:
            rr=dict(run,status=status,conclusion=conclusion)
            got=r.validate_current_case_live(c,case,rr,jobs,rel,ref)
            assert got['case_terminal_scope'] is True and got['whole_matrix_complete']==(status=='completed')
        active=copy.deepcopy(jobs)
        protected={x['id']for x in c['prerequisite_jobs']}|{e['job_id']}
        for j in active['jobs']:
            if j['id']not in protected:j.update(status='in_progress',conclusion=None)
        r.validate_current_case_live(c,case,dict(run,status='in_progress',conclusion=None),active,rel,ref)
        extra=dict(id=1,name=c['optional_finalizer_job_name'],run_id=c['producer']['run_id'],head_sha=c['producer']['source'],run_attempt=1,status='queued',conclusion=None,steps=[])
        finalizing=copy.deepcopy(jobs);finalizing['jobs'].append(extra);finalizing['total_count']+=1
        r.validate_current_case_live(c,case,run,finalizing,rel,ref)
        def live_mutation(name,target,change):
            objects={'run':copy.deepcopy(run),'jobs':copy.deepcopy(jobs),'release':copy.deepcopy(rel),'ref':copy.deepcopy(ref)}
            change(objects[target])
            refuse(name,lambda:r.validate_current_case_live(c,case,objects['run'],objects['jobs'],objects['release'],objects['ref']))
        def case_job(obj):return next(x for x in obj['jobs']if x['id']==e['job_id'])
        for name,key,value in [('current_run_id','id',1),('current_run_attempt','run_attempt',2),('current_workflow_id','workflow_id',1),('current_branch','head_branch','main'),('current_workflow_path','path','wrong'),('current_run_event','event','push'),('current_run_success','conclusion','success')]:
            live_mutation(name,'run',lambda x,key=key,value=value:x.update({key:value},**({'status':'completed'}if key=='conclusion'else{})))
        live_mutation('current_job_attempt','jobs',lambda x:case_job(x).update(run_attempt=2))
        live_mutation('current_case_incomplete','jobs',lambda x:case_job(x).update(status='in_progress',conclusion=None))
        live_mutation('current_case_success','jobs',lambda x:case_job(x).update(conclusion='success'))
        live_mutation('current_case_step','jobs',lambda x:case_job(x)['steps'][0].update(conclusion='failure'))
        live_mutation('current_case_missing_step','jobs',lambda x:case_job(x)['steps'].pop())
        live_mutation('current_jobs_duplicate','jobs',lambda x:x['jobs'].append(copy.deepcopy(x['jobs'][0])))
        live_mutation('current_jobs_missing_case','jobs',lambda x:x['jobs'].remove(case_job(x)))
        live_mutation('current_jobs_count','jobs',lambda x:x.update(total_count=x['total_count']-1))
        live_mutation('current_unexpected_job','jobs',lambda x:(x['jobs'].append(dict(extra,name='unexpected')),x.update(total_count=x['total_count']+1)))
        live_mutation('current_release_missing_asset','release',lambda x:x['assets'].pop())
        live_mutation('current_release_extra_asset','release',lambda x:x['assets'].append(dict(id=1,name='unexpected',state='uploaded',size=1,digest='sha256:'+'0'*64)))
        for suffix,key,value in [('digest','digest','sha256:'+'0'*64),('size','size',1),('id','id',1),('state','state','new')]:
            live_mutation('current_asset_'+suffix,'release',lambda x,key=key,value=value:x['assets'][0].update({key:value}))
        live_mutation('current_tag_source','ref',lambda x:x['object'].update(sha='0'*40))
        pub=r.decode(r.pinned(c,project,e['publication_path']))
        summary,parts,_=r.metadata(c,case,project)
        assert r.validate_original_publication(c,case,summary,parts,pub)['complete'] is True
        def pub_mutation(name,change):
            value=copy.deepcopy(pub);change(value)
            refuse(name,lambda:r.validate_original_publication(c,case,summary,parts,value))
        for name,key,value in [('publication_incomplete','status','RUNNING'),('publication_accepted','accepted',True),('publication_qualified','publication_qualified_as_success',True),('publication_source_integrity','source_integrity_qualified',False),('publication_raw_changed','raw_terminal_bytes_unchanged',False),('publication_wave_removed','waveform_samples_deliberately_removed',True),('publication_plan','direct_plan_sha256','0'*64),('publication_original_status','original_status','PASS')]:
            pub_mutation(name,lambda x,key=key,value=value:x.update({key:value}))
        pub_mutation('publication_source',lambda x:x['current_context'].update(source='0'*40))
        pub_mutation('publication_attempt',lambda x:x['current_context'].update(attempt=2))
        pub_mutation('publication_inventory',lambda x:x['complete_outputs'].pop(e['wave_member']))
        pub_mutation('publication_assets_missing',lambda x:x['assets'].pop())
        pub_mutation('publication_assets_duplicate',lambda x:x['assets'].append(copy.deepcopy(x['assets'][0])))
        pub_mutation('publication_assets_digest',lambda x:x['assets'][0].update(sha256='0'*64))
        pub_mutation('publication_reservation_source',lambda x:x['reservation'].update(tested_source='0'*40))
        pub_mutation('publication_reservation_clobber',lambda x:x['reservation'].update(assets_overwritten=True))
        record('current_case_provenance')
        def archive(path,rows):
            with tarfile.open(path,"w:gz") as tar:
                for name,data,kind in rows:
                    info=tarfile.TarInfo("box/"+name)
                    if kind=="link":info.type=tarfile.SYMTYPE;info.linkname="/etc/passwd";tar.addfile(info)
                    else:info.size=len(data);tar.addfile(info,io.BytesIO(data))
        base=[("a",b"alpha","file"),("b",b"","file")]
        expected={n:r.fingerprint(b)["sha256"] for n,b,_ in base}
        good=work/"good.tar.gz";archive(good,base)
        observed=r.select_archive(good,expected,["a"],"box",work/"selected")
        assert observed["full_member_count"]==2 and (work/"selected/a").read_bytes()==b"alpha" and observed["full_members"]["b"]["bytes"]==0
        variants={"archive_missing":base[:1],"archive_extra":base+[("c",b"extra","file")],"archive_duplicate":base+[base[0]],"archive_traversal":[("../escape",b"x","file")],"archive_link":[("a",b"","link"),base[1]],"archive_corruption":[("a",b"changed","file"),base[1]]}
        for name,items in variants.items():
            p=work/(name+".gz");archive(p,items)
            refuse(name,lambda p=p,name=name:r.select_archive(p,expected,["a"],"box",work/name))
        raw=b"synthetic part";h=r.fingerprint(raw)["sha256"]
        cp={"cases":{"synthetic":{"assets":{"part0":dict(id=1,bytes=len(raw),sha256=h)}}}}
        parts=dict(parts=[dict(index=0,name="part0",bytes=len(raw),sha256=h)],bytes=len(raw),sha256=h)
        for good_transport in (True,False):
            target=work/("transport-good"if good_transport else"transport-bad");target.mkdir()
            def fetch(pin,path,good_transport=good_transport):path.write_bytes(raw if good_transport else b"corrupt")
            if good_transport:assert r.acquire(cp,"synthetic",parts,target,fetch)[1]["sha256"]==h
            else:refuse("part_transport_corruption",lambda:r.acquire(cp,"synthetic",parts,target,fetch))
        record("archives")
        numeric=r.load_numeric(c,root);np=r.np
        names=["v(a)","v(b)"];times=[0.,1e-12,2e-12]
        def raw_file(path,ts=times,order=names,kind="voltage",extra=b"",truncate=0,nan=False):
            header="Title: synthetic\nDate: synthetic\nPlotname: Transient Analysis\nFlags: real\nNo. Variables: 3\nNo. Points: 3\nVariables:\n0 time time\n1 "+order[0]+" "+kind+"\n2 "+order[1]+" voltage\nBinary:\n"
            body=b"".join(struct.pack("<ddd",t,(float("nan") if nan else 1.),2.)for t in ts)
            data=header.encode()+body+extra
            if truncate:data=data[:-truncate]
            path.write_bytes(data)
        p=work/"synthetic.raw";raw_file(p)
        t,d,capture=numeric.read(p,names,2e-12,1e-12)
        assert t.tolist()==times and d["v(a)"].tolist()==[1.,1.,1.] and capture["header_rows"]==3
        raw_variants={"raw_truncated":dict(truncate=1),"raw_extra":dict(extra=b"x"),"raw_nonfinite":dict(nan=True),"raw_backward":dict(ts=[0.,2e-12,1e-12]),"raw_duplicate_time":dict(ts=[0.,0.,2e-12]),"raw_vector_missing":dict(order=["v(a)","v(unknown)"]),"raw_vector_duplicate":dict(order=["v(a)","v(a)"]),"raw_wrong_kind":dict(kind="current")}
        for name,kwargs in raw_variants.items():
            q=work/(name+".raw");raw_file(q,**kwargs)
            refuse(name,lambda q=q:numeric.read(q,names,2e-12,1e-12))
        q=work/"raw_order.raw";raw_file(q,order=list(reversed(names)))
        _,_,changed_capture=numeric.read(q,names,2e-12,1e-12)
        refuse("raw_wrong_order",lambda:r.capture_binding(changed_capture,dict(raw_capture=capture)))
        record("raw")
        import check_cdr_current_sampler_witness as sampler_controls
        assert Path(sampler_controls.__file__).resolve()==r.regular(root,'scripts/check_cdr_current_sampler_witness.py').resolve()
        suite=unittest.defaultTestLoader.loadTestsFromModule(sampler_controls)
        assert suite.countTestCases()==6
        sampler_output=io.StringIO()
        sampler_result=unittest.TextTestRunner(stream=sampler_output,verbosity=2).run(suite)
        assert sampler_result.wasSuccessful() and sampler_result.testsRun==6,sampler_output.getvalue()
        record('sampler_witness')
        contract=r.decode(r.pinned(c,project,c["composition"]["path"]))
        planes=r.decode(r.pinned(c,project,c["planes_path"]))
        report=reports["nominal_late"]
        # Exact current500 cards; synthetic inert R/C filler only. No simulator.
        cards=[".subckt nssoc_cdr_pd500_resistor_mim_wire_v59 "+" ".join(contract["interface"])]
        for dev in contract["device_records"]:
            cards.append(" ".join([dev["instance"],*[t["node"]for t in dev["terminals"]],dev["model"],*[k+"="+v for k,v in dev["parameters"].items()]]))
        cards.extend("Rsynthetic"+str(i)+" a b 1"for i in range(contract["counts"]["R"]))
        cards.extend("Csynthetic"+str(i)+" a b 1p"for i in range(contract["counts"]["C"]))
        cards.append(".ends nssoc_cdr_pd500_resistor_mim_wire_v59")
        model="\n".join(cards)+"\n"
        assert r.validate_binding(numeric,report,contract,planes,model)==report["binding"]
        bad=copy.deepcopy(contract);next(x for x in bad["device_records"]if x["native_id"]==61)["terminals"][0]["node"]="wrong"
        refuse("binding_terminal",lambda:r.validate_binding(numeric,report,bad,planes,model))
        bad=copy.deepcopy(contract);next(x for x in bad["device_records"]if x["native_id"]==279)["terminals"][0]["native_cluster"]=229
        refuse("binding_filter",lambda:r.validate_binding(numeric,report,bad,planes,model))
        t=np.linspace(0,numeric.rows.STOP,900);d={n:np.zeros(len(t))for n in report["vectors"]}
        for name,dev in report["devices"].items():
            for node,value in zip(dev["nodes"][:3],[.8,.7,.2],strict=True):d["v("+node+")"][:]=value
            d["@q."+name+".qnpn13g2[ic]"][:]=.0002
        for name,dev in report["mos_devices"].items():
            for node,value in zip(dev["nodes"][:3],[.2,.8,0.],strict=True):d["v("+node+")"][:]=value
            d["@n."+name+".nsg13_lv_nmos[ids]"][:]=.0002
        d["v(vip)"][:]=.004;d["v(vin)"][:]=0.
        for ident,value in [(167,.00011),(172,.00011),(168,.00010),(171,.00010)]:
            d["@q.xpd.xd"+str(ident).zfill(4)+".qnpn13g2[ic]"][:]=value
        actual=numeric.replay(t,d,{},report["binding"],[1]*256,report["data_offset_s"],True,report["devices"],report["mos_devices"],report["native_caps"])
        assert abs(actual["vi"]["mean_signed_current_a"]-2e-5)<1e-18
        assert abs(actual["vi"]["mean_output_difference_v"]-.004)<1e-15
        assert actual["vi"]["phase_passed"] is False and actual["vi"]["bias_passed"] is True
        assert abs(actual["device_checks"]["xpd.xd0061"]["minimum_active_vce_v"]-.6)<1e-15
        synthetic=dict(copy.deepcopy(actual),status="REJECTED_WHOLE_MIM_PD500_LOADED")
        r.compare_replay(actual,synthetic)
        bad=copy.deepcopy(synthetic);bad["device_checks"]["xpd.xd0061"]["minimum_active_vce_v"]+=.01
        refuse("scalar_HBT",lambda:r.compare_replay(actual,bad))
        bad=copy.deepcopy(synthetic);bad["vi"]["mean_output_difference_v"]+=.001
        refuse("scalar_VI",lambda:r.compare_replay(actual,bad))
        refuse("scalar_status",lambda:r.compare_replay(actual,dict(synthetic,status="PASS")))
        false_accept=copy.deepcopy(actual);false_accept["devices_passed"]=True;false_accept["data_passed"]=True;false_accept["vi"]["passed"]=True
        refuse("scalar_original_rejection",lambda:r.compare_replay(false_accept,dict(false_accept,status="REJECTED_WHOLE_MIM_PD500_LOADED")))
        record("binding_scalar")
        t=np.array(times);d={"v(a)":np.array([1.,2.,3.]),"v(b)":np.array([4.,5.,6.])};series={"difference_v":d["v(a)"]-d["v(b)"]}
        row_out=work/"row-output";row_out.mkdir()
        full=r.write_full_rows(row_out/"rows.jsonl.gz",t,d,names,series)
        with gzip.open(row_out/"rows.jsonl.gz","rt")as f:rows=[json.loads(x)for x in f]
        assert full["rows"]==3 and len(rows)==4 and rows[3]["index"]==2 and rows[3]["values"]==[3.,6.] and rows[3]["derived"]==[-3.]
        refuse("rows_missing_vector",lambda:r.write_full_rows(work/"missing-rows.gz",t,d,["v(absent)"],series))
        refuse("rows_length_mismatch",lambda:r.write_full_rows(work/"bad-length.gz",t,{"v(a)":np.array([1.])},["v(a)"],{}))
        r.write_new(row_out/"empty.stderr",b"");r.write_new(row_out/"small.json",b'{"kept":true}\n')
        emission=[];r.emit(row_out,writer=lambda text,**kwargs:emission.append(text))
        index=json.loads(next(x.split(" ",1)[1]for x in emission if x.startswith("CDR_DRAIN_REPLAY_INDEX ")))
        assert index["rows.jsonl.gz"]==r.file_pin(row_out/"rows.jsonl.gz")
        assert any(x.startswith("CDR_DRAIN_REPLAY_EXTERNAL_COMPLETE_FILE ")and'"rows.jsonl.gz"'in x for x in emission)
        assert not any(x.startswith("CDR_DRAIN_REPLAY_CHUNK ")and'"rows.jsonl.gz"'in x for x in emission)
        assert index["empty.stderr"]==r.fingerprint(b"")
        chunks=[json.loads(x.split(" ",1)[1]) for x in emission if x.startswith("CDR_DRAIN_REPLAY_CHUNK ")]
        for filename,raw in [("empty.stderr",b""),("small.json",b'{"kept":true}\n')]:
            payload=b"".join(base64.b64decode(x["data"]) for x in chunks if x["name"]==filename)
            assert zlib.decompress(payload)==raw
        record("full_rows")
        primary=ValueError("synthetic primary");secondary=RuntimeError("synthetic emission")
        out=work/"source-failure"
        put(project/helper,saved+b"\\n# synthetic source corruption\\n")
        with mock.patch.object(r,"emit",return_value={}):
            try:r.run(ctx,reserved,b"{}",out,project)
            except AssertionError as caught:assert str(caught)=="source/input bytes: "+helper
            else:raise AssertionError("source failure lost")
        assert r.decode((out/"readback-failure.json").read_bytes())["error"]["message"]=="source/input bytes: "+helper
        assert (out/"retained-input"/helper).read_bytes()==(project/helper).read_bytes()
        put(project/helper,saved)
        assert (out/"retained-source"/r.CONFIG).read_bytes()==r.regular(project,r.CONFIG).read_bytes()
        lifecycle.append("source_failure_preserved")
        out=work/"partial-failure"
        def partial(*args,**kwargs):
            r.write_new(args[3]/"partial.json",b'{"complete":false}\n')
            r.write_new(args[3]/"empty.stderr",b"")
            raise primary
        with mock.patch.object(r,"perform",side_effect=partial),mock.patch.object(r,"emit",side_effect=secondary):
            try:r.run(ctx,reserved,b"{}",out,project)
            except ValueError as caught:assert caught is primary
            else:raise AssertionError("primary lost to emission")
        assert (out/"partial.json").is_file()and (out/"empty.stderr").stat().st_size==0
        assert r.decode((out/"emission-error.json").read_bytes())["primary_error"]["message"]=="synthetic primary"
        lifecycle.append("primary_and_partial_emission")
        out=work/"cleanup-failure";out.mkdir()
        cp=copy.deepcopy(c);cp.update(source_controls_authorized=True,readback_authorized=True)
        proof=dict(status="PASS_CURRENT_EIGHT_DRAIN_WAVE_REPLAY_SOURCE_CONTROLS",passed=True,current_context=dict(source=ctx["source"],run_id=ctx["run_id"],attempt=1,source_controls_only=True,native_executed=False),native_executed=False,physical_acceptance=False,actual_capture_replayed=False,sampler_test_methods=6,completed_groups=r.SOURCE_GROUPS,failures=[],counts=r.SOURCE_COUNTS)
        class Temp:
            name=str(work/"temp-owned")
            def cleanup(self):raise RuntimeError("synthetic cleanup")
        Path(Temp.name).mkdir()
        def api(endpoint):
            if endpoint=="releases/tags/"+tag:return fresh
            if endpoint=="git/ref/tags/"+tag:return freshref
            if endpoint.startswith("actions/runs/")and"/jobs?"in endpoint:return jobs
            if endpoint.startswith("actions/runs/"):return run
            if endpoint.startswith("releases/"):return rel
            return ref
        with mock.patch.object(r,"checkout_binding",return_value={}),mock.patch.object(r.tempfile,"TemporaryDirectory",return_value=Temp()),mock.patch.object(r,"acquire",side_effect=primary),mock.patch.object(r.shutil,"disk_usage",return_value=mock.Mock(free=64*1024**3)):
            try:r.perform(ctx,reserved,r.encode(proof),out,cp,project,api)
            except ValueError as caught:assert caught is primary
            else:raise AssertionError("cleanup replaced transport refusal")
        saved=r.decode((out/"cleanup-error.json").read_bytes())
        assert saved["primary_error"]["message"]=="synthetic primary"and saved["error"]["message"]=="synthetic cleanup"
        lifecycle.append("transport_primary_over_cleanup")
        out=work/"no-clobber";out.mkdir();(out/"sentinel").write_bytes(b"keep")
        try:r.run(ctx,reserved,b"{}",out,project)
        except AssertionError as error:assert str(error)=="output no overwrite"
        else:raise AssertionError("overwrote output")
        assert (out/"sentinel").read_bytes()==b"keep"
        lifecycle.append("owned_output_no_clobber")
        record("lifecycle")
    assert completed==r.SOURCE_GROUPS
    assert sorted(x["name"]for x in refusals)==sorted(r.SOURCE_REFUSALS)
    assert len({x["name"]for x in refusals})==len(refusals)==86
    assert len(lifecycle)==4
    return dict(status="PASS_CURRENT_EIGHT_DRAIN_WAVE_REPLAY_SOURCE_CONTROLS",passed=True,completed_groups=completed,counts=dict(groups=len(completed),refusals=len(refusals),lifecycle=len(lifecycle)),refusals=refusals,lifecycle=lifecycle,sampler_test_methods=sampler_result.testsRun,sampler_test_output=sampler_output.getvalue(),failures=[],native_executed=False,physical_acceptance=False,actual_capture_replayed=False,synthetic_numeric_arrays_executed=True,synthetic_archives_only=True,unchanged_archive_functions=["checked_path","release_binding","reservation","acquire","select_archive"],original_measurement_block_sha256=c["measurement_block"]["sha256"])

def main():
    parser=argparse.ArgumentParser();parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args();ctx=r.context(os.environ);result=None;primary=None
    try:
        c=r.source_guard();r.checkout_binding(ctx,c)
        r.require(c["source_controls_authorized"] is True,"source controls disabled")
        result=controls()
        result["current_context"]=dict(source=ctx["source"],run_id=ctx["run_id"],attempt=1,source_controls_only=True,native_executed=False)
    except BaseException as error:
        primary=error
        result=dict(status="FAIL_CURRENT_EIGHT_DRAIN_WAVE_REPLAY_SOURCE_CONTROLS",passed=False,error=repr(error),traceback=traceback.format_exc(),native_executed=False,physical_acceptance=False,actual_capture_replayed=False)
    try:r.write_new(args.output,r.encode(result))
    except BaseException as error:
        print(r.encode(dict(result,publication_error=repr(error))).decode(),flush=True)
        if primary is None:raise
    else:print(r.encode(result).decode(),flush=True)
    if primary is not None:raise primary

if __name__=="__main__":main()
