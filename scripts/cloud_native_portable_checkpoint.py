#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Exact physical845 native SPICE checkpoint feasibility; bounded runtime proof only."""
import hashlib,json,os,re,shutil,subprocess,tarfile,time
from pathlib import Path
import numpy as np
import cloud_pll_vbic_acquisition as acquisition
import cloud_tx_companion_replay as engines
import cloud_pll_filter_physical_acquisition as physical
import run_cloud_pll865_snapshot as pll
from cloud_vbic_tree32_backend import backend_readback
from route_cloud_newer_postcts import fetch,sha as _file_sha
def sha(path):return _file_sha(Path(path))
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'cloud-native-portable-checkpoint';SOURCE=ROOT/'cloud-pll-snapshot'
STOP=4e-9
TUNABLES='glibc.cpu.hwcaps=-AVX512F,-AVX512CD,-AVX512BW,-AVX512DQ,-AVX512ER,-AVX512PF,-AVX512VL,-RTM'
REFERENCE_VALUES_SHA='633f0aaa88c7c08655e6d1b7f99d08284916746331f7c50c03091161ca2bbd1e'
ENGINE_SHA='103134f6e3bf71771a7f9c94cc43fd5ea2f9d51490116718814aa344e9c51509'
def prepare():
    fetch(acquisition.URL+'.json',acquisition.SUMMARY_SHA,OUT/'source-summary.json');old=json.loads((OUT/'source-summary.json').read_text())
    assert old['parent_sha256']==acquisition.PARENT_SHA and len(old['vectors'])==34 and old['native_off_flags']==102
    wanted={str(Path(r['hosted_path'])):r['sha256']for r in old['inputs'].values()}
    wanted.update({'circuit.cir':old['relocated_deck_sha256'],'parent865.spice':old['parent_sha256']})
    assert len(old['inputs'])==35 and not SOURCE.exists();SOURCE.mkdir()
    packed=OUT/'source.tar.gz';fetch(acquisition.URL+'.tar.gz',acquisition.ARCHIVE_SHA,packed);assert packed.stat().st_size==1318040150
    found=set()
    with tarfile.open(packed)as tar:
        for m in tar:
            path=Path(m.name);assert not path.is_absolute()and'..'not in path.parts and path.parts[0]==SOURCE.name
            rel=str(Path(*path.parts[1:]))
            if rel not in wanted:continue
            assert m.isfile()and rel not in found;found.add(rel)
            data=tar.extractfile(m).read();assert hashlib.sha256(data).hexdigest()==wanted[rel]
            p=SOURCE/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
    assert found==set(wanted);packed.unlink()
    engines.OUT=OUT;paths,provenance=engines.restore_engines();assert sha(paths['patched'])==ENGINE_SHA
    parent,receipt=physical.prepare((SOURCE/'parent865.spice').read_text(),OUT)
    body=(SOURCE/'circuit.cir').read_text();original='.tran 3.125e-13 1e-06 0 3.125e-13';bounded='.tran 3.125e-13 4e-09 0 3.125e-13'
    assert body.count(original)==1 and len(re.findall(r'(?m)^alter .*\[off\] = 1$',body))==102
    assert '.options reltol=1e-4 abstol=1e-12 klu'in body
    body=body.replace(original,bounded);assert body.replace(bounded,original)==(SOURCE/'circuit.cir').read_text()
    vectors=next(l[5:].split()for l in body.splitlines()if l.startswith('save '));assert vectors==old['vectors']
    deck='NSSOC actual845 bounded native checkpoint runtime proof only\n.include "circuit.cir"\n.control\nop\nwrite op.raw all\nrun actual-acquisition.raw\necho NSSOC_BACKEND_OPTIONS_BEGIN\noption\necho NSSOC_BACKEND_OPTIONS_END\nquit\n.endc\n.end\n'
    cases={}
    for name in ('host','reference','resumed'):
        p=OUT/name;p.mkdir();(p/'circuit.cir').write_text(body);(p/'parent865.spice').write_text(parent);(p/'actual-acquisition.cir').write_text(deck);(p/'spinit').write_text('set num_threads=1\n');cases[name]=p
    protected={str(p):sha(p)for p in [*SOURCE.rglob('*'),paths['patched'],*[p/f for p in cases.values()for f in ('circuit.cir','parent865.spice','actual-acquisition.cir','spinit')]]if p.is_file()}
    return paths['patched'],cases,vectors,dict(source_summary_sha256=acquisition.SUMMARY_SHA,source_archive_sha256=acquisition.ARCHIVE_SHA,runtime=provenance,physical_parent=receipt,protected=protected,only_analysis_stop_changed_for_runtime_test=True,stop_s=STOP,full_acquisition_test=False)

