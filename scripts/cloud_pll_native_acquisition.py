#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Original physical845 1us native trajectory across hosted process checkpoints.

Checkpointing changes elapsed host execution only. Never restart, interpolate,
concatenate captures, change TSTOP, or infer full PHY acceptance from these probes.
"""
import argparse,copy,hashlib,json,os,re,shutil,subprocess,tarfile,time
from pathlib import Path
import numpy as np
import cloud_native_checkpoint_probe as native
import cloud_native_portable_checkpoint as portable
import cloud_pll_vbic_acquisition as acquisition
import cloud_pll_filter_physical_acquisition as physical_pll
import cloud_tx_input_driver_localpins as restoration
import run_cloud_pll865_snapshot as pll
from cloud_vbic_tree32_backend import backend_readback,readback_controls
from cloud_chunked_results import verify_parts
from route_cloud_newer_postcts import fetch
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-pll-native-acquisition'
LIB=ROOT/'cloud-pll-snapshot'
CASE=OUT/'case'
BASE='https://github.com/Melihakbulut221/nssoc/releases/download/'
BOUNDED=dict(run=38904997140,group='native-portable-checkpoint',root='cloud-native-portable-checkpoint',bytes=59772311,sha='30bad1656b8c6f291d805b3161b8336825d7608c3a04355c57e10a6f8c0f7331',summary='5f261d535f386661979ef9854e26dead27b6ba1d4d681eed931d5c300faed176')
CROSS_SHA='fccc1d9f00d142f43013ac7900f80fb3daa26c9821d025b14cea6f9f43f343a0'
CHECKPOINT_STATUS='SAVED_ACTUAL_PHYSICAL845_ONE_US_PROCESS_NOT_FULL_CAPTURE_OR_ACCEPTANCE'
COMPLETE_STATUS='COMPLETE_ACTUAL_PHYSICAL845_ONE_US_NATIVE_CONTINUATION_NOT_PHY_ACCEPTANCE'
MARKER=b'Binary:\n'
sha=native.sha
def method_hashes():
    paths=[Path(__file__),Path(native.__file__),Path(portable.__file__),Path(acquisition.__file__),
        Path(physical_pll.__file__),Path(pll.__file__),ROOT/'scripts/cloud_vbic_tree32_backend.py',
        ROOT/'scripts/review_pcie_pll_acquisition_v1.py']
    return {str(p.relative_to(ROOT)):sha(p)for p in paths}

def payload_info(path):
    with path.open('rb')as f:
        header=f.read(65536);assert MARKER in header,'Missing native binary header'
        offset=header.index(MARKER)+len(MARKER)
        f.seek(offset);digest=hashlib.sha256();count=0
        while b:=f.read(4*1024**2):digest.update(b);count+=len(b)
    return dict(header_bytes=offset,payload_bytes=count,payload_sha256=digest.hexdigest(),bytes=path.stat().st_size,sha256=sha(path))

def prefix_preserved(path,prior):
    with path.open('rb')as f:
        h=f.read(65536);assert MARKER in h
        f.seek(h.index(MARKER)+len(MARKER));left=prior['payload_bytes'];d=hashlib.sha256()
        while left:
            b=f.read(min(left,4*1024**2));assert b,'Truncated checkpoint prefix'
            d.update(b);left-=len(b)
    assert d.hexdigest()==prior['payload_sha256'],'Native checkpoint payload changed'
    return True

def process_contract(case,protected,boots):
    assert boots==['native-entrypoint'],'Cold restart detected'
    assert all(sha(Path(p))==v for p,v in protected.items()),'Protected native input changed'
    body=(case/'circuit.cir').read_text()
    assert body.count('.tran 3.125e-13 1e-06 0 3.125e-13')==1,'Original full analysis changed'
    assert len(re.findall(r'(?m)^alter .*\[off\] = 1$',body))==102
    assert '.options reltol=1e-4 abstol=1e-12 klu'in body
    assert sha(case/'parent865.spice')==physical_pll.MODEL_SHA
    vectors=next(s[5:].split()for s in body.splitlines()if s.startswith('save '))
    assert len(vectors)==34
    return vectors

def controls():
    import tempfile
    with tempfile.TemporaryDirectory()as tmp:
        p=Path(tmp)/'raw';p.write_bytes(b'old header\n'+MARKER+b'0123456789')
        info=payload_info(p)
        p.write_bytes(b'backpatched native header\n'+MARKER+b'0123456789more')
        assert prefix_preserved(p,info)
        rejected=[]
        for name,data in [('truncation',b'0123'),('corruption',b'012345678xmore')]:
            p.write_bytes(b'header\n'+MARKER+data)
            try:prefix_preserved(p,info)
            except AssertionError:rejected.append(name)
            else:raise AssertionError('Bad native prefix accepted')
        assert rejected==['truncation','corruption']
    return dict(prefix_header_backpatch_allowed=True,payload_faults_rejected=rejected,
                reader=pll.self_test(),acquisition=pll.acquisition_controls(),
                cycles=pll.acquisition_cycle_controls(),readback=readback_controls())

def restore_models(wanted):
    assert not LIB.exists();LIB.mkdir()
    packed=OUT/'models-source.tar.gz';fetch(acquisition.URL+'.tar.gz',acquisition.ARCHIVE_SHA,packed)
    assert packed.stat().st_size==1318040150
    found=set()
    with tarfile.open(packed)as tar:
        for m in tar:
            p=Path(m.name);assert not p.is_absolute()and'..'not in p.parts and p.parts[0]==LIB.name
            rel=str(Path(*p.parts[1:]))
            if rel not in wanted:continue
            assert m.isfile()and rel not in found;found.add(rel)
            data=tar.extractfile(m).read();assert hashlib.sha256(data).hexdigest()==wanted[rel]
            target=LIB/rel;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    assert found==set(wanted);packed.unlink()

def prepare():
    OUT.mkdir(exist_ok=False)
    fetch(BASE+'cloud-results-38906315749-1-native-portable-cross-job/native-portable-cross-job-38906315749-1.summary.json',CROSS_SHA,OUT/'cross-job-proof.json')
    cross=json.loads((OUT/'cross-job-proof.json').read_text())
    assert cross['cross_job_native_restore_proven'] and cross['source']==BOUNDED
    assert cross['positive']['rows']==12818 and all(c['rejected']for c in cross['controls'])
    assert cross['source_has_avx512f']and not cross['destination_has_avx512f']
    assert cross['glibc_tunables']==portable.TUNABLES and cross['unchanged_native_inputs']
    restoration.OUT=OUT;old,proof=restoration.restore(BOUNDED)
    assert proof['native_checkpoint_proven']and proof['original_bounded_trajectory_unchanged']
    wanted={str(Path(p).relative_to(LIB)):d for p,d in proof['preparation']['protected'].items()if Path(p).is_relative_to(LIB)}
    assert len(wanted)>=37;restore_models(wanted)
    shutil.copytree(LIB,OUT/'model-sources')
    CASE.mkdir();(OUT/'runtime').mkdir()
    engine=OUT/'runtime/patched-ngspice';shutil.copy2(old/'runtime/patched-ngspice',engine);assert sha(engine)==native.ENGINE_SHA
    for filename in ['native-image.tar','source-summary.json']:
        shutil.copy2(old/filename,OUT/filename)
    assert sha(OUT/'native-image.tar')==proof['native_image_sha256']
    shutil.copytree(old/'physical-parent-proof',OUT/'physical-parent-proof')
    full=(LIB/'circuit.cir').read_text();bounded=(old/'resumed/circuit.cir').read_text()
    assert bounded.replace('.tran 3.125e-13 4e-09 0 3.125e-13','.tran 3.125e-13 1e-06 0 3.125e-13')==full
    (CASE/'circuit.cir').write_text(full)
    shutil.copy2(old/'resumed/parent865.spice',CASE/'parent865.spice')
    expected='NSSOC actual845 original1us continuous capture\n.include "circuit.cir"\n.control\nop\nwrite op.raw all\nrun actual-acquisition.raw\nquit\n.endc\n.end\n'
    readback='echo NSSOC_BACKEND_OPTIONS_BEGIN\noption\necho NSSOC_BACKEND_OPTIONS_END\n'
    (CASE/'actual-acquisition.cir').write_text(expected.replace('quit\n.endc',readback+'quit\n.endc'))
    (CASE/'spinit').write_text('set num_threads=1\n')
    protected={str(p):sha(p)for p in [engine,*LIB.rglob('*'),*CASE.iterdir()]if p.is_file()}
    physical_pll.verify_prepared(OUT,proof['preparation']['physical_parent'],(CASE/'parent865.spice').read_text())
    receipt=dict(image_id=proof['image_id'],native_image_sha256=proof['native_image_sha256'],
        protected=protected,model_sources=wanted,physical_parent=proof['preparation']['physical_parent'],
        expected_options=proof['restored']['native_options'],bounded_source=BOUNDED,
        cross_job_summary_sha256=CROSS_SHA,runtime_libraries=proof['runtime_libraries'],
        glibc_tunables=portable.TUNABLES,vectors=process_contract(CASE,protected,['native-entrypoint']))
    # Only the small immutable source proof is retained; no bounded capture is a
    # full-run input. New full trajectory starts at time zero exactly once.
    (OUT/'bounded-source-summary.json').write_text(json.dumps(proof,indent=2)+'\n')
    shutil.rmtree(OUT/'inputs')
    return receipt

def restore_source(spec):
    assert set(spec)=={'run','attempt','stage','summary_sha256','parts_sha256'}
    assert str(spec['run']).isdigit()and str(spec['attempt']).isdigit()and spec['stage']in ('initial','continuation')
    assert all(re.fullmatch('[0-9a-f]{64}',spec[k])for k in ('summary_sha256','parts_sha256'))
    assert not OUT.exists()
    staging=ROOT/'cloud-pll-native-restore';staging.mkdir(exist_ok=False)
    group='pll-native-acquisition-'+spec['stage'];stem=f"{group}-{spec['run']}-{spec['attempt']}"
    url=BASE+f"cloud-results-{spec['run']}-{spec['attempt']}-{group}/"
    fetch(url+stem+'.summary.json',spec['summary_sha256'],staging/'source-summary.json')
    fetch(url+stem+'.parts.json',spec['parts_sha256'],staging/(stem+'.parts.json'))
    report=json.loads((staging/'source-summary.json').read_text())
    assert report['status']==CHECKPOINT_STATUS and report['checkpoint_saved']
    assert report['controller_sha256']==sha(__file__),'Resume the exact controller revision'
    assert report['method_hashes']==method_hashes(),'Resume exact parser, physical and native methods'
    assert report['run_id']==str(spec['run'])and report['run_attempt']==str(spec['attempt'])and report['stage']==spec['stage']
    manifest=json.loads((staging/(stem+'.parts.json')).read_text());assert manifest['source_directory']==OUT.name and manifest['stem']==stem
    for i,part in enumerate(manifest['parts']):
        assert part['index']==i and part['name']==stem+'.tar.gz.part'+str(i).zfill(4)
        fetch(url+part['name'],part['sha256'],staging/part['name'])
    verify_parts(manifest,staging);packed=staging/'source.tar.gz'
    with packed.open('wb')as dest:
        for part in manifest['parts']:
            with(staging/part['name']).open('rb')as src:shutil.copyfileobj(src,dest)
    assert sha(packed)==manifest['sha256']
    with tarfile.open(packed)as tar:
        seen=set()
        for m in tar:
            p=Path(m.name);assert not p.is_absolute()and'..'not in p.parts and p.parts[0]==OUT.name
            assert m.name not in seen and(m.isfile()or m.isdir());seen.add(m.name)
            tar.extract(m,ROOT,filter='data')
    assert sha(OUT/'result.json')==spec['summary_sha256']
    assert all(sha(OUT/p)==d for p,d in report['outputs'].items())
    assert not LIB.exists();shutil.copytree(OUT/'model-sources',LIB)
    assert all(sha(LIB/p)==d for p,d in report['preparation']['model_sources'].items())
    assert sha(CASE/'actual-acquisition.raw')==report['checkpoint_prefix']['sha256']
    assert payload_info(CASE/'actual-acquisition.raw')==report['checkpoint_prefix']
    history=OUT/'history';history.mkdir(exist_ok=True)
    shutil.copyfile(OUT/'result.json',history/(stem+'.json'))
    shutil.rmtree(staging)
    return report

def command(name,image,cpu,create):
    engine=OUT/'runtime/patched-ngspice'
    code='printf "native-entrypoint\\n" >> boots.log; exec "'+str(engine)+'" -n -b actual-acquisition.cir'
    return ['docker','create'if create else'run',*([]if create else['-d']),'--name',name,
        '--network','host','--security-opt','seccomp=unconfined','--cpuset-cpus',cpu,
        '--mount','type=bind,src='+str(ROOT)+',dst='+str(ROOT)+',readonly',
        '--mount','type=bind,src='+str(CASE)+',dst='+str(CASE),'-w',str(CASE),
        '-e','SPICE_SCRIPTS='+str(CASE),'-e','OMP_NUM_THREADS=1','-e','RAYON_NUM_THREADS=1',
        '-e','GLIBC_TUNABLES='+portable.TUNABLES,'--entrypoint','/bin/dash',image,'-c',code]

def execute(stage,seconds,spec=None):
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    assert stage in ('initial','continuation')and 60<=seconds<=14400
    prior=restore_source(spec)if spec else None
    preparation=prior['preparation']if prior else prepare()
    result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],controller_sha256=sha(__file__),
        method_hashes=method_hashes(),run_id=os.environ['GITHUB_RUN_ID'],run_attempt=os.environ['GITHUB_RUN_ATTEMPT'],stage=stage,
        boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),preparation=preparation,
        source_checkpoint=spec,checkpoint_saved=False,full_capture=False,acquisition_accepted=False,
        full_device_safety_accepted=False,full_phy_accepted=False,qualified_pex=False,
        scope='Original physical845 full1us/34probes/.3125ps/KLU/zeroOP/102OFF. Actual native process continuation only. Frozen both final100ns acquisition windows. Selected probes cannot prove full-device safety/PVT/refinement/CDR/x4/mainchip or PHY.',
        controls=prior['controls']if prior else controls())
    def save():(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    def run(label,args,required=True,timeout=900):
        p=subprocess.run(args,capture_output=True,text=True,timeout=timeout)
        dest=OUT/(stage+'-'+label+'.log');dest.write_text(p.stdout+p.stderr)
        result.setdefault('commands',[]).append(dict(label=label,args=args,returncode=p.returncode,sha256=sha(dest)));save()
        if required and p.returncode:raise RuntimeError(label+': '+(p.stdout+p.stderr)[-6000:])
        return p
    container=None;save()
    try:
        assert sha(native.__file__)=='28e3ca20e1d7cce96ac68f4ec19e510326d8e96ed0da77ddc16ab5b3c5e86231'
        assert not run('empty-runner',['docker','ps','-aq']).stdout.strip()
        result['cpu']=json.loads(run('lscpu',['lscpu','--json']).stdout)
        run('kernel',['uname','-a'])
        result['criu_build']=json.loads((Path(os.environ['RUNNER_TEMP'])/'criu-build.json').read_text())
        assert sha('/usr/sbin/criu')==result['criu_build']['binary_sha256']
        assert result['criu_build']['source_commit']=='9539417f3e3cfa4eb84c319cd71f4d52f1f08645'
        config="import json,pathlib;p=pathlib.Path('/etc/docker/daemon.json');d=json.loads(p.read_text())if p.exists()else{};d['experimental']=True;p.write_text(json.dumps(d))"
        run('docker-experimental',['sudo','python3','-c',config]);run('docker-restart',['sudo','systemctl','restart','docker'])
        assert sha(OUT/'native-image.tar')==preparation['native_image_sha256']
        run('load-image',['docker','load','-i',str(OUT/'native-image.tar')])
        info=json.loads(run('image',['docker','image','inspect',preparation['image_id']]).stdout)[0]
        assert info['Id']==preparation['image_id']
        cpu=prior['cpu_affinity']if prior else str(min(os.sched_getaffinity(0)))
        assert int(cpu)in os.sched_getaffinity(0);result['cpu_affinity']=cpu
        boots=(CASE/'boots.log').read_text().splitlines()if prior else['native-entrypoint']
        vectors=process_contract(CASE,preparation['protected'],boots);assert vectors==preparation['vectors']
        container='nssoc-pll-full-'+stage
        cmd=command(container,preparation['image_id'],cpu,bool(prior));result['native_command']=cmd;save()
        cid=run('create-or-start',cmd).stdout.strip();assert re.fullmatch('[0-9a-f]{64}',cid)
        if prior:
            assert result['boot_id']!=prior['boot_id'],'A separate cloud host is required'
            assert cmd[cmd.index('--network'):]==prior['native_command'][prior['native_command'].index('--network'):]
            checkpoints=OUT/'checkpoints/state'
            assert {str(p.relative_to(checkpoints)):sha(p)for p in checkpoints.rglob('*')if p.is_file()}==prior['checkpoint_images']
            root=Path(run('docker-root',['docker','info','--format','{{.DockerRootDir}}']).stdout.strip())
            dest=root/'containers'/cid/'checkpoints/state'
            run('checkpoint-dir',['sudo','mkdir','-p',str(dest.parent)])
            run('copy-checkpoint',['sudo','cp','-a',str(checkpoints),str(dest)])
            check="import pathlib,hashlib,json,sys;r=pathlib.Path(sys.argv[1]);print(json.dumps({str(p.relative_to(r)):hashlib.sha256(p.read_bytes()).hexdigest()for p in r.rglob('*')if p.is_file()}))"
            actual=json.loads(run('copy-proof',['sudo','python3','-c',check,str(dest)]).stdout);assert actual==prior['checkpoint_images']
            started=run('restore',['docker','start','--checkpoint','state',container],False)
            if started.returncode:
                run('restore-detail',['sudo','cat','/run/containerd/io.containerd.runtime.v2.task/moby/'+cid+'/work/restore.log'],False)
                raise RuntimeError('Native continuation restore failed')
            result['native_resume_started']=True;save()
        state=json.loads(run('runtime-environment',['docker','inspect',container]).stdout)[0]
        assert 'GLIBC_TUNABLES='+portable.TUNABLES in state['Config']['Env']
        result['actual_native_environment']=state['Config']['Env'];result['native_started_epoch']=time.time();save()
        start=time.monotonic();raw=CASE/'actual-acquisition.raw'
        while True:
            state=json.loads(subprocess.check_output(['docker','inspect',container]))[0]['State']
            elapsed=time.monotonic()-start
            result['elapsed_this_stage_s']=elapsed
            progress=dict(elapsed_s=elapsed,raw_bytes=raw.stat().st_size if raw.exists()else 0,native_running=state['Running'])
            print(json.dumps(progress),flush=True);result['last_progress']=progress;save()
            if not state['Running']:break
            if elapsed>=seconds:
                checkpoints=OUT/'checkpoints'
                if checkpoints.exists():shutil.rmtree(checkpoints)
                checkpoints.mkdir()
                run('save-checkpoint',['docker','checkpoint','create','--checkpoint-dir',str(checkpoints),container,'state'])
                state=json.loads(run('checkpoint-stopped',['docker','inspect',container]).stdout)[0]['State']
                assert not state['Running']
                run('readable-checkpoint',['sudo','chown','-R',str(os.getuid())+':'+str(os.getgid()),str(checkpoints)])
                result['checkpoint_images']={str(p.relative_to(checkpoints/'state')):sha(p)for p in(checkpoints/'state').rglob('*')if p.is_file()}
                assert result['checkpoint_images']and'pages-1.img'in result['checkpoint_images']
                result['checkpoint_prefix']=payload_info(raw);assert result['checkpoint_prefix']['payload_bytes']>35*8*1000
                result.update(status=CHECKPOINT_STATUS,checkpoint_saved=True);break
            time.sleep(min(60,max(1,seconds-elapsed)))
        run('native-log',['docker','logs',container],False)
        log=(OUT/(stage+'-native-log.log')).read_text()
        cumulative=OUT/'cumulative-native.log'
        oldlog=cumulative.read_text()if cumulative.exists()else''
        cumulative.write_text(oldlog+log)
        assert (CASE/'boots.log').read_text().splitlines()==['native-entrypoint']
        if prior:
            prefix_preserved(raw,prior['checkpoint_prefix']);result['prior_payload_unchanged']=True
            assert raw.stat().st_size>prior['checkpoint_prefix']['bytes'],'Native continuation made no progress'
        process_contract(CASE,preparation['protected'],['native-entrypoint'])
        physical_pll.verify_prepared(OUT,preparation['physical_parent'],(CASE/'parent865.spice').read_text())
        result['zero_source_operating_point']=pll.zero_source_operating_point((CASE/'op.raw').read_bytes(),vectors)
        if not result['checkpoint_saved']:
            result['native_exitcode']=state['ExitCode'];save();assert state['ExitCode']==0,(state,log[-6000:])
            options,diagnostics,_=backend_readback(cumulative.read_text(),'klu')
            result.update(native_options=options,diagnostics=diagnostics);save();assert not diagnostics
            assert all(options[k]==preparation['expected_options'][k]for k in ('backend','numeric','method'))
            names,values,cap=acquisition.capture(raw,vectors);result['capture']=cap
            cols={n:values[:,i]for i,n in enumerate(names)}
            result['independent_acquisition']=pll.acquisition_analyzer()(cols)
            result['cycle_diagnosis']=pll.acquisition_cycle_diagnosis(cols,result['independent_acquisition'])
            result.update(status=COMPLETE_STATUS,full_capture=True,original_gate_passed=bool(result['independent_acquisition']['passed']))
        result['protected_inputs_unchanged']=True;save()
    except BaseException as e:
        result.update(status='FAIL_OR_ERROR',error=repr(e));save();raise
    finally:
        if container:
            run('final-log',['docker','logs',container],False)
            run('cleanup',['docker','rm','-f',container],False)
        result['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'}
        save();print(json.dumps({k:result[k]for k in ('status','error','checkpoint_saved','full_capture','original_gate_passed')if k in result}),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--controls',action='store_true');p.add_argument('--stage',choices=['initial','continuation']);p.add_argument('--seconds',type=int,default=14400);a=p.parse_args()
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    if a.controls:print(json.dumps(controls()))
    else:
        text=os.environ.get('SOURCE_CHECKPOINT','').strip()
        execute(a.stage,a.seconds,json.loads(text)if text else None)
