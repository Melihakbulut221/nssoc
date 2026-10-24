#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Authenticate the existing CDR diagnostic artifact once; no engine or capture replay."""
import argparse,base64,collections,copy,hashlib,io,json,math,os,re,stat,subprocess,tempfile,traceback,zipfile
from pathlib import Path,PurePosixPath
import ensure_cloud_tested_source_release as publication
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-cdr-v58-diagnostic-publication'
METHOD=ROOT/'scripts/cdr-v58-diagnostic-publication-methods.json'
REPO='Melihakbulut221/nssoc'
GROUP='cdr-v58-diagnostic-publication'
RUN=40122075973
HEAD='8cf2a01d3d541c42f03ab4d16c259d91fd6c1c87'
JOB=120955749588
ARTIFACT=12572066803
ZIP_BYTES=593468974
ZIP_SHA='3b8e73c072d85e8dfe3ae444252c480e90490ae92b76f9172a396b7749b067d4'
LOG_BYTES=27858
LOG_SHA='c414f7590eb869047af3ccc6e3aaea310c0fa36d603859d751b9f875d19050b4'
RESULT_BYTES=142943
RESULT_SHA='d54c81a4493814b50e28c0dd67289933197d9aad03f0c126a0b13b96a327d729'
CASES=('nominal_early','nominal_late','hot_early')
FILES={'source-summary.json','source-parts.json','original-measurements-reproduced.json','selected-native.bin','selected-native.json','diagnosis.json'}
STATUS='PASS_EXACT_EXISTING_CDR_DIAGNOSTICS_PUBLISHED_ORIGINAL_REJECTIONS_RETAINED'
def sha_bytes(b):return hashlib.sha256(b).hexdigest()
def sha_file(p):
    with Path(p).open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
def host():
    assert os.environ.get('GITHUB_ACTIONS')=='true'and os.environ.get('RUNNER_ENVIRONMENT')=='github-hosted'
    assert os.environ.get('GITHUB_REPOSITORY')==REPO
def pins():
    m=json.loads(METHOD.read_text())
    for p,h in m['protected'].items():assert sha_file(ROOT/p)==h,p
    return m
def api(path,raw=False):
    b=subprocess.check_output(['gh','api','--allow-escape-sequences','repos/'+REPO+'/'+path])
    return b if raw else json.loads(b)
def identity(run,job,a):
    assert run['id']==RUN and run['head_sha']==HEAD and run['run_attempt']==1
    assert run['head_branch']=='codex/cdr-v58-saved-capture-diagnosis'and run['path']=='.github/workflows/cdr-v58-saved-capture-cloud.yml'
    assert run['status']=='completed'and run['conclusion']=='success'
    assert job['id']==JOB and job['run_id']==RUN and job['head_sha']==HEAD and job['run_attempt']==1
    assert job['name']=='readback'and job['status']=='completed'and job['conclusion']=='success'
    assert a['id']==ARTIFACT and a['name']=='cdr-v58-saved-capture'and a['expired']is False
    assert a['size_in_bytes']==ZIP_BYTES and a['digest']=='sha256:'+ZIP_SHA
    r=a['workflow_run']
    assert r['id']==RUN and r['head_sha']==HEAD and r['head_branch']==run['head_branch']
    assert r['repository_id']==r['head_repository_id']==1364721142
def log_identity(b):
    assert len(b)==LOG_BYTES and sha_bytes(b)==LOG_SHA
    found=[]
    for line in b.decode('utf-8').splitlines():
        x=re.match(r'^\d{4}-\d\d-\d\dT\S+Z (\{.*\})$',line)
        if x:
            d=json.loads(x[1])
            if 'result_sha256'in d:found.append(d)
    expected=dict(status='PASS_EXACT_SAVED_CAPTURE_DIAGNOSTICS_ONLY',result_bytes=RESULT_BYTES,result_sha256=RESULT_SHA,
        completed_cases=list(CASES),new_simulation=False,cdr_accepted=False,full_phy_accepted=False)
    assert found==[expected]
    assert 'Artifact ID '+str(ARTIFACT)in b.decode()
    assert 'SHA256 digest of uploaded artifact zip is '+ZIP_SHA in b.decode()
    return expected
