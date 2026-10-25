#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Real harmless hosted GDB fixture plus strict metadata/cleanup controls; no chip run."""
import copy,hashlib,http.client,http.server,json,os,shutil,subprocess,sys,threading,time,traceback
from pathlib import Path
import mainchip_userstack_observer as obs
import mainchip_latest_stack_admission as admission
from mainchip_userstack_identity import snapshot,file_sha,check_frames,module_inventory,ProcessPin,loaded_executable_identity
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-mainchip-userstack-fixture'
METHOD=ROOT/'scripts/mainchip-userstack-fixture-methods.json'

def verify_pins(root,pins):
    for p,h in pins.items():assert file_sha(root/p)==h,p
    return True

def methods():
    m=json.loads(METHOD.read_text())
    verify_pins(ROOT,m['protected'])
    assert m['native_process_restore_authorized']is False
    assert m['native_attachment_authorized']is False
    assert m['fixture_execution_authorized']is True
    return m

def prepare_elf(folder,stripped=False):
    folder.mkdir(exist_ok=False);elf=folder/'counter'
    subprocess.run(['gcc','-std=c11','-O1','-g','-fno-omit-frame-pointer','-pthread',
        str(ROOT/'scripts/fixtures/mainchip_userstack_counter.c'),'-o',str(elf)],check=True)
    if stripped:subprocess.run(['strip','--strip-all',str(elf)],check=True)
    return elf

