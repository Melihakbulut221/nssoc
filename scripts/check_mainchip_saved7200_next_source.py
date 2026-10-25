#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Source/metadata and synthetic archive/log controls; never restores a process."""
import ast,copy,hashlib,io,json,os,tarfile,tempfile
from pathlib import Path
import mainchip_saved7200_next_admission as a
import cloud_mainchip_saved7200_next as c
import check_mainchip_userstack7200_source as prior
from cloud_chunked_results import pack,verify_parts
def check():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    m=c.methods();program,labels=c.adapted_source()
    prior.validate_generated(program)
    assert len(labels)==9 and hashlib.sha256(program.encode()).hexdigest()==m['generated_controller_sha256']
    derivation=json.loads((a.ROOT/'scripts/mainchip-saved7200-next-derivation.json').read_text())
    old=(a.ROOT/'scripts/cloud_mainchip_userstack7200_continue.py').read_text()
    assert a.sha(old.encode())==derivation['original_sha256']
    derived=old
    for row in derivation['edits']:
        assert derived.count(row['before'])==row['count']
        derived=derived.replace(row['before'],row['after'])
    current=Path(c.__file__).read_text();assert derived==current
    for row in reversed(derivation['edits']):
        assert derived.count(row['after'])==row['count']
        derived=derived.replace(row['after'],row['before'])
    assert derived==old
    oldf={n.name:ast.dump(n)for n in ast.parse(old).body if isinstance(n,ast.FunctionDef)}
    newf={n.name:ast.dump(n)for n in ast.parse(current).body if isinstance(n,ast.FunctionDef)}
    assert oldf.keys()==newf.keys()and {n for n in oldf if oldf[n]!=newf[n]}=={'adapted_source','main'}
    frozen_bridge=(a.ROOT/'scripts/mainchip_userstack7200_admission.py').read_text()
    def node(src,name):return ast.dump(next(n for n in ast.parse(src).body if isinstance(n,ast.FunctionDef)and n.name==name))
    assert node(frozen_bridge,'validate_current_rows')==node(Path(a.__file__).read_text(),'validate_current_rows')
    inherited=prior.check();assert inherited['status']=='PASS60_EXACT_DIAGNOSTIC_ADMISSION_AND_ROUTE_SOURCE_CONTROLS_ONLY'
    raw=(a.ROOT/'docs/evidence/mainchip-userstack7200-native-result-20261025.json').read_bytes()
    outer=a.source_report(raw)
    run=a.api('actions/runs/'+str(a.RUN));release=a.api('releases/423327513')
    tag=a.api('git/ref/tags/'+release['tag_name']);jobs=a.api('actions/runs/'+str(a.RUN)+'/jobs?per_page=100')['jobs']
    assert a.transport_identity(run,release,tag,jobs)
    rejected=[]
    def reject(label,fn):
        try:fn()
        except (AssertionError,KeyError,ValueError,TypeError,UnicodeError):rejected.append(label)
        else:raise AssertionError('Accepted corruption: '+label)
    def put(x,path,value):
        for k in path[:-1]:x=x[k]
        x[path[-1]]=value
    metadata=[
      ('run','id',1),('run','head_sha','0'*40),('run','run_attempt',2),('run','status','in_progress'),
      ('run','conclusion','failure'),('run','head_branch','main'),('run','path','unrelated.yml'),
      ('release','id',1),('release','tag_name','wrong'),('release','target_commitish','main'),
      ('release','draft',True),('release','prerelease',False),('tag','ref','refs/tags/wrong')]
    for target,key,value in metadata:
        q=copy.deepcopy(dict(run=run,release=release,tag=tag,jobs=jobs));q[target][key]=value
        reject('metadata-'+target+'-'+key,lambda q=q:a.transport_identity(**q))
    for name,path,value in [('tag-type',['object','type'],'tag'),('tag-head',['object','sha'],'0'*40)]:
        q=copy.deepcopy(tag);put(q,path,value);reject(name,lambda q=q:a.transport_identity(run,release,q,jobs))
    for name,key,value in [('asset-size','size',1),('asset-digest','digest','sha256:'+'0'*64),('asset-state','state','new')]:
        q=copy.deepcopy(release);next(x for x in q['assets']if x['id']==675060096)[key]=value
        reject(name,lambda q=q:a.transport_identity(run,q,tag,jobs))
    q=copy.deepcopy(jobs);q[0]['conclusion']='failure'
    reject('failed-prior-control-job',lambda:a.transport_identity(run,release,tag,q))
    reject('missing-prior-native-job',lambda:a.transport_identity(run,release,tag,jobs[:1]))
    badouter=[
      ('status',['status'],'PASS'),('head',['source_head'],'0'*40),('run',['run_id'],'1'),
      ('controller',['generated_program_sha256'],'0'*64),('inner',['inner_controller_result_sha256'],'0'*64),
      ('no-progress',['continuation_accepted'],False),('route-invented',['routing_complete'],True),
      ('timing-invented',['final_timing_complete'],True),('PHY-invented',['full_phy_accepted'],True),
      ('history-invented',['historical_sources_unchanged_proven'],True),('debugger',['gdb_attached'],True),
      ('cold',['cold_restart'],True),('lost-perturbation',['old_scheduling_perturbation_retained'],False),
      ('images',['new_saved_process_images'],{}),('outputs',['outputs'],{}),
      ('input-mismatch',['current_inputs_after','independent_streamed_hashes_verified'],False)]
    for name,path,value in badouter:
        q=copy.deepcopy(outer);put(q,path,value);reject('outer-'+name,lambda q=q:a.validate_outer(q))
    reject('summary-truncated',lambda:a.source_report(raw[:-1]))
    # Synthetic inner shape. Native restoration separately requires actual exact INNER bytes.
    inner=dict(status='SAVED_CROSS_RUNNER_ACTIVE_DRT_PROGRESS_REQUIRES_FURTHER_CONTINUATION_AND_SIGNOFF',
        native_process_saved=True,restored_native_process=True,sources_unchanged=True,active_drt_cross_runner_progress_proven=True,
        source_head=a.HEAD,run_id=a.RUN,stage='cross',route_complete=False,final_timing_complete=False,full_phy_accepted=False,
        controller_sha256=a.CONTROLLER,checkpointed_elf_sha256=a.ELF,image_id=a.IMAGE,
        checkpoint_images=outer['new_saved_process_images'],retained_timing_contract=dict(clock_periods_ns=[20,4,8,8],
        derating_percent=5,new_native_sta_run_required=True),native_log=dict(single_entrypoint=True,sha256=outer['outputs']['work/native.log']),
        outputs={n:h for n,h in outer['outputs'].items()if n.startswith(('work/','checkpoints/'))},
        continuation=dict(run=a.RUN,attempt=1,group=a.GROUP,source_head=a.HEAD,controller_sha256=a.CONTROLLER,
        native_process_saved=True,next_phase='continue_same_native_process'),
        unobserved_runtime_binding=dict(status='PASS_EXACT_RUNTIME_CLOSURE_WITHOUT_GDB',runtime_closure=a.capsule()['runtime_closure'],
        target_detached=True,gdb_attached=False),segment_elapsed_s=7200.1)
    inner.update(a.original.GLOBAL_INPUTS);assert a.inner_fields(inner,outer)
    badinner=[
      ('unsaved',['native_process_saved'],False),('unrestored',['restored_native_process'],False),
      ('sources',['sources_unchanged'],False),('cpu-only',['active_drt_cross_runner_progress_proven'],False),
      ('head',['source_head'],'0'*40),('run',['run_id'],1),('stage',['stage'],'initial'),
      ('controller',['controller_sha256'],'0'*64),('ELF',['checkpointed_elf_sha256'],'0'*64),
      ('image',['image_id'],'wrong'),('clock',['retained_timing_contract','clock_periods_ns'],[20,4,8,9]),
      ('derating',['retained_timing_contract','derating_percent'],0),('STA',['retained_timing_contract','new_native_sta_run_required'],False),
      ('continuation',['continuation','group'],'wrong'),('runtime',['unobserved_runtime_binding','runtime_closure'],{}),
      ('tracer',['unobserved_runtime_binding','target_detached'],False),('elapsed',['segment_elapsed_s'],float('nan')),
      ('error',['error'],'prior error')]
    for name,path,value in badinner:
        q=copy.deepcopy(inner);put(q,path,value);reject('inner-'+name,lambda q=q:a.inner_fields(q,outer))
    boots=b'native-entrypoint\n'
    prefix=b'NSSOC_SAVED_GLOBAL_DRT_BEGIN\nStart 1st optimization iteration\nCompleting 50% with 120 violations\n'
    log=prefix+b'Completing 100% with 100 violations\n[INFO DRT-0199] Number of violations = 100\nStart 2nd optimization iteration\n'
    old=dict(native_log=a.original.log_proof(prefix,boots))
    current=dict(native_log=a.original.log_proof(log,boots),restored_work_prefixes_verified={'work/native.log':a.sha(prefix)},
        controls=a.original.log_controls(log,boots),segment_elapsed_s=7200.1)
    assert a.native_log_evidence(current,old,log,boots)['appended_bytes']==len(log)-len(prefix)
    for name,mutlog,mutboots in [('cold-entry',log,boots+boots),('prefix-rewritten',b'X'+log[1:],boots),
        ('no-appended-progress',prefix+b'CPU active\n',boots),('no-growth',prefix,boots),
        ('duplicate-init',log+b'NSSOC_SAVED_GLOBAL_DRT_BEGIN\n',boots)]:
        q=copy.deepcopy(current)
        if name in('no-appended-progress','no-growth'):q['native_log']=a.original.log_proof(mutlog,mutboots)
        reject('log-'+name,lambda q=q,mutlog=mutlog,mutboots=mutboots:a.native_log_evidence(q,old,mutlog,mutboots))
    for name,path,value in [('recorded-proof',['native_log','bytes'],1),('prefix-hash',['restored_work_prefixes_verified','work/native.log'],'0'*64),('controls',['controls'],[])]:
        q=copy.deepcopy(current);put(q,path,value);reject('log-'+name,lambda q=q:a.native_log_evidence(q,old,log,boots))
    with tempfile.TemporaryDirectory()as temp:
        root=Path(temp);source=root/'fixture';source.mkdir()
        payload={'result.json':b'{}\n','work/native.log':log,'criu-build.log':b'qualified build fixture\n','criu-build.json':b'{}\n'}
        for n,b in payload.items():p=source/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
        expected={n:a.sha(b)for n,b in payload.items()if n not in a.ADDONS}
        manifest=pack(source,'positive',root,71)
        positive=a.complete_extract(manifest,root,root/'restored',expected)
        assert set(positive['original_members'])==set(expected)and set(positive['publication_additions'])==a.ADDONS
        q=copy.deepcopy(manifest);q['sha256']='0'*64
        reject('archive-whole-hash',lambda:a.complete_extract(q,root,root/'bad-whole',expected))
        q=copy.deepcopy(expected);q['work/native.log']='0'*64
        reject('archive-original-hash',lambda:a.complete_extract(manifest,root,root/'bad-member',q))
        # Every inventory fault has a valid newly packed transport, so inventory must reject.
        cases=[
          ('unknown','fixture/unknown',tarfile.REGTYPE,b'x',None),
          ('duplicate','fixture/work/native.log',tarfile.REGTYPE,log,None),
          ('symlink','fixture/link',tarfile.SYMTYPE,b'',None),
          ('hardlink','fixture/link',tarfile.LNKTYPE,b'',None),
          ('traversal','fixture/../escape',tarfile.REGTYPE,b'x',None),
          ('backslash','fixture/work\\escape',tarfile.REGTYPE,b'x',None),
          ('wrong-root','other/escape',tarfile.REGTYPE,b'x',None),
          ('missing-addon',None,None,None,'criu-build.log'),
          ('missing-original',None,None,None,'work/native.log')]
        for name,extra,kind,data,omit in cases:
            path=root/(name+'.tar.gz.part0000')
            with tarfile.open(path,'w:gz')as archive:
                for n,b in payload.items():
                    if n==omit:continue
                    ent=tarfile.TarInfo('fixture/'+n);ent.size=len(b);archive.addfile(ent,io.BytesIO(b))
                if extra is not None:
                    ent=tarfile.TarInfo(extra);ent.type=kind;ent.linkname='work/native.log'if kind in(tarfile.SYMTYPE,tarfile.LNKTYPE)else''
                    ent.size=len(data);archive.addfile(ent,io.BytesIO(data))
            digest=a.file_sha(path);size=path.stat().st_size
            packed=dict(format='ordered-tar-gzip-parts-v1',stem=name,source_directory='fixture',bytes=size,sha256=digest,
                parts=[dict(index=0,name=path.name,bytes=size,sha256=digest)])
            verify_parts(packed,root)
            reject('archive-'+name,lambda packed=packed,name=name:a.complete_extract(packed,root,root/('bad-'+name),expected))
    assert len(rejected)==74 and len(set(rejected))==74
    return dict(status='PASS74_SAVED7200_NEXT_SOURCE_CONTROLS_NOT_PROCESS_RESTORE',
        rejected=rejected,prior60=inherited,actual_outer_summary_authenticated=True,
        inner_positive_scope='SYNTHETIC SHAPE ONLY; ACTUAL INNER AND NATIVE LOG REMAIN PRE-RESTORE GATES',
        original_inner_member_restored=False,archive_downloaded=False,native_process_restored=False,
        chip_started=False,gdb_attached=False,full_source_derivation_reversed=True,
        generated_controller_sha256=a.sha(program.encode()))
if __name__=='__main__':print(json.dumps(check(),indent=2))