def report_identity(r):
    assert r['status']=='PASS_EXACT_SAVED_CAPTURE_DIAGNOSTICS_ONLY'and r['source_head']==HEAD
    assert r['source_run']==40108285374 and r['sources_unchanged']is True and r['original_electrical_rejections_authoritative']is True
    assert all(r[k]is False for k in ('new_simulation','cdr_accepted','full_phy_accepted'))
    assert [c['case']for c in r['cases']]==list(CASES)
    expected={'result.json':RESULT_SHA}
    for c in r['cases']:
        case=c['case']
        assert c['status']=='DIAGNOSTIC_ONLY_ORIGINAL_ELECTRICAL_REJECTION_REPRODUCED'
        assert c['source_head']=='d92a3367a1013d1071125b753ec4f65ae4ec813b'and c['run']==40108285374
        assert c['original_rejection_preserved']is True
        assert all(c[k]is False for k in ('new_simulation','cdr_accepted','full_phy_accepted'))
        assert c['failed_native_ids']==[59,60,71,72,87,88,111,112]
        assert c['clock_native_ids']==list(range(61,69))+list(range(79,87))+list(range(95,103))+list(range(113,121))
        assert c['raw_capture']['header_rows']==113475 and c['raw_capture']['columns']==1152
        cache=c['selected_cache'];assert cache['rows']==113475 and len(cache['columns'])==188
        assert cache['columns'][0]=='time'and len(set(cache['columns']))==188 and cache['dtype']=='<f8'
        assert cache['bytes']==170666400 and cache['all_native_rows_retained']is True
        assert set(c['outputs'])==FILES and c['outputs']['selected-native.bin']==cache['sha256']
        for n,h in c['outputs'].items():
            assert re.fullmatch('[a-f0-9]{64}',h);expected[case+'/'+n]=h
    assert len(expected)==19
    return expected
def regular_name(info):
    n=info.filename
    assert n and '\\'not in n and '\0'not in n and ':'not in n and not n.startswith('/')
    p=PurePosixPath(n);assert '..'not in p.parts and str(p)==n.rstrip('/')
    mode=info.external_attr>>16
    assert stat.S_IFMT(mode)in(0,stat.S_IFREG,stat.S_IFDIR)
    assert not(info.flag_bits&1)and info.compress_type in(zipfile.ZIP_STORED,zipfile.ZIP_DEFLATED)
    assert info.is_dir()==n.endswith('/')
    assert stat.S_IFMT(mode)in ((0,stat.S_IFDIR)if info.is_dir()else(0,stat.S_IFREG))
    return n
def scan_archive(path,expected,size,digest,out,keep):
    """Stream every member through CRC/SHA; selected cache bytes are never copied."""
    assert Path(path).stat().st_size==size and sha_file(path)==digest
    assert set(keep)<=set(expected)
    parents={str(p)for n in expected for p in PurePosixPath(n).parents if str(p)!='.'}
    seen=set();files={};total=0
    with zipfile.ZipFile(path)as z:
        assert not z.comment and len(z.infolist())<=len(expected)+len(parents)
        for info in z.infolist():
            n=regular_name(info);assert n not in seen;seen.add(n)
            if info.is_dir():assert n[:-1]in parents and info.file_size==0;continue
            assert n in expected and n not in files
            assert info.file_size<=256*1024**2
            total+=info.file_size;assert total<=2*1024**3
            target=out/n if n in keep else None
            if target is not None:target.parent.mkdir(parents=True,exist_ok=True)
            h=hashlib.sha256();count=0
            with z.open(info)as inp:
                dest=target.open('xb')if target is not None else None
                try:
                    while block:=inp.read(4*1024**2):
                        h.update(block);count+=len(block)
                        if dest is not None:dest.write(block)
                finally:
                    if dest is not None:dest.close()
            assert count==info.file_size and h.hexdigest()==expected[n],n
            files[n]=dict(bytes=count,sha256=h.hexdigest())
    assert set(files)==set(expected)
    return dict(files=files,uncompressed_bytes=total,archive_bytes=size,archive_sha256=digest,all_member_CRC_and_SHA_verified=True)
