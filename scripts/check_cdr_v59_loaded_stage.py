#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted real file/pack/extract/publisher fixtures; all native verdict data is synthetic."""
import copy,io,json,os,tempfile,types
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch
import cloud_cdr_v59_loaded_stage as w

def result_fixture(case='nominal_early',prepare=False):
    result=dict(source_head='a'*40,case=case,sources_unchanged=True,source_bits=[0]*256,
      binding_controls=dict(rejected=list(range(13))),current_saved_input_integrity=dict(files=5549,all_hashes_unchanged=True),
      devices={str(i):{}for i in range(124)},mos_devices={str(i):{}for i in range(50)},native_caps={str(i):{}for i in range(7)},
      binding=dict(groups=dict(rppd={str(i):{}for i in range(98)},ptap1={str(i):{}for i in range(221)})),
      vector_census=dict(hbt_collector_currents=124,mos_drain_currents=50,total=174),vectors=['fixture'+str(i)for i in range(174)],
      accepted=False,qualified_pex=False,full_phy_accepted=False,cdr_accepted=False,closed_loop=False)
    if prepare:result.update(status='PASS_PD500_LOADED_PREPARATION_AND13_BINDING_CONTROLS_NO_TRANSIENT',transient_executed=False)
    else:result.update(status='PASS_WHOLE_MIM_PD500_LOADED_SCREEN_NOT_CLOSED_LOOP_OR_PHY_SIGNOFF',
      returncode=0,diagnostics=[],native_flags_verified=124,zero_source_op_maximum=0.,
      actual_fault_detected=case in ('clock_stopped','vi_bias_off'),devices_passed=True,data_passed=True,vi=dict(passed=True))
    return result