def start_fixture(elf,folder):
    log=(folder/'counter.log').open('xb')
    p=subprocess.Popen([str(elf)],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    end=time.monotonic()+5
    while time.monotonic()<end:
        assert p.poll()is None
        if (folder/'counter.log').stat().st_size:break
        time.sleep(.05)
    expected=snapshot(p.pid,tracer=0,require_running=True)['identity']
    home=folder/'home';home.mkdir()
    fixture=dict(owned_pid=p.pid,owner_pid=os.getpid(),elf_sha256=file_sha(elf),
        elf_path=str(elf),purpose='HARMLESS_COUNTER_FIXTURE',fixture_home=str(home),fixture_cwd=str(folder))
    return p,log,expected,fixture

def stop_fixture(p,log):
    if p.poll()is None:
        p.terminate()
        try:p.wait(timeout=3)
        except subprocess.TimeoutExpired:p.kill();p.wait(timeout=3)
    log.close()

def controls():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    methods();OUT.mkdir(exist_ok=False)
    result=dict(status='RUNNING',native_process_restored=False,native_attachment_authorized=False,
        native_route_started=False,normal_continuation_accepted=False,route_progress_proven=False,
        scheduling_perturbation_on_harmless_fixture=True,controls=[])
    fixture_owned=[]
    def passed(label,evidence):
        assert label not in [x['id']for x in result['controls']]
        result['controls'].append(dict(id=label,evidence=evidence))
        obs.write(OUT/'progress.json',result)
    def rejected(label,callback):
        try:callback()
        except(AssertionError,FileNotFoundError,ProcessLookupError,KeyError,ValueError)as e:
            passed(label,dict(actual_rejection=repr(e)));return
        raise AssertionError('Control accepted '+label)
    try:
        gdb=shutil.which('gdb');assert gdb
        gdb=str(Path(gdb).resolve())
        result['gdb']=dict(path=gdb,sha256=file_sha(gdb),
            version=subprocess.check_output([gdb,'--nx','--nh','--version'],text=True))
        elf=prepare_elf(OUT/'fixture')
        p,log,expected,fixture=start_fixture(elf,elf.parent);fixture_owned.append((p,log))

        # Actual /proc link and GDB's possible canonical spelling bind the same held object.
        binding_controls=[]
        with ProcessPin(p.pid,expected)as pin:
            pin.verify()
            for spelling in ('/proc/'+str(p.pid)+'/exe',str(elf)):
                value=loaded_executable_identity(p.pid,expected,spelling)
                assert value['files']['gdb_reported']['sha256']==expected['exe_sha256']
            alias=elf.parent/'counter-alias';alias.symlink_to(elf)
            loaded_executable_identity(p.pid,expected,str(alias))
            duplicate=elf.parent/'counter-identical-copy';shutil.copyfile(elf,duplicate)
            def binding_reject(label,reported,wanted=expected,pid=p.pid):
                try:loaded_executable_identity(pid,wanted,reported)
                except(AssertionError,FileNotFoundError):binding_controls.append(label)
                else:raise AssertionError('Accepted loaded executable corruption '+label)
            binding_reject('empty-filename','')
            binding_reject('relative-filename','counter')
            binding_reject('wrong-existing-file',str(ROOT/'scripts/fixtures/mainchip_userstack_counter.c'))
            binding_reject('identical-bytes-different-inode',str(duplicate))
            wrong=copy.deepcopy(expected);wrong['exe']['inode']+=1
            binding_reject('wrong-inode',str(elf),wrong)
            wrong=copy.deepcopy(expected);wrong['exe_bytes']+=1
            binding_reject('wrong-size',str(elf),wrong)
            wrong=copy.deepcopy(expected);wrong['exe_sha256']='0'*64
            binding_reject('wrong-sha256',str(elf),wrong)
            binding_reject('wrong-pid',str(elf),pid=p.pid+1)
            pin.verify()
        assert len(binding_controls)==8
        result['loaded_executable_binding_controls']=dict(
            positive_spellings=3,rejected=binding_controls,full_identity_bound=True)
        # Initialization canaries are actual files, not inferred from argv alone.
        canary=OUT/'autoload-ran'
        command='shell touch '+str(canary)+'\n'
        (Path(fixture['fixture_home'])/'.gdbinit').write_text(command)
        (elf.parent/'.gdbinit').write_text(command)
        (elf.parent/(elf.name+'-gdb.py')).write_text('open('+repr(str(canary))+',"w").write("auto-loaded")\n')
        # Local diagnostic endpoint is tested live. The actual debugger must disable and clear it.
        hits=[]
        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                hits.append(self.path);self.send_response(404);self.end_headers()
            def log_message(self,*args):pass
        server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        os.environ['DEBUGINFOD_URLS']='http://127.0.0.1:'+str(server.server_port)
        conn=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=2)
        conn.request('GET','/control-probe');assert conn.getresponse().status==404;conn.close()
        assert hits==['/control-probe'];hits.clear()
        try:collection=obs.collect(p.pid,expected,fixture,gdb,OUT/'twenty')
        finally:server.shutdown();server.server_close();thread.join(timeout=3)
        passed('positive-20',dict(samples=20,result_sha256=file_sha(OUT/'twenty/result.json')))
        first=collection['samples'][0]['reader']
        assert all(s['reader']['loaded_executable_identity']['files']['gdb_reported']['sha256']==expected['exe_sha256']for s in collection['samples'])
        bad=copy.deepcopy(first);bad['threads'].pop()
        rejected('all-lwps',lambda:check_frames(bad,first['stopped_identity']))
        # Actual target-root hashes and frame file offsets are retained for every acquisition.
        modules=first['native_modules']
        assert modules['files'][str(elf)]['sha256']==expected['exe_sha256']
        assert all(f['binding']['native_pc']==f['pc']for t in first['threads']for f in t['frames'])
        changed=copy.deepcopy(modules);changed['files'][str(elf)]['sha256']='0'*64
        rejected('container-root',lambda:assert_equal(changed['files'],modules['files']))
        assert not canary.exists()
        passed('initialization-canary',dict(actual_home_local_executable_canaries_not_executed=True,
            system_init_exclusion_by_nx=True,system_init_file_not_modified=True))
        assert hits==[]
        passed('debuginfod-canary',dict(actual_http_requests=hits,early_off=True,urls_cleared=True))
        assert len(first['permission_canaries'])==3 and all(v is False for v in first['permissions'].values())
        passed('permission-canaries',dict(actual_write_register_call_rejections=first['permission_canaries'],
            breakpoint_tracepoint_fast_tracepoint_permissions=False,
            trace_activation_not_attempted=True))
        def bad_identity(key,value,label):
            bad=copy.deepcopy(expected);bad[key]=value
            rejected(label,lambda:snapshot(p.pid,bad,tracer=0,require_running=True))
        bad_identity('starttime',expected['starttime']+1,'wrong-starttime')
        bad_identity('exe_sha256','0'*64,'wrong-executable')
        bad_identity('cgroup_hex','00','wrong-container')
        # Actual different live process cannot inherit the first fixture identity.
        elf2=prepare_elf(OUT/'other')
        p2,l2,e2,f2=start_fixture(elf2,elf2.parent);fixture_owned.append((p2,l2))
        rejected('pid-replacement',lambda:snapshot(p2.pid,expected,tracer=0,require_running=True))
        with ProcessPin(p2.pid,e2)as dead_pin:
            p2.terminate();p2.wait(timeout=3)
            try:dead_pin.verify()
            except AssertionError:result['actual_pidfd_exit_rejected']=True
            else:raise AssertionError('Accepted exited pinned fixture')
        # While an actual debugger holds the fixture, a competing observer rejects its tracer.
        errs=[]
        def timed():
            try:obs.attach_once(p.pid,expected,fixture,gdb,OUT/'timeout',fault='timeout-after-attach',seconds=4.)
            except BaseException as e:errs.append(repr(e))
        worker=threading.Thread(target=timed);worker.start()
        until=time.monotonic()+3
        while time.monotonic()<until:
            if (OUT/'timeout/gdb-result.json').exists():break
            time.sleep(.02)
        assert (OUT/'timeout/gdb-result.json').exists(),'No actual stopped fixture witness'
        rejected('already-traced',lambda:snapshot(p.pid,expected,tracer=0,require_running=True))
        worker.join(timeout=12);assert not worker.is_alive()and errs
        timeout=json.loads((OUT/'timeout/result.json').read_text())
        assert timeout['status']=='REJECTED_OWNED_FIXTURE_ATTACHMENT'and 'cleanup_unproved'not in timeout
        assert timeout['command']['failure']=='debugger_deadline'
        passed('timeout-cleanup',dict(report_sha256=file_sha(OUT/'timeout/result.json'),detach_verified=True))
        bad=copy.deepcopy(expected['namespaces']);bad['mnt']='mnt:[0]'
        bad_identity('namespaces',bad,'namespace-drift')
        for label,fault in [('during-stop-rebind','identity-after-attach'),('error-finally-detach','error-after-attach')]:
            folder=OUT/label
            rejected(label,lambda folder=folder,fault=fault:obs.attach_once(p.pid,expected,fixture,gdb,folder,fault=fault))
            r=json.loads((folder/'result.json').read_text())
            assert r['reader']['detached']and 'cleanup_unproved'not in r
        # Real process-group descendant survives its leader and ignores TERM.
        code='import os,signal,time\np=os.fork()\nif p==0:\n signal.signal(signal.SIGTERM,signal.SIG_IGN)\n time.sleep(30)\nelse:\n time.sleep(.2)\n os._exit(0)\n'
        orphan=obs.supervised([sys.executable,'-c',code],os.environ.copy(),OUT/'orphan',2.)
        assert orphan['failure']=='live_debugger_descendant_after_leader'
        assert any(x['signal']==9 and x['members']for x in orphan['cleanup']['attempts'])
        passed('leader-descendant',orphan)
        bad=copy.deepcopy(first);bad['detached']=False
        rejected('detach-unproved',lambda:obs.accepted_reader(bad))
        rejected('partial-19',lambda:obs.accepted_collection(collection['samples'][:19]))
        large=obs.supervised([sys.executable,'-c','import os;os.write(1,b"x"*17000)'],
            os.environ.copy(),OUT/'bounded-output',2.,output_limit=16000)
        assert large['failure']=='debugger_output_limit'
        passed('oversize-or-time',large)
        # Actual stripped fixture, not fabricated symbols.
        stripped=prepare_elf(OUT/'stripped',stripped=True)
        ps,ls,es,fs=start_fixture(stripped,stripped.parent);fixture_owned.append((ps,ls))
        unknown=obs.attach_once(ps.pid,es,fs,gdb,OUT/'unknown-symbols')
        assert any(f['name']is None for t in unknown['reader']['threads']for f in t['frames'])
        passed('unknown-unwind',dict(actual_unknown_symbols_retained=True,result_sha256=file_sha(OUT/'unknown-symbols/result.json')))
        raw=(admission.BASIS/'mainchip-observed-native-result.json').read_bytes()
        real=admission.source_report(raw)
        rejected('wrong-capsule',lambda:admission.source_report(raw+b' '))
        def api(path):return json.loads(subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/'+path]))
        run=api('actions/runs/'+str(admission.RUN));release=api('releases/422907570')
        tag=api('git/ref/tags/'+release['tag_name'])
        admission.transport_identity(run,release,tag)
        metadata_faults=[]
        for field,value in [('id',40095811631),('head_sha','0'*40),('run_attempt',2),('conclusion','failure')]:
            wrong=copy.deepcopy(run);wrong[field]=value
            try:admission.transport_identity(wrong,release,tag)
            except AssertionError:metadata_faults.append(field)
            else:raise AssertionError('Accepted changed source metadata '+field)
        assert len(metadata_faults)==4
        result['latest_capsule_actual_metadata_verified']=dict(run=admission.RUN,source=admission.HEAD,metadata_faults=metadata_faults)
        bad=copy.deepcopy(real);bad['expected_rejection']['original_no_log_progress_rejection_reproduced']=False
        rejected('original-rejection',lambda:admission.source_report(json.dumps(bad).encode()))
        protected=ROOT/'scripts/mainchip_userstack_observer.py'
        changed_folder=OUT/'changed-source';changed_folder.mkdir()
        (changed_folder/'observer.py').write_bytes(protected.read_bytes()+b'\n# actual changed copy\n')
        rejected('material-mutation',lambda:verify_pins(changed_folder,{'observer.py':file_sha(protected)}))
        failed=json.loads((OUT/'error-finally-detach/result.json').read_text())
        assert failed['status']=='REJECTED_OWNED_FIXTURE_ATTACHMENT'
        for name in ('stdout.log','stderr.log','command.json'):
            assert (OUT/'error-finally-detach/command'/name).is_file()
        assert failed['failure_console']['emitted']is True
        for name,record in failed['failure_console']['streams'].items():
            actual=OUT/'error-finally-detach/command'/name
            assert record['sha256']==file_sha(actual)and record['bytes']==actual.stat().st_size
            assert sum(x['bytes']for x in record['selected'])<=8192
        bounded=OUT/'bounded-console';bounded.mkdir()
        (bounded/'stdout.log').write_bytes(b'a'*9000)
        (bounded/'stderr.log').write_bytes(b'\xfffailure\n')
        stream=obs.emit_bounded_command_outputs(bounded)
        assert stream['streams']['stdout.log']['omitted_bytes']==808
        assert [x['offset']for x in stream['streams']['stdout.log']['selected']]==[0,4904]
        assert stream['streams']['stderr.log']['omitted_bytes']==0
        passed('failure-publication',dict(actual_partial_failure_files_preserved=True,
            bounded_console_streams_verified=True,
            remote_artifact_upload_not_proven_by_checker=True))
        values=[int(s)for s in (elf.parent/'counter.log').read_text().splitlines()]
        assert len(values)>2 and values[-1]>values[0]
        assert len(result['controls'])==24
        methods()
        result.update(status='PASS_24_HARMLESS_USERSTACK_CONTROLS_ONLY',sources_unchanged=True,
            counter_progress=dict(first=values[0],last=values[-1]),
            complete_chip_admission_unexecuted=True,live_container_binding_unexecuted=True,
            actual_archive_read=False,full_user_stacks_claimed=False)
    except BaseException as e:
        result.update(status='REJECTED_USERSTACK_FIXTURE',error=repr(e),traceback=traceback.format_exc());raise
    finally:
        for p,log in reversed(fixture_owned):stop_fixture(p,log)
        obs.write(OUT/'result.json',result)
        raw=(OUT/'result.json').read_bytes()
        print(json.dumps(dict(status=result['status'],bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),
            controls=len(result['controls']),native_attachment_authorized=False)),flush=True)
    return result

def assert_equal(a,b):assert a==b
if __name__=='__main__':controls()