def original_result(path):
    with zipfile.ZipFile(path)as z:
        found=[i for i in z.infolist()if i.filename=='result.json'];assert len(found)==1
        i=found[0];regular_name(i);assert not i.is_dir()and i.file_size==RESULT_BYTES
        b=z.read(i);assert len(b)==RESULT_BYTES and sha_bytes(b)==RESULT_SHA
    r=json.loads(b);report_identity(r);return r
def events_summary(events):
    assert isinstance(events,list)
    for e in events:
        assert e['left_row']<e['right_row']and e['left_s']<e['right_s']
        assert all(math.isfinite(e[k])for k in ('left_s','right_s','left_value','right_value','threshold'))
        assert e['direction']in ('rising','falling')and e['ordering_qualified']is False
        assert e['zero_plateau_rows']==e['right_row']-e['left_row']-1
        assert 'linear_estimate_s'not in e
    return dict(count=len(events),directions=dict(collections.Counter(e['direction']for e in events)),
        first=None if not events else {k:v for k,v in events[0].items()if k!='same_native_row_devices'},
        last=None if not events else {k:v for k,v in events[-1].items()if k!='same_native_row_devices'},
        maximum_bracket_s=max((e['right_s']-e['left_s']for e in events),default=0.),
        maximum_zero_plateau_rows=max((e['zero_plateau_rows']for e in events),default=0))
def relations(a,b,records,kind):
    result=[];seen=[]
    for rec in records:
        if kind=='parent':
            i=rec['parent_index'];indices=rec['local_indices'];pairs=[(i,j)for j in indices]
        else:
            i=rec['collector_index'];indices=rec['base_indices'];pairs=[(j,i)for j in indices]
        assert i==len(seen);seen.append(i);assert len(indices)==len(set(indices))and len(indices)==len(rec['relations'])
        for (ia,ib),label in zip(pairs,rec['relations'],strict=True):
            x,y=a[ia],b[ib]
            actual='a_definitely_before_b'if x['right_s']<y['left_s']else'b_definitely_before_a'if y['right_s']<x['left_s']else'overlapping_native_brackets_order_ambiguous'
            assert label==actual
            result.append([ia,ib,y['left_s']-x['right_s'],y['right_s']-x['left_s'],label])
    assert len(seen)==len(a if kind=='parent'else b)
    return dict(columns=['a_index','b_index','b_minus_a_min_s','b_minus_a_max_s','ordering'],
                all_existing_associations=result,
                caveat='Every original half-UI association is retained; interval differences are not causal, fitted, or interpolated delays.')
def point_extrema(samples):
    fields=('C_v','B_v','E_v','S_v','VCE_v','VBE_v','Ic_a','Ic_per_emitter_a')
    assert samples
    for s in samples:
        p=s['sample'];assert p['nx']==2
        assert all(math.isfinite(p[k])for k in fields)
    return {k:{'minimum':min(samples,key=lambda s:s['sample'][k]),'maximum':max(samples,key=lambda s:s['sample'][k])}for k in fields}
