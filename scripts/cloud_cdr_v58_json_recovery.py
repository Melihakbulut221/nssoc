#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Recover the exact JSON-only CDR fallback; no cache, simulator, or waveform replay."""
import argparse,base64,collections,copy,hashlib,json,math,os,re,subprocess,tempfile,traceback,zipfile
from pathlib import Path
import cloud_cdr_v58_diagnostic_publication as original
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-cdr-v58-json-recovery'
METHOD=ROOT/'scripts/cdr-v58-json-recovery-methods.json'
GROUP='cdr-v58-json-recovery'
RUN=40124538661
ATTEMPT=2
HEAD='849cf464829e778753839bfde037234f41adba2f'
JOB=120963922485
ARTIFACT=12572830573
ZIP_BYTES=92897707
ZIP_SHA='d1dafe2abeb00da5260b98cc54d989cec11a4006fb9ae11bacfb020b41b5c94e'
LOG_BYTES=26492
LOG_SHA='3b91ffb3813da6e0627b23f51d9ecb05c248089f093af7c30ee2f9a672c26280'
STATUS='PASS_COMPLETE_ORIGINAL_CDR_JSONS_AND_LOSSLESS_CASE_SUMMARIES_COMPACT_INDEX_ONLY'
LIMIT=8*1024**2
def pins():
    m=json.loads(METHOD.read_text())
    for p,h in m['protected'].items():assert original.sha_file(ROOT/p)==h,p
    original.pins()
    return m
def identity(run,job,artifact):
    assert run['id']==RUN and run['run_attempt']==ATTEMPT and run['head_sha']==HEAD
    assert run['status']=='completed'and run['conclusion']=='failure'
    assert run['head_branch']=='codex/cdr-v58-saved-capture-diagnosis'
    assert run['path']=='.github/workflows/cdr-v58-diagnostic-publication-cloud.yml'
    assert job['id']==JOB and job['run_id']==RUN and job['run_attempt']==ATTEMPT and job['head_sha']==HEAD
    assert job['name']=='authenticate-and-publish'and job['status']=='completed'and job['conclusion']=='failure'
    assert artifact['id']==ARTIFACT and artifact['name']=='cdr-v58-complete-diagnostic-jsons'and artifact['expired']is False
    assert artifact['size_in_bytes']==ZIP_BYTES and artifact['digest']=='sha256:'+ZIP_SHA
    w=artifact['workflow_run']
    assert w['id']==RUN and w['head_sha']==HEAD and w['head_branch']==run['head_branch']
    assert w['repository_id']==w['head_repository_id']==1364721142
def failed_log(data):
    assert len(data)==LOG_BYTES and original.sha_bytes(data)==LOG_SHA
    text=data.decode()
    assert 'Summary too large; never silently truncate'in text and 'line 228, in emit'in text
    assert 'With the provided path, there will be 17 files uploaded'in text
    assert 'Artifact ID '+str(ARTIFACT)in text and 'SHA256 digest of uploaded artifact zip is '+ZIP_SHA in text
    assert 'PUBLICATION_RESULT_BASE64 'not in text
def prerequisite():
    # Attempt endpoint remains immutable even if a later attempt is ever created.
    run=original.api('actions/runs/'+str(RUN)+'/attempts/'+str(ATTEMPT))
    job=original.api('actions/jobs/'+str(JOB))
    artifact=original.api('actions/artifacts/'+str(ARTIFACT))
    identity(run,job,artifact)
    log=original.api('actions/jobs/'+str(JOB)+'/logs',True);failed_log(log)
    return run,job,artifact,log
def flat_members(expected):
    assert len(expected)==19 and expected['result.json']==original.RESULT_SHA
    exact={'result.json'}|{c+'/'+f for c in original.CASES for f in original.FILES}
    assert set(expected)==exact
    result={'cdr-v58-'+n.replace('/','--'):h for n,h in expected.items()if n.endswith('.json')}
    assert len(result)==16 and len(set(result))==16
    assert all(re.fullmatch('[0-9a-f]{64}',v)for v in result.values())
    result['original-job.log']=original.LOG_SHA
    return result
def root_report(path):
    with zipfile.ZipFile(path)as z:
        found=[i for i in z.infolist()if i.filename=='cdr-v58-result.json'];assert len(found)==1
        info=found[0];original.regular_name(info);assert not info.is_dir()and info.file_size==original.RESULT_BYTES
        b=z.read(info);assert len(b)==original.RESULT_BYTES and original.sha_bytes(b)==original.RESULT_SHA
    r=json.loads(b);return r,flat_members(original.report_identity(r))