def inspect_capture(case,vectors,log):
    path=case/'actual-acquisition.raw';names,values,meta=pll.decode_prefix(path.read_bytes())
    assert meta['header_matches_observed']and meta['payload_has_only_complete_rows']
    assert set(names)=={'time',*vectors}and len(names)==35 and names[0]=='time'
    assert len(values)>12000 and np.isfinite(values).all();t=values[:,0]
    assert t[0]==0 and abs(t[-1]-STOP)<1e-20 and np.all(np.diff(t)>0)and np.diff(t).max()<=3.125e-13*1.00001
    options,diagnostics,_=backend_readback(log,'klu');assert not diagnostics
    op=pll.zero_source_operating_point((case/'op.raw').read_bytes(),vectors)
    return names,values,dict(capture=meta,start_s=float(t[0]),end_s=float(t[-1]),values_sha256=hashlib.sha256(values.tobytes()).hexdigest(),native_options=options,zero_source_operating_point=op,diagnostics=diagnostics)

def verify(reference,restored,boots):
    rn,rv=reference;sn,sv=restored
    assert boots==['native-entrypoint'],'Cold restart detected'
    assert rn==sn and rv.shape==sv.shape,'Missing samples or probes'
    assert np.array_equal(rv,sv),'Native times or voltage states changed'
    return dict(all_native_times_and_all34_probes_bit_exact=True,rows=len(rv),values_sha256=hashlib.sha256(sv.tobytes()).hexdigest(),single_entrypoint=True)