def diagnostic_summary(d,case):
    assert d['status']=='DIAGNOSTIC_ONLY_ORIGINAL_ELECTRICAL_REJECTION_REPRODUCED'
    assert all(d[k]is False for k in ('interpolation_used_for_new_diagnostic','event_filtering','phase_fitting','new_simulation','cdr_accepted','full_phy_accepted'))
    assert d['original_measurement_interpolation_preserved']is True
    assert set(d['same_row_failed_devices'])==set(map(str,[59,60,71,72,87,88,111,112]))
    parent=d['parent_clock_native_crossing_brackets'];parent_info=events_summary(parent)
    clocks=[]
    assert len(d['actual_parallel_clock_pairs'])==16
    for pair in d['actual_parallel_clock_pairs']:
        for dev in pair['devices']:
            samples=[]
            assert len(dev['parent_edges'])==len(parent)
            for i,item in enumerate(dev['parent_edges']):
                assert item['parent_edge']==parent[i]and len(item['bracket_rows'])==2
                for pos,p in enumerate(item['bracket_rows']):
                    assert p['row']==parent[i]['left_row'if pos==0 else'right_row']
                    assert p['time_s']==parent[i]['left_s'if pos==0 else'right_s']
                    samples.append(dict(parent_edge_index=i,side='left'if pos==0 else'right',sample=p))
            clocks.append(dict(native_id=dev['id'],clock=dev['clock'],native_topology=pair['native_topology'],
                base_vs_opposite_parent=events_summary(dev['terminal_base_vs_opposite_parent_clock']),
                same_row_extrema_at_every_parent_edge=point_extrema(samples)))
    assert len(clocks)==32 and len({x['native_id']for x in clocks})==32
    branches=[]
    for b in d['actual_shared_tail_base_differences']:
        base=b['events'];collect=b['collector_events']
        branches.append(dict(sampler=b['sampler'],tail_cluster=b['tail_cluster'],cp_id=b['cp_id'],cn_id=b['cn_id'],
            actual_base_vectors=b['actual_base_vectors'],actual_collector_vectors=b['actual_collector_vectors'],
            base=events_summary(base),collector=events_summary(collect),
            parent_to_base=relations(parent,base,b['parent_relations'],'parent'),
            base_to_collector=relations(base,collect,b['collector_to_base_relations'],'collector')))
    assert len(branches)==32
    samplers={}
    assert set(d['sampler_settling'])==set('abcd')
    for name,items in d['sampler_settling'].items():
        assert len(items)==255 and [x['bit_index']for x in items]==list(range(1,256))
        phases={}
        for phase in (-.05,0,.3,.6,.9):
            candidates=[]
            for item in items:
                pts=[p for p in item['fixed_points']if p['phase_ui']==phase];assert len(pts)==1
                b=pts[0]['bracket'];assert b['interpolation']is False
                assert len(b['rows'])==(1 if b['exact_native']else 2)
                for p in b['rows']:
                    keys=list(p['values']);assert len(keys)==4 and keys[2:]==['v(cp)','v(cn)']
                    signed=(p['values'][keys[0]]-p['values'][keys[1]])*(2*item['expected_bit']-1)
                    assert math.isfinite(signed)
                    candidates.append(dict(bit_index=item['bit_index'],expected_bit=item['expected_bit'],
                        phase_ui=phase,signed_native_margin_v=signed,bracket=b))
            phases[str(phase)]=dict(native_rows=len(candidates),minimum=min(candidates,key=lambda x:x['signed_native_margin_v']),
                maximum=max(candidates,key=lambda x:x['signed_native_margin_v']))
        samplers[name]=dict(all_bits=[dict(bit_index=x['bit_index'],expected_bit=x['expected_bit'],
            ideal_source_edge_s=x['ideal_source_edge_s'],original_clock_to_valid_s=x['original_clock_to_valid_s'],
            last_bad_native_row=x['last_bad_native_row'],native_100mV_crossings=x['native_100mV_crossings'])for x in items],
            fixed_phase_native_margin_extrema=phases)
        for x in items:events_summary(x['native_100mV_crossings'])
    return dict(case=case,same_row_failed_devices=d['same_row_failed_devices'],parent_clock=parent_info,
        all32_clock_devices=clocks,all32_shared_tail_combinations=branches,all_sampler_bits=samplers,
        original_electrical_rejection_preserved=True,diagnostic_only=True,new_simulation=False,cdr_accepted=False,full_phy_accepted=False)