def json_file(path,value):
    # Stream exact JSON to durable cloud output before applying any console bound.
    with path.open('x',encoding='utf-8')as f:
        for part in json.JSONEncoder(indent=2,allow_nan=False).iterencode(value):f.write(part)
        f.write('\n')
    return dict(name=path.name,bytes=path.stat().st_size,sha256=original.sha_file(path))
def relation_index(relation):
    assert relation['columns']==['a_index','b_index','b_minus_a_min_s','b_minus_a_max_s','ordering']
    rows=relation['all_existing_associations'];assert isinstance(rows,list)
    labels=('a_definitely_before_b','b_definitely_before_a','overlapping_native_brackets_order_ambiguous')
    h=hashlib.sha256();counts=collections.Counter();lo=hi=None
    for row in rows:
        assert len(row)==5 and all(type(row[i])is int and row[i]>=0 for i in (0,1))
        assert all(type(row[i])in (int,float)and math.isfinite(row[i])for i in (2,3))and row[2]<=row[3]
        assert row[4]in labels
        if row[4]=='a_definitely_before_b':assert row[2]>0
        elif row[4]=='b_definitely_before_a':assert row[3]<0
        else:assert row[2]<=0<=row[3]
        h.update((json.dumps(row,separators=(',',':'),allow_nan=False)+'\n').encode())
        counts[row[4]]+=1
        if lo is None or row[2]<lo[2]:lo=row
        if hi is None or row[3]>hi[3]:hi=row
    return dict(association_count=len(rows),ordering_counts=dict(counts),all_row_order_sha256=h.hexdigest(),
        minimum_interval_witness=lo,maximum_interval_witness=hi,
        full_rows_retained_in_case_summary=True,caveat=relation['caveat'])
def bit_index(bits):
    assert len(bits)==255 and [x['bit_index']for x in bits]==list(range(1,256))
    out=[]
    for x in bits:
        assert x['expected_bit']in(0,1)
        assert math.isfinite(x['ideal_source_edge_s'])and math.isfinite(x['original_clock_to_valid_s'])
        ev=x['native_100mV_crossings'];es=original.events_summary(ev)
        out.append(dict(bit_index=x['bit_index'],expected_bit=x['expected_bit'],ideal_source_edge_s=x['ideal_source_edge_s'],
            original_clock_to_valid_s=x['original_clock_to_valid_s'],last_bad_native_row=x['last_bad_native_row'],
            native_100mV_crossings=es,all_crossings_sha256=original.sha_bytes(json.dumps(ev,separators=(',',':'),allow_nan=False).encode()),
            all_crossings_retained_in_case_summary=True))
    return out
def compact_case(case,full_asset):
    # The unmodified original validator has already examined every association,
    # event, same-row sample and all255 bits. This is a separately labeled index.
    assert case['original_electrical_rejection_preserved']is True and case['diagnostic_only']is True
    assert all(case[k]is False for k in ('new_simulation','cdr_accepted','full_phy_accepted'))
    assert len(case['all32_clock_devices'])==32 and len(case['all32_shared_tail_combinations'])==32
    branches=[]
    for b in case['all32_shared_tail_combinations']:
        q={k:v for k,v in b.items()if k not in ('parent_to_base','base_to_collector')}
        q['parent_to_base']=relation_index(b['parent_to_base'])
        q['base_to_collector']=relation_index(b['base_to_collector'])
        branches.append(q)
    samplers={}
    assert set(case['all_sampler_bits'])==set('abcd')
    for name,s in case['all_sampler_bits'].items():
        samplers[name]=dict(all255_bit_indexes=bit_index(s['all_bits']),
            fixed_phase_native_margin_extrema=s['fixed_phase_native_margin_extrema'])
    return dict(case=case['case'],same_row_failed_devices=case['same_row_failed_devices'],
        parent_clock=case['parent_clock'],all32_clock_devices=case['all32_clock_devices'],
        all32_shared_tail_combination_indexes=branches,all_sampler_bit_indexes=samplers,
        complete_case_summary=full_asset,
        scope='Compact index. All original JSONs and complete unmodified derived case summaries are separate byte-hashed assets; no event or bit is dropped from those assets.',
        original_electrical_rejection_preserved=True,new_simulation=False,cdr_accepted=False,full_phy_accepted=False)