def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(exist_ok=False)
    result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],native_checkpoint_proven=False,cross_job_native_restore_proven=False,full_capture=False,acquisition_accepted=False,full_phy_accepted=False,scope='Bounded4ns exact physical845/102HBT/3OSDI runtime test with original34probes/.3125ps/KLU/zeroOP/OFF/solver and circuit. Host versus container baseline then native checkpoint/restore must be bit-exact. Not original1us acquisition, full-device safety, PVT, x4 or PHY acceptance.')
    def save():(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    def run(label,args,required=True,timeout=900):
        p=subprocess.run(args,capture_output=True,text=True,timeout=timeout);(OUT/(label+'.log')).write_text(p.stdout+p.stderr)
        result.setdefault('commands',[]).append(dict(label=label,args=args,returncode=p.returncode,sha256=sha(OUT/(label+'.log'))));save()
        if required and p.returncode:raise RuntimeError(label+': '+(p.stdout+p.stderr)[-5000:])
        return p
    owned=[];save()
    try:
        result['glibc_tunables']=TUNABLES
        result['portability_hypothesis']='Disable glibc AVX512 and RTM IFUNC choices before any native process starts. Original simulator/circuit/model libraries and bounded native numerical trajectory must remain exact. Cross-job portability not yet proven.'
        result['cpu']=json.loads(run('source-lscpu',['lscpu','--json']).stdout)
        (OUT/'source-cpuinfo.txt').write_text(Path('/proc/cpuinfo').read_text());run('source-kernel',['uname','-a'])
        engine,cases,vectors,receipt=prepare();result['preparation']=receipt;save()
        assert not run('empty-runner',['docker','ps','-aq']).stdout.strip()
        result['boot_id']=Path('/proc/sys/kernel/random/boot_id').read_text().strip();result['runner_name']=os.environ.get('RUNNER_NAME');result['run_id']=os.environ['GITHUB_RUN_ID']
        result['criu_build']=json.loads((Path(os.environ['RUNNER_TEMP'])/'criu-build.json').read_text());assert sha('/usr/sbin/criu')==result['criu_build']['binary_sha256']
        run('criu-check',['sudo','criu','check','--all'],False)
        cpu_directory=OUT/'source-cpu-capabilities';cpu_directory.mkdir()
        run('source-cpu-capabilities',['sudo','criu','cpuinfo','dump','-D',str(cpu_directory)])
        run('readable-cpu-capabilities',['sudo','chown','-R',str(os.getuid())+':'+str(os.getgid()),str(cpu_directory)])
        config="import json,pathlib;p=pathlib.Path('/etc/docker/daemon.json');d=json.loads(p.read_text())if p.exists()else{};d['experimental']=True;p.write_text(json.dumps(d))"
        run('docker-experimental',['sudo','python3','-c',config]);run('docker-restart',['sudo','systemctl','restart','docker'])
        # Build a network-free root image from the exact host ELF loader/libraries.
        # OSDI dependencies are included explicitly. No apt/tag drift inside a container.
        rootfs=OUT/'runtime-root';rootfs.mkdir();libraries={};elfs=[engine,Path('/bin/dash'),*SOURCE.rglob('*.osdi')];assert len(list(SOURCE.rglob('*.osdi')))==3
        for i,elf in enumerate(elfs):
            text=run('ldd-'+str(i),['ldd',str(elf)]).stdout;assert 'not found'not in text
            for path in re.findall(r'(?:=>\s+|^\s*)(/\S+)',text,re.M):
                p=Path(path);assert p.is_file();libraries[path]=sha(p)
        libraries['/bin/dash']=sha('/bin/dash')
        for name,digest in libraries.items():
            target=rootfs/name.lstrip('/');target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(name,target);assert sha(target)==digest
        (rootfs/'tmp').mkdir();(rootfs/'tmp').chmod(0o1777)
        (rootfs/'Dockerfile').write_text('FROM scratch\nCOPY . /\n')
        run('build-native-root',['docker','build','--network','none','-t','nssoc-native-checkpoint',str(rootfs)],timeout=300)
        info=json.loads(run('native-image',['docker','image','inspect','nssoc-native-checkpoint']).stdout)[0];result['image_id']=info['Id'];result['runtime_libraries']=libraries
        run('save-native-image',['docker','save','-o',str(OUT/'native-image.tar'),result['image_id']]);result['native_image_sha256']=sha(OUT/'native-image.tar');save()
        cpu=str(min(os.sched_getaffinity(0)))
        env={k:v for k,v in os.environ.items()if k not in ('LD_PRELOAD','PYTHONPATH','PYTHONHOME','GH_TOKEN','GITHUB_TOKEN','LD_LIBRARY_PATH','GLIBC_TUNABLES')};env.update(SPICE_SCRIPTS=str(cases['host']),OMP_NUM_THREADS='1',RAYON_NUM_THREADS='1',GLIBC_TUNABLES=TUNABLES)
        with (cases['host']/'run.log').open('w')as stream:
            p=subprocess.run([str(engine),'-n','-b','actual-acquisition.cir'],cwd=cases['host'],env=env,preexec_fn=lambda:os.sched_setaffinity(0,{int(cpu)}),stdout=stream,stderr=subprocess.STDOUT,timeout=900)
        assert p.returncode==0
        hn,hv,hr=inspect_capture(cases['host'],vectors,(cases['host']/'run.log').read_text());result['host']=hr;save()
        assert hr['values_sha256']==REFERENCE_VALUES_SHA,'CPU masking changed original native physical845 bounded trajectory'
        def command(name,case,create=False):
            # Environment is explicitly enumerated; no GitHub credentials enter the process.
            code='printf "native-entrypoint\\n" >> boots.log; exec "'+str(engine)+'" -n -b actual-acquisition.cir'
            return ['docker','create'if create else'run',*([]if create else['-d']),'--name',name,'--network','host','--security-opt','seccomp=unconfined','--cpuset-cpus',cpu,'--mount','type=bind,src='+str(ROOT)+',dst='+str(ROOT)+',readonly','--mount','type=bind,src='+str(case)+',dst='+str(case),'-w',str(case),'-e','SPICE_SCRIPTS='+str(case),'-e','OMP_NUM_THREADS=1','-e','RAYON_NUM_THREADS=1','-e','GLIBC_TUNABLES='+TUNABLES,'--entrypoint','/bin/dash',result['image_id'],'-c',code]
        reference='nssoc-native-reference';original='nssoc-native-original';clone='nssoc-native-restored';owned=[reference,original,clone]
        run('start-reference',command(reference,cases['reference']));reference_exit=run('wait-reference',['docker','wait',reference]).stdout.strip()
        run('reference-log',['docker','logs',reference],False);ref_log=(OUT/'reference-log.log').read_text()
        assert reference_exit=='0',('Native reference exit',reference_exit,ref_log[-6000:])
        rn,rv,rr=inspect_capture(cases['reference'],vectors,ref_log);result['reference']=rr
        result['host_container_equivalence']=verify((hn,hv),(rn,rv),(cases['reference']/'boots.log').read_text().splitlines());save()
        run('start-native',command(original,cases['resumed']))
        state=json.loads(run('native-runtime-environment',['docker','inspect',original]).stdout)[0]
        assert 'GLIBC_TUNABLES='+TUNABLES in state['Config']['Env']
        result['actual_native_environment']=state['Config']['Env'];save()
        raw=cases['resumed']/'actual-acquisition.raw';deadline=time.monotonic()+180
        while not raw.exists()or raw.stat().st_size<35*8*2000:
            assert time.monotonic()<deadline,'No native transient prefix';time.sleep(.2)
        checkpoints=OUT/'checkpoints';checkpoints.mkdir()
        run('checkpoint-native',['docker','checkpoint','create','--checkpoint-dir',str(checkpoints),original,'state'])
        state=json.loads(run('stopped-native',['docker','inspect',original]).stdout)[0]['State'];assert not state['Running']
        prefix=raw.read_bytes();marker=b'Binary:\n';assert prefix.count(marker)==1;payload=prefix.split(marker,1)[1]
        assert len(payload)>35*8*1000 and len(payload)<rv.nbytes
        result['checkpoint_prefix']=dict(bytes=len(prefix),payload_bytes=len(payload),sha256=hashlib.sha256(prefix).hexdigest(),payload_sha256=hashlib.sha256(payload).hexdigest());(OUT/'checkpoint-prefix.raw').write_bytes(prefix);save()
        run('original-prefix-log',['docker','logs',original]);original_log=(OUT/'original-prefix-log.log').read_text()
        clone_id=run('create-native-clone',command(clone,cases['resumed'],True)).stdout.strip();assert re.fullmatch('[0-9a-f]{64}',clone_id)
        docker_root=Path(run('docker-root',['docker','info','--format','{{.DockerRootDir}}']).stdout.strip());destination=docker_root/'containers'/clone_id/'checkpoints/state'
        run('native-default-dir',['sudo','mkdir','-p',str(destination.parent)]);run('native-copy',['sudo','cp','-a',str(checkpoints/'state'),str(destination)])
        check="import pathlib,hashlib,sys,json;scan=lambda r:{str(p.relative_to(r)):hashlib.sha256(p.read_bytes()).hexdigest()for p in r.rglob('*')if p.is_file()};a=scan(pathlib.Path(sys.argv[1]));b=scan(pathlib.Path(sys.argv[2]));assert a and a==b;print(json.dumps(a))"
        result['checkpoint_images']=json.loads(run('native-copy-proof',['sudo','python3','-c',check,str(checkpoints/'state'),str(destination)]).stdout);save()
        restored=run('restore-native',['docker','start','--checkpoint','state',clone],False)
        if restored.returncode:
            run('restore-native-detail',['sudo','cat','/run/containerd/io.containerd.runtime.v2.task/moby/'+clone_id+'/work/restore.log'],False);raise RuntimeError('Native restore failed')
        clone_exit=run('wait-native-clone',['docker','wait',clone]).stdout.strip()
        run('restored-native-log',['docker','logs',clone],False);resumed_log=original_log+(OUT/'restored-native-log.log').read_text()
        assert clone_exit=='0',('Restored native exit',clone_exit,resumed_log[-6000:])
        sn,sv,sr=inspect_capture(cases['resumed'],vectors,resumed_log);result['restored']=sr
        assert raw.read_bytes().split(marker,1)[1].startswith(payload),'Native pre-checkpoint payload changed'
        result['positive']=verify((rn,rv),(sn,sv),(cases['resumed']/'boots.log').read_text().splitlines());controls=[]
        for fault in ('truncation','state_corruption','cold_restart'):
            bad=sv[:-1]if fault=='truncation'else sv.copy();boots=['native-entrypoint']
            if fault=='state_corruption':bad[-1,1]+=1e-6
            if fault=='cold_restart':boots.append('native-entrypoint')
            try:verify((rn,rv),(sn,bad),boots)
            except AssertionError as error:controls.append(dict(fault=fault,rejected=True,error=str(error)))
            else:raise AssertionError('Native checkpoint corruption escaped')
        result['controls']=controls
        assert all(sha(Path(p))==v for p,v in receipt['protected'].items())and all(sha(p)==v for p,v in libraries.items())
        result.update(status='PASS_NATIVE_PHYSICAL845_MASKED_IFUNC_CHECKPOINT_BIT_EXACT_BOUNDED4NS_NOT_CROSS_JOB_OR_ACQUISITION',native_checkpoint_proven=True,original_bounded_trajectory_unchanged=True)
    except BaseException as error:result.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        for name in owned:
            run('final-log-'+name,['docker','logs',name],False)
            run('cleanup-'+name,['docker','rm','-f',name],False)
        if (OUT/'checkpoints').exists():run('readable-checkpoints',['sudo','chown','-R',str(os.getuid())+':'+str(os.getgid()),str(OUT/'checkpoints')],False)
        result['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
        print(json.dumps({k:result[k]for k in ('status','error','native_checkpoint_proven')if k in result}),flush=True)
if __name__=='__main__':main()