def emit(result):
    b=(json.dumps(result,indent=2,allow_nan=False)+'\n').encode()
    assert len(b)<=32*1024**2,'Summary too large; never silently truncate'
    (OUT/'result.json').write_bytes(b)
    print('PUBLICATION_RESULT_BYTES',len(b));print('PUBLICATION_RESULT_SHA256',sha_bytes(b))
    s=base64.b64encode(b).decode();parts=[s[i:i+4096]for i in range(0,len(s),4096)]
    for i,p in enumerate(parts):print(f'PUBLICATION_RESULT_BASE64 {i}/{len(parts)} {p}',flush=True)
def controls():
    host();m=pins();faults=[]
    run=api('actions/runs/'+str(RUN));job=api('actions/jobs/'+str(JOB));a=api('actions/artifacts/'+str(ARTIFACT));identity(run,job,a)
    log=api('actions/jobs/'+str(JOB)+'/logs',True);log_identity(log)
    def reject(name,fn):
        try:fn()
        except (AssertionError,KeyError,ValueError,zipfile.BadZipFile):faults.append(name)
        else:raise AssertionError('Accepted corruption '+name)
    for which,k,v in [('run','head_sha','0'*40),('run','run_attempt',2),('run','status','in_progress'),('run','conclusion','failure'),
        ('job','id',0),('job','name','controls'),('job','head_sha','0'*40),('artifact','id',0),('artifact','expired',True),
        ('artifact','digest','sha256:'+'0'*64),('artifact','size_in_bytes',ZIP_BYTES+1)]:
        r,j,b=copy.deepcopy((run,job,a));obj={'run':r,'job':j,'artifact':b}[which];obj[k]=v
        reject(which+'_'+k,lambda r=r,j=j,b=b:identity(r,j,b))
    reject('log_truncated',lambda:log_identity(log[:-1]))
    reject('log_ANSI_removed',lambda:log_identity(re.sub(rb'\x1b\[[0-?]*[ -/]*[@-~]',b'',log)))
    with tempfile.TemporaryDirectory()as tmp:
        root=Path(tmp);raw=b'opaque\x1b[31m\x00\xff';expected={'a.json':sha_bytes(raw),'nested/b.bin':sha_bytes(b'second')}
        def archive(entries,comment=b''):
            p=root/('fixture'+str(len(list(root.glob('fixture*'))))+'.zip')
            with zipfile.ZipFile(p,'w',compression=zipfile.ZIP_DEFLATED)as z:
                for n,b in entries:z.writestr(n,b)
                z.comment=comment
            return p
        def check(p,expected=expected,size=None,digest=None):
            out=root/('out'+str(len(list(root.glob('out*')))));out.mkdir()
            return scan_archive(p,expected,p.stat().st_size if size is None else size,sha_file(p)if digest is None else digest,out,{'a.json'}&set(expected))
        positive=archive([('a.json',raw),('nested/b.bin',b'second')]);proof=check(positive)
        assert proof['all_member_CRC_and_SHA_verified']and len(proof['files'])==2
        reject('wrong_archive_extent',lambda:check(positive,size=positive.stat().st_size+1))
        reject('wrong_archive_hash',lambda:check(positive,digest='0'*64))
        reject('wrong_member_hash',lambda:check(positive,expected={**expected,'a.json':'0'*64}))
        for name,entries in [('missing',[('a.json',raw)]),('extra',[('a.json',raw),('nested/b.bin',b'second'),('extra',b'x')]),
            ('duplicate',[('a.json',raw),('a.json',raw)]),('traversal',[('../a.json',raw)]),('absolute',[('/a.json',raw)]),
            ('alias',[('nested/../a.json',raw)]),('backslash',[('a\\b',raw)]),('colon',[('a:b',raw)]),
            ('unused_directory',[('unused/',b'')]),('member_changed',[('a.json',b'changed'),('nested/b.bin',b'second')])]:
            p=archive(entries);reject(name,lambda p=p:check(p))
        link=zipfile.ZipInfo('a.json');link.external_attr=(stat.S_IFLNK|0o777)<<16
        p=archive([(link,raw)]);reject('symlink',lambda:check(p))
        p=archive([('a.json',raw),('nested/b.bin',b'second')],b'comment');reject('comment',lambda:check(p))
    e=dict(left_row=1,right_row=2,left_s=1.,right_s=2.,left_value=-1.,right_value=1.,threshold=0.,
        direction='rising',zero_plateau_rows=0,ordering_qualified=False)
    events_summary([e])
    for k,v in [('left_row',2),('ordering_qualified',True),('linear_estimate_s',1.5),('threshold',float('nan')),('zero_plateau_rows',1)]:
        bad=dict(e);bad[k]=v;reject('event_'+k,lambda bad=bad:events_summary([bad]))
    r=relations([e],[dict(e,left_row=3,right_row=4,left_s=3.,right_s=4.)],
        [dict(parent_index=0,local_indices=[0],relations=['a_definitely_before_b'])],'parent')
    assert r['all_existing_associations']==[[0,0,1.,3.,'a_definitely_before_b']]
    reject('relation_changed',lambda:relations([e],[e],[dict(parent_index=0,local_indices=[0],relations=['a_definitely_before_b'])],'parent'))
    reject('relation_dropped',lambda:relations([e],[e],[],'parent'))
    # Synthetic report exercises real schema gates; actual report remains SHA-bound in production.
    fixture=dict(status='PASS_EXACT_SAVED_CAPTURE_DIAGNOSTICS_ONLY',source_head=HEAD,source_run=40108285374,
        sources_unchanged=True,original_electrical_rejections_authoritative=True,new_simulation=False,cdr_accepted=False,full_phy_accepted=False,cases=[])
    for name in CASES:
        fixture['cases'].append(dict(case=name,status='DIAGNOSTIC_ONLY_ORIGINAL_ELECTRICAL_REJECTION_REPRODUCED',
            source_head='d92a3367a1013d1071125b753ec4f65ae4ec813b',run=40108285374,original_rejection_preserved=True,
            new_simulation=False,cdr_accepted=False,full_phy_accepted=False,failed_native_ids=[59,60,71,72,87,88,111,112],
            clock_native_ids=list(range(61,69))+list(range(79,87))+list(range(95,103))+list(range(113,121)),
            raw_capture=dict(header_rows=113475,columns=1152),outputs={n:'a'*64 for n in FILES},
            selected_cache=dict(rows=113475,columns=['time',*['v'+str(i)for i in range(187)]],dtype='<f8',bytes=170666400,
                all_native_rows_retained=True,sha256='a'*64)))
    report_identity(fixture)
    mutations=[('status',lambda x:x.update(status='PASS')),('source',lambda x:x.update(source_head='0'*40)),
        ('acceptance',lambda x:x.update(cdr_accepted=True)),('simulation',lambda x:x.update(new_simulation=True)),
        ('missing_case',lambda x:x['cases'].pop()),('lost_rejection',lambda x:x['cases'][0].update(original_rejection_preserved=False)),
        ('missing_failed_device',lambda x:x['cases'][0]['failed_native_ids'].pop()),
        ('raw_rows',lambda x:x['cases'][0]['raw_capture'].update(header_rows=113474)),
        ('cache_extent',lambda x:x['cases'][0]['selected_cache'].update(bytes=1)),
        ('cache_digest',lambda x:x['cases'][0]['selected_cache'].update(sha256='b'*64))]
    for name,change in mutations:
        bad=copy.deepcopy(fixture);change(bad);reject('report_'+name,lambda bad=bad:report_identity(bad))
    pub=publication.controls();assert len(pub['rejected'])==17
    assert len(faults)==45,len(faults)
    pins()
    return dict(status='PASS_EXISTING_CDR_ARTIFACT_METADATA_AND45_CONTROLS_ONLY',faults=faults,publication_controls=pub,
        artifact_downloaded=False,new_simulation=False,cdr_accepted=False,full_phy_accepted=False)