def emit(result):
    proof=json_file(OUT/'result.json',result)
    print('RECOVERY_RESULT_BYTES',proof['bytes'],flush=True);print('RECOVERY_RESULT_SHA256',proof['sha256'],flush=True)
    # Even an unexpected size failure leaves the complete actual JSON for fallback.
    assert proof['bytes']<=LIMIT,'Compact index too large; complete result already preserved'
    raw=(OUT/'result.json').read_bytes();s=base64.b64encode(raw).decode()
    parts=[s[i:i+4096]for i in range(0,len(s),4096)]
    for i,p in enumerate(parts):print(f'RECOVERY_RESULT_BASE64 {i}/{len(parts)} {p}',flush=True)
def controls():
    original.host();pins();run,job,artifact,log=prerequisite();faults=[]
    def reject(name,fn):
        try:fn()
        except (AssertionError,KeyError,ValueError,TypeError):faults.append(name)
        else:raise AssertionError('Accepted '+name)
    for which,key,value in [('run','head_sha','0'*40),('run','run_attempt',1),('run','conclusion','success'),
        ('job','id',1),('job','run_attempt',1),('job','name','readback'),('artifact','id',1),
        ('artifact','size_in_bytes',1),('artifact','digest','sha256:'+'0'*64),('artifact','expired',True)]:
        r,j,a=copy.deepcopy((run,job,artifact));{'run':r,'job':j,'artifact':a}[which][key]=value
        reject(which+'-'+key,lambda r=r,j=j,a=a:identity(r,j,a))
    reject('failure-log-truncated',lambda:failed_log(log[:-1]))
    noansi=re.sub(rb'\x1b\[[0-?]*[ -/]*[@-~]',b'',log);assert noansi!=log
    reject('failure-log-ANSI-removed',lambda:failed_log(noansi))
    expected={'result.json':original.RESULT_SHA}|{c+'/'+f:'a'*64 for c in original.CASES for f in original.FILES}
    assert len(flat_members(expected))==17
    for name,change in [('flat-missing',lambda e:e.pop('hot_early/diagnosis.json')),
        ('flat-extra',lambda e:e.update({'extra.json':'a'*64})),
        ('flat-root-hash',lambda e:e.update({'result.json':'0'*64})),
        ('flat-invalid-member-hash',lambda e:e.update({'hot_early/diagnosis.json':'invalid'}))]:
        e=copy.deepcopy(expected);change(e);reject(name,lambda e=e:flat_members(e))
    rel=dict(columns=['a_index','b_index','b_minus_a_min_s','b_minus_a_max_s','ordering'],
        all_existing_associations=[[0,0,1.,2.,'a_definitely_before_b'],[1,2,-1.,1.,'overlapping_native_brackets_order_ambiguous']],
        caveat='fixture')
    ix=relation_index(rel);assert ix['association_count']==2 and ix['minimum_interval_witness']==rel['all_existing_associations'][1]
    for name,change in [('relation-label',lambda r:r['all_existing_associations'][0].__setitem__(4,'unknown')),
        ('relation-nonfinite',lambda r:r['all_existing_associations'][0].__setitem__(2,float('nan'))),
        ('relation-wrong-order',lambda r:r['all_existing_associations'][0].__setitem__(4,'b_definitely_before_a')),
        ('relation-column',lambda r:r['columns'].__setitem__(0,'wrong'))]:
        r=copy.deepcopy(rel);change(r);reject(name,lambda r=r:relation_index(r))
    bits=[dict(bit_index=i,expected_bit=i%2,ideal_source_edge_s=float(i),
        original_clock_to_valid_s=0.,last_bad_native_row=None,native_100mV_crossings=[])for i in range(1,256)]
    assert len(bit_index(bits))==255
    bad=copy.deepcopy(bits);bad.pop();reject('missing-bit',lambda:bit_index(bad))
    bad=copy.deepcopy(bits);bad[0]['bit_index']=2;reject('reordered-bit',lambda:bit_index(bad))
    bad=copy.deepcopy(bits);bad[0]['expected_bit']=3;reject('invalid-bit',lambda:bit_index(bad))
    bad=copy.deepcopy(bits);bad[0]['original_clock_to_valid_s']=float('nan');reject('nonfinite-delay',lambda:bit_index(bad))
    with tempfile.TemporaryDirectory()as tmp:
        p=Path(tmp)/'complete.json';value={'value':'x'*4096}
        pr=json_file(p,value);assert json.loads(p.read_text())==value and pr['bytes']>1024
        # A small synthetic console bound must reject only after exact JSON exists.
        reject('size-bound-preserves-file',lambda:assert_limit(pr['bytes'],1024))
        assert original.sha_file(p)==pr['sha256']
    legacy=original.controls();assert len(legacy['faults'])==45 and len(legacy['publication_controls']['rejected'])==17
    assert len(faults)==25
    pins()
    return dict(status='PASS_JSON_ONLY_RECOVERY25_FAULTS_PLUS_ORIGINAL45_AND17_NO_ARCHIVE',
        faults=faults,original_controls=legacy,complete_json_written_before_console_limit=True,
        artifact_downloaded=False,new_simulation=False,cdr_accepted=False,full_phy_accepted=False)
