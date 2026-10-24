#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Compare unchanged original CDR validation with the guarded read-only execution."""
import collections,datetime,hashlib,io,json,os,re,subprocess,tarfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-cdr-source-validation-comparison'
REPO='repos/Melihakbulut221/nssoc/'
def api(path):return json.loads(subprocess.check_output(['gh','api',REPO+path]))
def asset(a):return subprocess.check_output(['gh','api',REPO+'releases/assets/'+str(a),'-H','Accept: application/octet-stream'])
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT.mkdir(exist_ok=False)
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],native_started=False,full_phy_accepted=False,production_workflow_changed=False)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        sr=asset(668606063);parts=asset(668606187);packed=asset(668606276)
        assert sha(sr)=='04072bc5ef6e302b89ef04d82cb4b13e26493da5d111c1dbc5795e1b9f1d9fcf'
        assert sha(parts)=='fce7c590ff1d7c734ef86bcc07e0617bb73f38ede2044da7e73926881036e162'
        assert sha(packed)=='d8f801462edc9e5ff6b378142269ed3b94991b518e8372a8ac661e8173aebda2'
        proof=json.loads(sr);manifest=json.loads(parts)
        assert len(manifest['parts'])==1 and manifest['bytes']==len(packed)and manifest['sha256']==sha(packed)
        assert proof['source_head']=='4ffe7bec0549df950a0c81aea4b27495f7497bca'
        assert proof['status']=='PASS_READ_ONLY_UNIQUE_SOURCE_VALIDATION_AND_THREE_REAL_CORRUPTIONS'
        assert len(proof['faults'])==3 and all(c['rejected']for c in proof['faults'])
        positive=proof['positive']
        assert positive['every_distinct_validator_executed']and positive['all_read_files_unchanged']
        wanted=manifest['source_directory']+'/positive.log'
        with tarfile.open(fileobj=io.BytesIO(packed),mode='r:gz')as tar:
            members=[x for x in tar.getmembers()if x.name==wanted]
            assert len(members)==1 and members[0].isfile()
            fastlog=tar.extractfile(members[0]).read()
        job=api('actions/jobs/120331387449')
        original=api('actions/runs/39928714596')
        assert job['run_id']==39928714596 and job['status']=='completed'and job['conclusion']=='success'
        assert original['head_sha']=='a0ff9960d6fdad98aff8da7434f7c6e0d48add07'
        measured=next(x for x in job['steps']if x['name']=='Verify exact PD476 model, count and physical parallel-tail adaptation')
        assert measured['conclusion']=='success'
        oldtree=api('git/trees/'+original['head_sha']+'?recursive=1')
        fasttree=api('git/trees/'+proof['source_head']+'?recursive=1')
        assert not oldtree['truncated']and not fasttree['truncated']
        trees=[{x['path']:x['sha']for x in t['tree']if x['type']=='blob'}for t in (oldtree,fasttree)]
        for path in positive['protected_read_files']:
            assert path in trees[0]and trees[0][path]==trees[1][path],('Original input differs',path)
        oldlog=subprocess.check_output(['gh','api',REPO+'actions/jobs/120331387449/logs','--allow-escape-sequences'])
        def markers(log):
            rows=[]
            for line in log.decode().splitlines():
                match=re.search(r'(PASS[A-Z0-9_]*(?:[: ].*)?)$',line)
                if match:rows.append(match[1])
            return collections.Counter(rows)
        a,b=markers(fastlog),markers(oldlog)
        assert a and set(a)<=set(b),'Optimized checker success marker absent from original successful execution'
        assert all(b[k]>=a[k]for k in a)
        seconds=(datetime.datetime.fromisoformat(measured['completed_at'].replace('Z','+00:00'))-datetime.datetime.fromisoformat(measured['started_at'].replace('Z','+00:00'))).total_seconds()
        assert seconds>proof['positive_elapsed_s']>0
        r.update(status='PASS_SAME870_INPUTS_ALL_DISTINCT_VALIDATORS_AND_ORIGINAL_SUCCESS_MARKERS',
          original_run=39928714596,original_job=120331387449,original_head=original['head_sha'],
          optimized_run=39930946907,optimized_head=proof['source_head'],
          optimized_summary_sha256=sha(sr),original_job_log_sha256=sha(oldlog),
          identical_input_blob_count=len(positive['protected_read_files']),
          distinct_validators=len(positive['executed']),guarded_calls=sum(positive['calls'].values()),
          original_source_step_seconds=seconds,optimized_positive_seconds=proof['positive_elapsed_s'],
          timing_scope='Observed separate hosted jobs, not a guaranteed speedup. Original step also includes v41 adaptation verifier.',
          optimized_success_markers=dict(a),corresponding_original_marker_counts={k:b[k]for k in a},
          all_source_corruptions_rejected=proof['faults'],original_assertions_and_sources_unchanged=True,
          eligible_scope='Fresh read-only source preflight only; never cache native simulation or physical/electrical acceptance.',
          existing_live_jobs_preserved=True)
        (OUT/'original-source-job.log').write_bytes(oldlog)
        (OUT/'guarded-positive.log').write_bytes(fastlog)
    except BaseException as error:r.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:save()
if __name__=='__main__':main()
