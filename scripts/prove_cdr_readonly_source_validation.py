#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
import hashlib,json,os,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-cdr-readonly-source-validation'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT.mkdir(exist_ok=False)
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],native_started=False,full_phy_accepted=False,
           production_validator_changed=False)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    def run(label):
        env=dict(os.environ,NSSOC_VALIDATOR_REPORT=str(OUT/(label+'.json')),PYTHONDONTWRITEBYTECODE='1')
        started=time.monotonic()
        p=subprocess.run([sys.executable,str(ROOT/'scripts/run_cdr_readonly_source_validation.py')],capture_output=True,text=True,env=env,cwd=ROOT)
        (OUT/(label+'.log')).write_text(p.stdout+p.stderr)
        result=json.loads((OUT/(label+'.json')).read_text())
        return p.returncode,result,time.monotonic()-started
    save()
    try:
        rc,positive,elapsed=run('positive')
        r['positive']=positive;r['positive_elapsed_s']=elapsed;save()
        assert rc==0 and positive['status']=='PASS_EVERY_DISTINCT_READ_ONLY_SOURCE_VALIDATOR_ON_IMMUTABLE_INPUTS'
        assert positive['every_distinct_validator_executed']and positive['all_read_files_unchanged']
        assert any(n>1 for n in positive['calls'].values()),'No duplicate validation was observed'
        targets=[
         ('changed-original-gate-source','scripts/cloud_cdr_sampler_settling_v32_mim_streamed.py'),
         ('changed-physical-source','scripts/cloud_cdr_sampler_settling_v32_mim_parent_rc.py'),
         ('changed-native-receipt','docs/evidence/cdr-sampler-settling-v32-planes-pass-20261022.json')]
        r['faults']=[]
        for label,name in targets:
            p=ROOT/name;before=p.read_bytes()
            try:
                if name.endswith('.py'):p.write_bytes(before+b'\n# explicit corruption control\n')
                else:
                    d=json.loads(before);d['summary_sha256']='0'*64
                    p.write_text(json.dumps(d,indent=2)+'\n')
                assert p.read_bytes()!=before
                rc,rejected,elapsed=run(label)
                r['faults'].append(dict(name=label,source=name,rejected=rc!=0 and rejected['status']=='FAIL_READ_ONLY_SOURCE_VALIDATION',
                    error=rejected.get('error'),elapsed_s=elapsed))
                save()
                assert r['faults'][-1]['rejected'],'Changed source accepted'
            finally:
                p.write_bytes(before);assert p.read_bytes()==before
        assert all(sha(ROOT/p)==h for p,h in positive['protected_read_files'].items())
        r.update(status='PASS_READ_ONLY_UNIQUE_SOURCE_VALIDATION_AND_THREE_REAL_CORRUPTIONS',
            protected_sources_restored=True,all_distinct_original_assertions_executed=True,
            no_native_or_electrical_result_cached=True,production_adoption_pending=True)
    except BaseException as error:r.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:save()
if __name__=='__main__':main()