def assert_limit(size,limit):assert size<=limit
def main():
    p=argparse.ArgumentParser();p.add_argument('--controls',action='store_true');p.add_argument('--publish',action='store_true');a=p.parse_args()
    original.host();pins();OUT.mkdir(exist_ok=False)
    result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],run_id=os.environ['GITHUB_RUN_ID'],
        new_simulation=False,cdr_accepted=False,full_phy_accepted=False,cache_restored=False,original_binary_rescan_performed=False)
    try:
        if a.controls:result.update(controls());return
        assert a.publish
        tag,head=original.publication.context(GROUP,os.environ)
        rel=original.publication.validate_release(original.publication.api('releases/tags/'+tag),original.publication.api('git/ref/tags/'+tag),tag,head)
        assert not rel['existing_assets']
        run,job,artifact,log=prerequisite();(OUT/'failed-publication-job.log').write_bytes(log)
        # Preserve the original full-capture reader identity/rejection as well.
        original.identity(original.api('actions/runs/'+str(original.RUN)),original.api('actions/jobs/'+str(original.JOB)),
                          original.api('actions/artifacts/'+str(original.ARTIFACT)))
        archive=OUT/'json-fallback.zip'
        with archive.open('xb')as f:
            q=subprocess.run(['gh','api','--allow-escape-sequences','repos/'+original.REPO+'/actions/artifacts/'+str(ARTIFACT)+'/zip'],stdout=f)
        assert q.returncode==0 and archive.stat().st_size==ZIP_BYTES and original.sha_file(archive)==ZIP_SHA
        report,expected=root_report(archive)
        restored=OUT/'verified-json';restored.mkdir()
        proof=original.scan_archive(archive,expected,ZIP_BYTES,ZIP_SHA,restored,set(expected))
        original.log_identity((restored/'original-job.log').read_bytes())
        for n,h in expected.items():
            dest=OUT/n;dest.write_bytes((restored/n).read_bytes());assert original.sha_file(dest)==h
        case_indexes=[];full_summaries=[]
        for case in report['cases']:
            name=case['case'];prefix='cdr-v58-'+name+'--'
            prior=json.loads((restored/(prefix+'source-summary.json')).read_text())
            assert prior['status']=='REJECTED_WHOLE_MIM_PD500_LOADED'and prior['case']==name and not prior['accepted']
            assert prior['source_head']==case['source_head']and prior['raw_capture']==case['raw_capture']
            reproduced=json.loads((restored/(prefix+'original-measurements-reproduced.json')).read_text())
            assert set(reproduced)==set(case['original_measurement_keys'])and all(prior[k]==v for k,v in reproduced.items())
            assert not reproduced['devices_passed']and not reproduced['data_passed']and not reproduced['vi']['passed']
            assert json.loads((restored/(prefix+'selected-native.json')).read_text())==case['selected_cache']
            diagnosis=json.loads((restored/(prefix+'diagnosis.json')).read_text())
            summary=original.diagnostic_summary(diagnosis,name);del diagnosis
            full=json_file(OUT/(prefix+'complete-derived-summary.json'),summary)
            case_indexes.append(compact_case(summary,full));full_summaries.append(full);del summary
        pins()
        outputs=[dict(name=n,bytes=(OUT/n).stat().st_size,sha256=h)for n,h in sorted(expected.items())]
        result.update(status=STATUS,recovered_from=dict(run=RUN,attempt=ATTEMPT,job=JOB,head=HEAD,artifact=ARTIFACT),
            archive_proof=proof,original_result_sha256=original.RESULT_SHA,
            original_electrical_rejections_authoritative=True,all_original_jsons_byte_identical=True,
            original_json_and_log_assets=outputs,complete_derived_case_summaries=full_summaries,
            compact_case_indexes=case_indexes,full_associations_and_bits_retained=True,
            original_selected_binary_verification_source=dict(run=original.RUN,head=original.HEAD,attempt=1),
            original_binary_rescan_performed=False)
        archive.unlink()
    except BaseException as e:result.update(status='FAIL_OR_ERROR',error=repr(e),traceback=traceback.format_exc());raise
    finally:emit(result)
if __name__=='__main__':main()
