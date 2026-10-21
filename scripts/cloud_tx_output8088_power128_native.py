#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Run the unchanged full8088 TX transient with durable native process capsules."""
import argparse,copy,hashlib,json,os,re,shlex,shutil,struct,subprocess,time,traceback
from pathlib import Path
import compare_cloud_routed_endpoints as reports
import cloud_tx_p4_drive3_builder as review
from cloud_tx_chunked_op import assemble_op
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1]
REPO='repos/Melihakbulut221/nssoc/'
ENGINE_SHA='103134f6e3bf71771a7f9c94cc43fd5ea2f9d51490116718814aa344e9c51509'
CRIU='9539417f3e3cfa4eb84c319cd71f4d52f1f08645'
TUNABLES='glibc.cpu.hwcaps=-AVX512F,-AVX512CD,-AVX512BW,-AVX512DQ,-AVX512ER,-AVX512PF,-AVX512VL,-RTM'
def digest(data):return hashlib.sha256(data).hexdigest()
def api(path):return json.loads(subprocess.check_output(['gh','api',REPO+path]))
def byte_hash(path,offset=0,length=None):
    h=hashlib.sha256()
    with path.open('rb')as f:
        f.seek(offset)
        while length is None or length>0:
            b=f.read(8*1024*1024 if length is None else min(length,8*1024*1024))
            if not b:break
            h.update(b)
            if length is not None:length-=len(b)
    assert length is None or length==0,'Truncated native file prefix'
    return h.hexdigest()
def raw_state(path,columns):
    if not path.exists():return None
    header=b''
    with path.open('rb')as f:
        while not header.endswith(b'Binary:\n'):
            line=f.readline()
            if not line:return None
            header+=line;assert len(header)<8*1024*1024,'Unexpected raw header size'
        assert int(re.search(rb'No. Variables:\s*(\d+)',header).group(1))==columns
        assert re.search(rb'(?m)^\s*0\s+time\s+time\s*$',header)
        offset=f.tell();size=path.stat().st_size;payload=size-offset
        rows=payload//(columns*8);last=None
        if rows:
            f.seek(offset+(rows-1)*columns*8);last=struct.unpack('<d',f.read(8))[0]
            assert 0<=last<=34e-9+1e-20
    normalized=re.sub(rb'(?m)^(No. Points:)[^\n]*',rb'\1',header)
    return dict(header_bytes=offset,header_identity_sha256=digest(normalized),payload_bytes=payload,
      payload_sha256=byte_hash(path,offset),complete_rows=rows,partial_row_bytes=payload%(columns*8),last_time_s=last,columns=columns)
def verify_prefix(case,prior,columns):
    assert (case/'boots.log').read_bytes()==b'native-entrypoint\n','Cold restart detected'
    p=prior['native_log']
    assert byte_hash(case/'native.log',0,p['bytes'])==p['sha256'],'Native log prefix changed'
    old=prior['raw_prefix']
    if old is not None:
        now=raw_state(case/'wave.raw',columns);assert now is not None
        assert now['header_identity_sha256']==old['header_identity_sha256'],'Raw vector/header identity changed'
        assert now['payload_bytes']>=old['payload_bytes']
        assert byte_hash(case/'wave.raw',now['header_bytes'],old['payload_bytes'])==old['payload_sha256'],'Native trajectory prefix changed'
def source_valid(spec,run,r,self_sha):
    assert set(spec)=={'run','attempt','group','source_head','controller_sha256','summary_sha256','parts_sha256','case'}
    assert type(spec['run'])is int and spec['run']>0 and spec['attempt']==1
    assert spec['case']in ('none','swap_leaf_select')
    assert spec['group']in ('tx-output8088-power128-native-initial-'+spec['case'],'tx-output8088-power128-native-cross-'+spec['case'])
    assert re.fullmatch('[0-9a-f]{40}',spec['source_head'])
    assert all(re.fullmatch('[0-9a-f]{64}',spec[k]) for k in ('controller_sha256','summary_sha256','parts_sha256'))
    assert run['id']==spec['run'] and run['run_attempt']==1 and run['head_sha']==spec['source_head']
    assert run['head_branch']=='codex/complete-open-work' and run['status']=='completed' and run['conclusion']=='success'
    assert run['path']in ('.github/workflows/tx-output8088-power128-native-initial-cloud.yml','.github/workflows/tx-output8088-power128-native-continuation-cloud.yml')
    assert r['source_head']==spec['source_head'] and r['run_id']==spec['run'] and r['case']==spec['case']
    assert r['controller_sha256']==spec['controller_sha256']==self_sha
    assert r['status']=='SAVED_ACTUAL8088_POWER128_NATIVE_PROCESS_REQUIRES_CONTINUATION_AND_FULL_REVIEW'
    assert r['native_process_saved'] and r['sources_unchanged'] and not r['full_capture']
    assert r['checkpointed_elf_sha256']==ENGINE_SHA and r['checkpoint_images']
    assert r['single_entrypoint'] and r['continuation']['next_phase']=='continue_same_native_process'