def main():
    p=argparse.ArgumentParser();p.add_argument('--controls',action='store_true');p.add_argument('--publish',action='store_true');a=p.parse_args()
    host();m=pins();OUT.mkdir(exist_ok=False)
    result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],run_id=os.environ['GITHUB_RUN_ID'],
        new_simulation=False,cdr_accepted=False,full_phy_accepted=False)
    try:
        if a.controls:result.update(controls());return
        assert a.publish
        tag,head=publication.context(GROUP,os.environ)
        pr=publication.validate_release(publication.api('releases/tags/'+tag),publication.api('git/ref/tags/'+tag),tag,head)
        assert not pr['existing_assets']
        run=api('actions/runs/'+str(RUN));job=api('actions/jobs/'+str(JOB));ar=api('actions/artifacts/'+str(ARTIFACT));identity(run,job,ar)
        log=api('actions/jobs/'+str(JOB)+'/logs',True);log_identity(log);(OUT/'original-job.log').write_bytes(log)
        archive=OUT/'verified-artifact.zip'
        with archive.open('xb')as f:
            q=subprocess.run(['gh','api','--allow-escape-sequences','repos/'+REPO+'/actions/artifacts/'+str(ARTIFACT)+'/zip'],stdout=f)
        assert q.returncode==0 and archive.stat().st_size==ZIP_BYTES and sha_file(archive)==ZIP_SHA
        original=original_result(archive);expected=report_identity(original)
        keep={n for n in expected if n.endswith('.json')};restored=OUT/'verified-json';restored.mkdir()
        proof=scan_archive(archive,expected,ZIP_BYTES,ZIP_SHA,restored,keep)
        assert json.loads((restored/'result.json').read_text())==original
        summaries=[]
        for c in original['cases']:
            name=c['case'];folder=restored/name
            assert json.loads((folder/'selected-native.json').read_text())==c['selected_cache']
            assert proof['files'][name+'/selected-native.bin']['bytes']==c['selected_cache']['bytes']
            prior=json.loads((folder/'source-summary.json').read_text())
            assert prior['status']=='REJECTED_WHOLE_MIM_PD500_LOADED'and prior['case']==name and not prior['accepted']
            assert prior['source_head']==c['source_head']and prior['raw_capture']==c['raw_capture']
            reproduced=json.loads((folder/'original-measurements-reproduced.json').read_text())
            assert set(reproduced)==set(c['original_measurement_keys'])and all(prior[k]==v for k,v in reproduced.items())
            assert not reproduced['devices_passed']and not reproduced['data_passed']and not reproduced['vi']['passed']
            d=json.loads((folder/'diagnosis.json').read_text());summaries.append(diagnostic_summary(d,name));del d
        pins()
        # Full source JSONs become standalone immutable release assets. Do not duplicate caches or archive.
        publication_assets=[]
        for n in sorted(keep):
            target=OUT/('cdr-v58-'+n.replace('/','--'))
            target.write_bytes((restored/n).read_bytes());assert sha_file(target)==expected[n]
            publication_assets.append(dict(name=target.name,original_member=n,bytes=target.stat().st_size,sha256=expected[n]))
        result.update(status=STATUS,original_run=run,original_job=job,artifact=ar,archive_proof=proof,
            original_result=original,all_case_summaries=summaries,publication_assets=publication_assets,
            original_rejections_preserved=True,source_bytes_unchanged=True,cache_republished=False)
        archive.unlink()
    except BaseException as e:result.update(status='FAIL_OR_ERROR',error=repr(e),traceback=traceback.format_exc());raise
    finally:emit(result)
if __name__=='__main__':main()