def controls():
    w.a.methods()
    env=dict(GITHUB_ACTIONS='true',RUNNER_ENVIRONMENT='github-hosted',GITHUB_REPOSITORY='Melihakbulut221/nssoc',
      GITHUB_RUN_ID='17',GITHUB_RUN_ATTEMPT='1',GITHUB_SHA='a'*40)
    rejected=[];positives=[]
    def refuse(label,fn,types_=(AssertionError,KeyError,ValueError,FileNotFoundError,FileExistsError,NotADirectoryError)):
        try:fn()
        except types_:rejected.append(label)
        else:raise AssertionError('Accepted '+label)
    with patch.dict(os.environ,env):
        for case,prepare in [('nominal_early',True),*[(c,False)for c in w.CASES]]:
            r=result_fixture(case,prepare);assert w.validate_result(r,case,prepare,0)
            positives.append('schema-'+case+('-prepare'if prepare else''))
        changes=[
          ('wrong-source',lambda r:r.update(source_head='b'*40)),
          ('wrong-case',lambda r:r.update(case='hot_early')),
          ('source-change',lambda r:r.update(sources_unchanged=False)),
          ('short-bits',lambda r:r['source_bits'].pop()),
          ('missing-binding-fault',lambda r:r['binding_controls']['rejected'].pop()),
          ('missing-input',lambda r:r['current_saved_input_integrity'].update(files=5548)),
          ('input-change',lambda r:r['current_saved_input_integrity'].update(all_hashes_unchanged=False)),
          ('missing-HBT',lambda r:r['devices'].pop('0')),
          ('missing-MOS',lambda r:r['mos_devices'].pop('0')),
          ('missing-MIM',lambda r:r['native_caps'].pop('0')),
          ('missing-rppd',lambda r:r['binding']['groups']['rppd'].pop('0')),
          ('missing-contact',lambda r:r['binding']['groups']['ptap1'].pop('0')),
          ('duplicate-vector',lambda r:r['vectors'].__setitem__(0,r['vectors'][1])),
          ('accepted',lambda r:r.update(accepted=True)),
          ('wrong-status',lambda r:r.update(status='RUNNING')),
          ('native-nonzero',lambda r:r.update(returncode=1)),
          ('native-diagnostics',lambda r:r.update(diagnostics=['warning'])),
          ('missing-OFF',lambda r:r.update(native_flags_verified=123)),
          ('nonzero-OP',lambda r:r.update(zero_source_op_maximum=1e-9)),
          ('failed-device',lambda r:r.update(devices_passed=False)),
          ('failed-data',lambda r:r.update(data_passed=False)),
          ('failed-VI',lambda r:r['vi'].update(passed=False)),
        ]
        for label,change in changes:
            r=result_fixture();change(r);refuse(label,lambda:w.validate_result(r,'nominal_early',False,0))
        refuse('controller-nonzero',lambda:w.validate_result(result_fixture(),'nominal_early',False,1))
        r=result_fixture('clock_stopped');r['actual_fault_detected']=False
        refuse('fault-not-detected',lambda:w.validate_result(r,'clock_stopped',False,0))
        r=result_fixture(prepare=True);r['transient_executed']=True
        refuse('preparation-ran-transient',lambda:w.validate_result(r,'nominal_early',True,0))
        # The original fault verdict deliberately differs from a normal-case safety verdict.
        r=result_fixture('clock_stopped');r.update(devices_passed=False,data_passed=False);r['vi']['passed']=False
        assert w.validate_result(r,'clock_stopped',False,0);positives.append('original-fault-verdict-preserved')
        with tempfile.TemporaryDirectory(prefix='cdr-v59-loaded-publication-')as folder:
            top=Path(folder);original_pack=w.pack
            def setup(label,status='REJECTED_WHOLE_MIM_PD500_LOADED',report=True):
                repo=top/label;repo.mkdir();root=repo/'cloud-cdr-v59-loaded-nominal_early';root.mkdir()
                (root/'native.log').write_bytes(bytes(range(256))*8);(root/'.hidden').write_bytes(b'exact hidden bytes')
                (root/'empty.log').write_bytes(b'');(root/'nested').mkdir();(root/'nested/partial.txt').write_text('partial evidence')
                if report:
                    inner=dict(status=status,error='original failure retained',accepted=False)
                    (root/'native-controller-result.json').write_text(json.dumps(inner)+'\n')
                    r=dict(status=status,source_head='a'*40,run_id=17,run_attempt=1,case='nominal_early',preparation_only=False,
                      native_case_passed=False,accepted=False,full_phy_accepted=False,cdr_accepted=False,qualified_pex=False)
                    if label=='oversize':r['synthetic_padding']='x'*(4*1024**2)
                    r['outputs']={str(p.relative_to(root)):w.a.sha(p)for p in root.rglob('*')if p.is_file()}
                    w.write(root/'result.json',r)
                return repo,root,repo/'hw/soc/out/cloud-cdr-v59-loaded-nominal_early-publication'
            def exercise(repo,root,out,change=None,expect_failure=False):
                group='cdr-v59-loaded-nominal_early';tag='cloud-results-17-1-'+group;uploads=[]
                info=dict(id=7,tag_name=tag,target_commitish='a'*40,draft=False,prerelease=True,assets=[])
                ref=dict(ref='refs/tags/'+tag,object=dict(type='commit',sha='a'*40))
                def api(path,missing=False):
                    if path=='releases/tags/'+tag:return copy.deepcopy(info)
                    if path=='git/ref/tags/'+tag:return copy.deepcopy(ref)
                    raise AssertionError('Unexpected remote operation '+path)
                def upload(argv,**kw):
                    assert argv[:4]==['gh','release','upload',tag]and '--clobber'not in argv
                    p=Path(argv[4]);assert p.parent==out and p.is_file()and not p.is_symlink()
                    info['assets'].append(dict(id=100+len(uploads),name=p.name,size=p.stat().st_size,
                      digest='sha256:'+w.a.sha(p),browser_download_url='https://example.invalid/'+p.name))
                    uploads.append(p.name);return types.SimpleNamespace(returncode=0)
                def packed(root,stem,out,size):
                    m=original_pack(root,stem,out,127)
                    if change is not None:change(root,out,stem,m)
                    return m
                previous=w.publisher.release
                with redirect_stdout(io.StringIO()),patch.object(w,'ROOT',repo),patch.object(w.a,'methods',lambda:{}),patch.object(w.waiter,'wait',lambda *args:dict(fixture=True)),patch.object(w.release,'api',api),patch.object(w.publisher.subprocess,'run',upload),patch.object(w,'pack',packed),patch.object(w.evidence,'emit',lambda *args:None):
                    if expect_failure:
                        refuse('publication-'+repo.name,lambda:w.publish_existing('nominal_early',False))
                        result=None;assert not uploads
                    else:result=w.publish_existing('nominal_early',False)
                assert w.publisher.release is previous
                return result,uploads
            for label,status,report in [('failed','REJECTED_WHOLE_MIM_PD500_LOADED',True),('interrupted','RUNNING',True),('missing','FAIL_BEFORE_NATIVE_CASE_RESULT',False),('oversize','REJECTED_WHOLE_MIM_PD500_LOADED',True)]:
                repo,root,out=setup(label,status,report);before={str(p.relative_to(root)):w.a.sha(p)for p in root.rglob('*')if p.is_file()}
                proof,uploads=exercise(repo,root,out);saved=json.loads((root/'result.json').read_bytes())
                assert saved['status']==status and saved['native_case_passed']is False
                assert all(w.a.sha(root/n)==h for n,h in before.items())
                stem='cdr-v59-loaded-nominal_early-17-1';m=json.loads((out/(stem+'.parts.json')).read_bytes())
                assert len(m['parts'])>1
                paths=[out/(stem+'.summary.json'),out/(stem+'.parts.json'),*[out/p['name']for p in m['parts']]]
                if report:paths.append(out/(stem+'.native-result.json'))
                assert uploads==[p.name for p in paths]
                expected={str(p.relative_to(root)):w.a.sha(p)for p in root.rglob('*')if p.is_file()}
                restored=repo/'exact-restored'
                # Actual qualified streaming extraction, complete member hashes and empty/hidden evidence.
                result=w.a.saved.exact_extract(m,out,restored,expected)
                assert result['regular_members']==len(expected)
                assert all((restored/n).read_bytes()==(root/n).read_bytes()for n in expected)
                assert (out/(stem+'.summary.json')).read_bytes()==(root/'result.json').read_bytes()
                assert proof['status']=='PASS_COMPLETE_CURRENT_V59_LOADED_EVIDENCE_PUBLISHED_NOT_ACCEPTANCE'
                positives.append('actual-pack-extract-publish-'+label)
            for label in ('attempt2','root-link','report-link','descendant-link','root-file','changed-original'):
                repo,root,out=setup(label)
                if label=='root-link':
                    real=repo/'real';root.rename(real);root.symlink_to(real,target_is_directory=True)
                elif label=='report-link':
                    real=repo/'saved-result.json';(root/'result.json').rename(real);(root/'result.json').symlink_to(real)
                elif label=='descendant-link':(root/'link').symlink_to(root/'native.log')
                elif label=='root-file':
                    real=repo/'real';root.rename(real);root.write_bytes(b'not directory')
                elif label=='changed-original':(root/'native.log').write_bytes(b'changed')
                with patch.dict(os.environ,{'GITHUB_RUN_ATTEMPT':'2'if label=='attempt2'else'1'}):exercise(repo,root,out,expect_failure=True)
                assert not out.exists()
            faults=[
              ('missing-part',lambda r,o,s,m:(o/m['parts'][0]['name']).unlink()),
              ('duplicate-part',lambda r,o,s,m:m['parts'].append(copy.deepcopy(m['parts'][0]))),
              ('changed-part',lambda r,o,s,m:(o/m['parts'][0]['name']).write_bytes(b'changed')),
              ('changed-digest',lambda r,o,s,m:m['parts'][0].update(sha256='0'*64)),
              ('wrong-directory',lambda r,o,s,m:m.update(source_directory='wrong')),
              ('changed-summary',lambda r,o,s,m:(o/(s+'.summary.json')).write_bytes(b'{}')),
              ('changed-manifest',lambda r,o,s,m:(o/(s+'.parts.json')).write_bytes(b'{}')),
            ]
            for label,change in faults:
                repo,root,out=setup(label);exercise(repo,root,out,change,True)
    assert len(positives)==16 and len(rejected)==38 and len(set(rejected))==38
    return dict(status='PASS_CURRENT_V59_LOADED_STAGE_AND_PUBLICATION_CONTROLS_NOT_NATIVE',
      positives=positives,rejected=rejected,native_verdict_fixtures_are_synthetic=True,
      actual_complete_archive_roundtrips=4,qualified_publisher_used_with_fake_remote_transport=True,
      simulator_or_prior_archive_accessed=False)
if __name__=='__main__':print(json.dumps(controls(),indent=2))