def spice_lines(path):
    # SPICE inputs are byte-oriented; Latin-1 comments must not rewrite model bytes.
    return [line.decode('latin-1') for line in path.read_bytes().splitlines()]
def runtime_files(deck,prepared):
    todo=[deck];seen={};osdis=[]
    for line in spice_lines(deck):
        if line.startswith('pre_osdi '):osdis.append(Path(shlex.split(line)[1]).resolve())
    assert len(osdis)==3 and len(set(osdis))==3
    while todo:
        p=todo.pop().resolve()
        if str(p)in seen:continue
        assert p.is_relative_to(ROOT) and p.is_file(),('Missing or external runtime input',str(p))
        assert str(p)in prepared['protected_inputs'],('Runtime input not in preparation evidence',str(p))
        h=sha(p);assert h==prepared['protected_inputs'][str(p)],('Prepared runtime bytes changed',str(p));seen[str(p)]=h
        for line in spice_lines(p):
            m=re.match(r"\s*\.(include|inc|lib)\s+(?:\"([^\"]+)\"|'([^']+)'|(\S+))(.*)$",line,re.I)
            if not m:continue
            name=next(v for v in m.group(2,3,4)if v is not None);target=Path(name)
            if not target.is_absolute():target=p.parent/target
            if m.group(1).lower()=='lib' and not m.group(5).strip() and not target.is_file() and '.'not in name:continue
            todo.append(target)
    for p in osdis:
        assert str(p)in prepared['protected_inputs'] and sha(p)==prepared['protected_inputs'][str(p)]
        seen[str(p)]=sha(p)
    return seen,osdis
def controls():
    """Synthetic descriptor/prefix corruption checks, never DUT acceptance."""
    import tempfile
    h='1'*64
    spec=dict(run=17,attempt=1,group='tx-output8088-power128-native-initial-none',source_head='a'*40,controller_sha256=h,summary_sha256='2'*64,parts_sha256='3'*64,case='none')
    run=dict(id=17,run_attempt=1,head_sha='a'*40,head_branch='codex/complete-open-work',status='completed',conclusion='success',path='.github/workflows/tx-output8088-power128-native-initial-cloud.yml')
    r=dict(source_head='a'*40,run_id=17,case='none',controller_sha256=h,status='SAVED_ACTUAL8088_POWER128_NATIVE_PROCESS_REQUIRES_CONTINUATION_AND_FULL_REVIEW',
      native_process_saved=True,sources_unchanged=True,full_capture=False,checkpointed_elf_sha256=ENGINE_SHA,checkpoint_images={'pages.img':'4'*64},single_entrypoint=True,continuation={'next_phase':'continue_same_native_process'})
    source_valid(spec,run,r,h)
    rejected=[]
    for label,where,key,value in [
        ('live_source','run','status','in_progress'),('failed_source','run','conclusion','failure'),
        ('wrong_run','run','id',18),('wrong_head','run','head_sha','b'*40),
        ('unknown_workflow','run','path','other.yml'),('wrong_case','report','case','swap_leaf_select'),
        ('unknown_controller','report','controller_sha256','5'*64),('cold_source','report','native_process_saved',False),
        ('changed_sources','report','sources_unchanged',False),('completed_capture','report','full_capture',True),
        ('wrong_engine','report','checkpointed_elf_sha256','6'*64),('empty_images','report','checkpoint_images',{}),
        ('repeated_entrypoint','report','single_entrypoint',False),('bad_summary_digest','spec','summary_sha256','invalid')]:
        ss,rr,pp=copy.deepcopy((spec,run,r));{'spec':ss,'run':rr,'report':pp}[where][key]=value
        try:source_valid(ss,rr,pp,h)
        except (AssertionError,KeyError):rejected.append(label)
        else:raise AssertionError('Accepted descriptor '+label)
    with tempfile.TemporaryDirectory()as directory:
        root=Path(directory);(root/'boots.log').write_bytes(b'native-entrypoint\n');(root/'native.log').write_bytes(b'original native log\n')
        header=b'Title: original\nNo. Variables: 2\nNo. Points: 0\nVariables:\n\t0\ttime\ttime\n\t1\tv(n)\tvoltage\nBinary:\n'
        payload=struct.pack('<dddd',0.,0.,1e-9,.5)
        raw=root/'wave.raw';raw.write_bytes(header+payload)
        prior=dict(native_log=dict(bytes=(root/'native.log').stat().st_size,sha256=sha(root/'native.log')),raw_prefix=raw_state(raw,2))
        continued=header.replace(b'No. Points: 0',b'No. Points: 3')+payload+struct.pack('<dd',2e-9,.7)
        raw.write_bytes(continued);(root/'native.log').write_bytes(b'original native log\ncontinued\n')
        verify_prefix(root,prior,2)
        for fault in ('cold_entrypoint','changed_log','changed_raw_value','truncated_raw','changed_vector'):
            (root/'boots.log').write_bytes(b'native-entrypoint\n')
            (root/'native.log').write_bytes(b'original native log\ncontinued\n');raw.write_bytes(continued)
            if fault=='cold_entrypoint':(root/'boots.log').write_bytes(b'native-entrypoint\nnative-entrypoint\n')
            elif fault=='changed_log':(root/'native.log').write_bytes(b'changed native log\ncontinued\n')
            elif fault=='changed_raw_value':raw.write_bytes(header+struct.pack('<dddd',0.,.01,1e-9,.5)+struct.pack('<dd',2e-9,.7))
            elif fault=='truncated_raw':raw.write_bytes(header+payload[:-8])
            else:raw.write_bytes(continued.replace(b'v(n)',b'v(x)'))
            try:verify_prefix(root,prior,2)
            except (AssertionError,AttributeError):rejected.append(fault)
            else:raise AssertionError('Accepted prefix '+fault)
    with tempfile.TemporaryDirectory(dir=ROOT)as directory:
        root=Path(directory);deck=root/'bench.cir';child=root/'child.inc';leaf=root/'leaf.lib'
        osdis=[root/('model'+str(i)+'.osdi')for i in range(3)]
        for p in osdis:p.write_bytes(b'\x7fELF\x00\xb5')
        deck.write_bytes((''.join('pre_osdi '+str(p)+'\n'for p in osdis)+'.include "child.inc"\n').encode())
        child.write_bytes(b'* untouched 1\xb5m comment\r\n.include leaf.lib\r\n')
        leaf.write_bytes(b'.lib typical\n* native section comment\n.endl typical\n')
        originals={p:p.read_bytes()for p in [deck,child,leaf,*osdis]}
        prepared=dict(protected_inputs={str(p.resolve()):sha(p)for p in originals})
        seen,loaded=runtime_files(deck,prepared)
        assert seen==prepared['protected_inputs'] and loaded==osdis
        assert all(p.read_bytes()==b for p,b in originals.items())
        for fault in ('changed_model_bytes','unproven_model_input','missing_model_input'):
            pp=copy.deepcopy(prepared);child.write_bytes(originals[child])
            if fault=='changed_model_bytes':child.write_bytes(originals[child]+b'* changed\n')
            elif fault=='unproven_model_input':del pp['protected_inputs'][str(child)]
            else:child.unlink()
            try:runtime_files(deck,pp)
            except AssertionError:rejected.append(fault)
            else:raise AssertionError('Accepted runtime model fault '+fault)
        child.write_bytes(originals[child])
    assert len(rejected)==22
    return dict(scope='Synthetic descriptor, lossless native prefix and byte-preserving SPICE closure controls only',rejected=rejected,count=22)

def main():
    p=argparse.ArgumentParser();p.add_argument('--stage',choices=('initial','cross'),required=True);p.add_argument('--case',choices=('none','swap_leaf_select'),required=True);args=p.parse_args()
    assert os.environ.get('GITHUB_ACTIONS')=='true' and os.environ['GITHUB_RUN_ATTEMPT']=='1'
    methods=json.loads((ROOT/'scripts/tx-output8088-power128-native-methods.json').read_text())
    assert all(sha(ROOT/p)==h for p,h in methods.items())
    assert str(ROOT)=='/home/runner/work/nssoc/nssoc'
    stage=args.stage;case_name=args.case;group='tx-output8088-power128-native-'+stage+'-'+case_name
    out=ROOT/('cloud-'+group);out.mkdir(exist_ok=False)
    staging=ROOT/('.tx8088-power128-stage-'+stage+'-'+case_name);staging.mkdir(exist_ok=False)
    prepared_root=ROOT/('cloud-tx-output8088-power128-prepared-wire-nominal-'+case_name)
    case=prepared_root/'native';reports.OUT=staging
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],run_id=int(os.environ['GITHUB_RUN_ID']),stage=stage,case=case_name,
      controller_sha256=sha(Path(__file__)),full_capture=False,full_serial_phy=False,mainchip_integrated=False,qualified_pex=False,electrical_screen_passed=False,native_process_saved=False)
    def save():(out/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    def run(label,cmd,required=True,timeout=900):
        q=subprocess.run(cmd,capture_output=True,text=True,timeout=timeout)
        log=out/(label+'.log');log.write_text(q.stdout+q.stderr)
        r.setdefault('commands',[]).append(dict(label=label,returncode=q.returncode,log_sha256=sha(log)));save()
        if required and q.returncode:raise RuntimeError(label+': '+(q.stdout+q.stderr)[-12000:])
        return q
    def state():return json.loads(subprocess.check_output(['docker','inspect',name]))[0]['State']
    def dump(label):
        st=state();assert st['Running']
        actual=run('actual-native-executable',['sudo','sha256sum','/proc/'+str(st['Pid'])+'/exe']).stdout.split()[0]
        assert actual==ENGINE_SHA
        images=out/'checkpoints';images.mkdir(exist_ok=True)
        run(label,['docker','checkpoint','create','--checkpoint-dir',str(images),name,'state'],timeout=1200)
        assert not state()['Running']
        run('readable-images',['sudo','chown','-R',str(os.getuid())+':'+str(os.getgid()),str(images)])
        r.update(checkpointed_elf_sha256=actual,native_process_saved=True,
          checkpoint_images={str(p.relative_to(images/'state')):sha(p)for p in(images/'state').rglob('*')if p.is_file()})
        assert r['checkpoint_images'];save()
    name='nssoc-tx8088-power128-'+stage+'-'+case_name.replace('_','-');owned=False;prior=None;save()
    try:
        prep_pin=json.loads((ROOT/'docs/evidence/tx-output8088-power128-preparation-pass-20261021.json').read_text())['cases'][case_name]
        assert prep_pin['run']==39625813143 and prep_pin['source_head']=='11012523cc39198bc2e3293a65bed0e47e5c588c'
        prepared,proof=reports.restore_report(prep_pin['group'],prep_pin['run'],prep_pin['summary_sha256'],prep_pin['parts_sha256'],prepared_root,list(prep_pin['outputs']))
        assert prepared['status']=='READY_ACTUAL8088_POWER128_PHYSICAL_WIRE_DECK_NOT_SIMULATED' and prepared['source_unchanged']
        assert prepared['output_parent_binding']['no_ideal_driver_core_or_output_interconnect'] and len(prepared['output_parent_binding']['controls'])==10
        assert prepared['output_parent_binding']['separate_schematic_output_removed']
        assert prepared['output_parent_binding']['original_stimuli_solver_timestep_external_loads_and_gates_unchanged']
        assert prepared['model_sha256']=='4dd5cfb2ad7e2c15cafe9e7cd3f3f029811d66fa58a8eb4823711d6a2a1cfdb5'
        assert prepared['core_counts']==dict(devices=8088,R=140222,C=99906)
        assert prepared['capture_preflight']['columns']==14182 and prepared['capture_preflight']['minimum_rows']==68001
        contract=json.loads((case/'contract.json').read_text());assert len(contract['hbt'])==604 and len(contract['mos'])==5376 and len(contract['vectors'])==14181
        assert contract['source_bits_sha256']=='5dd4496031f00ffea20c2af8cd828d95a868960129829389125dc5055bdb6825'
        engine=prepared_root/'runtime/patched-ngspice';engine.chmod(0o755);assert sha(engine)==ENGINE_SHA
        required,osdis=runtime_files(case/'bench.cir',prepared)
        required[str(engine)]=ENGINE_SHA
        for f in ('contract.json','spinit'):
            assert sha(case/f)==prepared['outputs']['native/'+f];required[str(case/f)]=sha(case/f)
        r['preparation_source']=proof;r['runtime_inputs']=required;r['prepared_case']=case_name
        r['boot_id']=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
        r['glibc_tunables']=TUNABLES;r['cpuset']=str(min(os.sched_getaffinity(0)))
        assert not run('empty-containers',['docker','ps','-aq']).stdout.strip()
        build=json.loads((Path(os.environ['RUNNER_TEMP'])/'criu-build.json').read_text())
        assert build['source_commit']==CRIU and sha(Path('/usr/sbin/criu'))==build['binary_sha256'];r['criu_build']=build
        run('criu-check',['sudo','criu','check','--all'],False)
        run('kernel',['uname','-a']);run('cpu',['lscpu','--json'])
        config="import json,pathlib;p=pathlib.Path('/etc/docker/daemon.json');d=json.loads(p.read_text())if p.exists()else{};d['experimental']=True;p.write_text(json.dumps(d))"
        run('docker-experimental',['sudo','python3','-c',config]);run('docker-restart',['sudo','systemctl','restart','docker'])
        if stage=='initial':
            assert not(case/'wave.raw').exists() and not(case/'boots.log').exists()
            assert shutil.disk_usage(case).free>=72*1024**3,'Insufficient space for full capture and durable process publication'
            rootfs=staging/'rootfs';rootfs.mkdir();libraries={}
            for i,elf in enumerate([engine,Path('/bin/dash'),*osdis]):
                output=run('ldd-'+str(i),['ldd',str(elf)]).stdout;assert 'not found'not in output
                for n in re.findall(r'(?:=>\s+|^\s*)(/\S+)',output,re.M):
                    q=Path(n);assert q.is_file();libraries[n]=sha(q)
            libraries['/bin/dash']=sha(Path('/bin/dash'))
            for n,h in libraries.items():
                q=rootfs/n.lstrip('/');q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(n,q);assert sha(q)==h
            (rootfs/'tmp').mkdir();(rootfs/'tmp').chmod(0o1777)
            (rootfs/'Dockerfile').write_text('FROM scratch\nCOPY . /\n')
            run('build-runtime',['docker','build','--network','none','-t','nssoc-tx8088-power128-native',str(rootfs)])
            r['image_id']=json.loads(run('runtime-image',['docker','image','inspect','nssoc-tx8088-power128-native']).stdout)[0]['Id']
            r['runtime_libraries']=libraries
            run('save-runtime',['docker','save','-o',str(out/'native-image.tar'),r['image_id']])
            r['native_image_sha256']=sha(out/'native-image.tar');shutil.rmtree(rootfs)
        else:
            spec=json.loads(os.environ['NSSOC_TX_SOURCE']);assert spec['case']==case_name
            sr=api('actions/runs/'+str(spec['run']));assert sr['status']=='completed'and sr['conclusion']=='success','Never restore a live or failed source'
            rel=api('releases/tags/cloud-results-'+str(spec['run'])+'-1-'+spec['group']);pieces={}
            for suffix in ('.summary.json','.parts.json'):
                a=next(a for a in rel['assets']if a['name'].endswith(suffix))
                raw=subprocess.check_output(['gh','api',REPO+'releases/assets/'+str(a['id']),'-H','Accept: application/octet-stream'])
                assert len(raw)==a['size']and a['digest']=='sha256:'+digest(raw);pieces[suffix]=raw
            assert digest(pieces['.summary.json'])==spec['summary_sha256'] and digest(pieces['.parts.json'])==spec['parts_sha256']
            prior=json.loads(pieces['.summary.json']);source_valid(spec,sr,prior,r['controller_sha256'])
            assert prior['boot_id']!=r['boot_id'] and prior['run_id']!=r['run_id']
            assert prior['runtime_inputs']==required and prior['glibc_tunables']==TUNABLES
            assert prior['preparation_source']['summary_sha256']==prep_pin['summary_sha256']
            r['cpuset']=prior['cpuset'];assert int(r['cpuset'])in os.sched_getaffinity(0)
            selected=[n for n in prior['outputs']if n=='native-image.tar' or n.startswith(('work/','checkpoints/'))]
            restored,sp=reports.restore_report(spec['group'],spec['run'],spec['summary_sha256'],spec['parts_sha256'],staging/'prior',selected)
            assert restored==prior
            for f in(staging/'prior/work').iterdir():
                assert f.is_file(),'Unexpected directory in native case'
                target=case/f.name
                if target.exists():
                    assert sha(target)==sha(f),'Prepared immutable case file changed';target.unlink()
                os.link(f,target)
            verify_prefix(case,prior,14182)
            image=staging/'prior/native-image.tar';assert sha(image)==prior['native_image_sha256']
            run('load-runtime',['docker','load','-i',str(image)])
            r['image_id']=prior['image_id'];assert json.loads(run('exact-image',['docker','image','inspect',r['image_id']]).stdout)[0]['Id']==r['image_id']
            shutil.copy2(image,out/'native-image.tar');r['native_image_sha256']=sha(out/'native-image.tar')
            r['runtime_libraries']=prior['runtime_libraries'];r['previous_boot_id']=prior['boot_id'];r['continuation_source']=sp;r['source_descriptor']=spec
        code='printf "native-entrypoint\\n" >> boots.log; exec "'+str(engine)+'" -n -b bench.cir > native.log 2>&1'
        cmd=['docker','create','--name',name,'--network','host','--security-opt','seccomp=unconfined','--cpuset-cpus',r['cpuset'],
          '--memory','12g','--memory-swap','12g','--ulimit','core=0:0','--ulimit','fsize=34359738368:34359738368',
          '--mount','type=bind,src='+str(ROOT)+',dst='+str(ROOT)+',readonly',
          '--mount','type=bind,src='+str(case)+',dst='+str(case),'-w',str(case),
          '-e','SPICE_SCRIPTS='+str(case),'-e','OMP_NUM_THREADS=1','-e','RAYON_NUM_THREADS=1','-e','GLIBC_TUNABLES='+TUNABLES,
          '--entrypoint','/bin/dash',r['image_id'],'-c',code]
        r['native_command']=cmd;save()
        if prior:assert cmd[4:]==prior['native_command'][4:],'Native runtime command changed'
        ident=run('create-native',cmd).stdout.strip();assert re.fullmatch('[a-f0-9]{64}',ident);owned=True
        if stage=='initial':run('start-native',['docker','start',name])
        else:
            images=staging/'prior/checkpoints/state'
            assert {str(p.relative_to(images)):sha(p)for p in images.rglob('*')if p.is_file()}==prior['checkpoint_images']
            docker_root=Path(run('docker-root',['docker','info','--format','{{.DockerRootDir}}']).stdout.strip())
            target=docker_root/'containers'/ident/'checkpoints/state'
            run('default-checkpoint-parent',['sudo','mkdir','-p',str(target.parent)])
            run('copy-checkpoint',['sudo','cp','-a',str(images),str(target)])
            compare="import pathlib,hashlib,sys;scan=lambda d:{str(p.relative_to(d)):hashlib.sha256(p.read_bytes()).hexdigest()for p in d.rglob('*')if p.is_file()};assert scan(pathlib.Path(sys.argv[1]))==scan(pathlib.Path(sys.argv[2]))"
            run('checkpoint-copy-proof',['sudo','python3','-c',compare,str(images),str(target)])
            q=run('restore-native',['docker','start','--checkpoint','state',name],False)
            if q.returncode:
                run('restore-diagnostic',['sudo','cat','/run/containerd/io.containerd.runtime.v2.task/moby/'+ident+'/work/restore.log'],False)
                raise RuntimeError('Native TX process restore failed')
            assert state()['Running'];r['restored_native_process']=True
            run('remove-consumed-default-images',['sudo','rm','-rf',str(target)])
            shutil.rmtree(staging/'prior');r['consumed_prior_capsule_removed']=True;save()
        seconds=int(os.environ.get('NSSOC_TX_SECONDS','600' if stage=='initial' else'3600'));assert 300<=seconds<=7200
        start=time.monotonic()
        while time.monotonic()-start<seconds and state()['Running']:
            if shutil.disk_usage(case).free<20*1024**3:
                r['early_checkpoint_reason']='Reserve real process dump/publication space';break
            time.sleep(15)
        r['segment_elapsed_s']=time.monotonic()-start
        if state()['Running']:dump('checkpoint-native')
        else:
            r['native_exit_code']=state()['ExitCode'];assert r['native_exit_code']==0,'Native simulator exited with failure'
            r['full_capture']=True
        assert(case/'boots.log').read_bytes()==b'native-entrypoint\n';r['single_entrypoint']=True
        r['native_log']=dict(bytes=(case/'native.log').stat().st_size,sha256=sha(case/'native.log'))
        r['raw_prefix']=raw_state(case/'wave.raw',14182)
        if prior:
            verify_prefix(case,prior,14182)
            before=prior['raw_prefix'];now=r['raw_prefix']
            r['cross_runner_numerical_progress_proven']=now is not None and (before is None or now['complete_rows']>before['complete_rows'])
            assert r['cross_runner_numerical_progress_proven'],'No observable native numerical progress; preserve checkpoint for diagnosis'
        if r['full_capture']:
            log=(case/'native.log').read_text()
            r['solver_options']=review.verify_solver_options(log,'breakpoint_tight_trap')
            r['diagnostics']=review.native_diagnostics(log,'breakpoint_tight_trap')
            flags=re.findall(r'(?ms)^NSSOC_NATIVE_FLAG_BEGIN (\S+)\n(.*?)^NSSOC_NATIVE_FLAG_END\s*$',log)
            assert [n for n,_ in flags]==['q.'+n+'.qnpn13g2'for n in contract['hbt']]
            assert all(re.findall(r'(?m)^\s*off\s+([01])\s*$',body)==['1']for _,body in flags)
            r['op_reassembly']=assemble_op(case,prepared['op_chunk_spec'])
            r['review']=review.review(case,contract)
            assert set(r['review']['interfaces'])=={'cmos','final','level_4','level_8','level_16'}
            assert all(v['samples']==6912 for v in r['review']['interfaces'].values())
            r['electrical_screen_passed']=case_name=='none' and r['review']['all_engineering_gates_passed'] and not r['diagnostics']
            if case_name!='none':
                r['original_fault_detected']=not r['review']['signals']['passed'];assert r['original_fault_detected']
            r['status']='COMPLETE_ACTUAL8088_POWER128_FULL_NATIVE_CAPTURE_REQUIRES_REVIEW_AND_FULL_PHY'
            if case_name=='none' and not r['electrical_screen_passed']:r['status']='REJECTED_ACTUAL8088_POWER128_ORIGINAL_LOADED_GATES'
        else:r['status']='SAVED_ACTUAL8088_POWER128_NATIVE_PROCESS_REQUIRES_CONTINUATION_AND_FULL_REVIEW'
        assert all(sha(Path(n))==h for n,h in required.items()) and all(sha(ROOT/p)==h for p,h in methods.items())
        r['sources_unchanged']=True
        r['continuation']=dict(run=r['run_id'],attempt=1,group=group,source_head=r['source_head'],controller_sha256=r['controller_sha256'],case=case_name,
          native_process_saved=r['native_process_saved'],next_phase='review_complete_capture'if r['full_capture']else'continue_same_native_process')
        save()
        assert r['status']!='REJECTED_ACTUAL8088_POWER128_ORIGINAL_LOADED_GATES','Original full loaded electrical gates rejected'
    except BaseException as e:
        if not r['status'].startswith('REJECTED_'):r['status']='FAIL_OR_ERROR'
        r.update(error=repr(e),traceback=traceback.format_exc());save()
        if(case/'native.log').exists():print((case/'native.log').read_text(errors='replace')[-16000:],flush=True)
        raise
    finally:
        if owned:
            try:
                if state()['Running'] and not r['native_process_saved']:dump('emergency-checkpoint-native')
            except BaseException as e:r['emergency_checkpoint_error']=repr(e)
            run('remove-owned-container',['docker','rm','-f',name],False)
        if case.exists()and not(out/'work').exists():
            run('readable-native-work',['sudo','chown','-R',str(os.getuid())+':'+str(os.getgid()),str(case)])
            shutil.copytree(case,out/'work',copy_function=os.link)
        r['outputs']={str(p.relative_to(out)):sha(p)for p in out.rglob('*')if p.is_file()and p!=out/'result.json'};save()
if __name__=='__main__':main()
