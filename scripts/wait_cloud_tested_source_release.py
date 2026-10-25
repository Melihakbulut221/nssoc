#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Wait for an externally reserved exact-source release; never create or move tags."""
import argparse,copy,json,os,time
import ensure_cloud_tested_source_release as release
ATTEMPTS=61
INTERVAL_S=5
def wait(group,env,read=release.api,pause=time.sleep,emit=print):
    tag,source=release.context(group,env)
    for attempt in range(ATTEMPTS):
        info=read('releases/tags/'+tag,missing=True)
        if info is not None:
            proof=release.validate_release(info,read('git/ref/tags/'+tag),tag,source)
            return dict(**proof,read_attempts=attempt+1,externally_reserved=True,creation_attempted=False)
        if attempt==ATTEMPTS-1:
            raise AssertionError('Exact-source release missing after61reads and300seconds of scheduled waits')
        emit('Waiting for externally reserved exact-source evidence release; native work has not started',flush=True)
        pause(INTERVAL_S)
def controls():
    env=dict(GITHUB_ACTIONS='true',GITHUB_REPOSITORY=release.REPO,GITHUB_RUN_ID='123',
      GITHUB_RUN_ATTEMPT='1',GITHUB_SHA='a'*40)
    tag,source=release.context('fixture',env)
    info=dict(id=5,tag_name=tag,target_commitish=source,draft=False,prerelease=True,
      assets=[dict(id=9,name='prior.json',size=3,digest='sha256:'+'b'*64)])
    ref=dict(ref='refs/tags/'+tag,object=dict(type='commit',sha=source))
    histories=[]
    for delay in (0,2,60):
        calls=[];pauses=[];seen=[0]
        def read(path,missing=False):
            calls.append((path,missing))
            if path.startswith('releases/'):
                seen[0]+=1
                return None if seen[0]<=delay else copy.deepcopy(info)
            return copy.deepcopy(ref)
        r=wait('fixture',env,read,pauses.append,lambda *a,**k:None)
        assert r['read_attempts']==delay+1 and r['existing_assets'][0]['id']==9
        assert r['creation_attempted']is False and r['externally_reserved']
        assert pauses==[5]*delay and len(calls)==delay+2
        histories.append(dict(absent_reads=delay,exact_release_accepted=True))
    rejected=[]
    def reject(name,read,expected_reads,expected_pauses):
        calls=[];pauses=[]
        def wrapped(path,missing=False):
            calls.append(path);return read(path,missing)
        try:wait('fixture',env,wrapped,pauses.append,lambda *a,**k:None)
        except AssertionError:rejected.append(name)
        else:raise AssertionError('Accepted '+name)
        assert len(calls)==expected_reads and pauses==[5]*expected_pauses
    reject('bounded-missing-reservation',lambda p,m:None,61,60)
    def denied(p,m):raise AssertionError('HTTP403')
    reject('API-denied-not-retried',denied,1,0)
    wrong=copy.deepcopy(info);wrong['target_commitish']='c'*40
    reject('different-release-source',lambda p,m:wrong if p.startswith('releases/')else ref,2,0)
    wrongref=copy.deepcopy(ref);wrongref['object']['sha']='c'*40
    reject('different-tag-object',lambda p,m:info if p.startswith('releases/')else wrongref,2,0)
    assert len(rejected)==4
    return dict(status='PASS_READ_ONLY_RELEASE_WAIT_CONTROLS',positive_cases=histories,rejected=rejected,
      maximum_missing_reads=61,maximum_scheduled_wait_s=300,creation_attempted=False,native_executed=False)
def main():
    p=argparse.ArgumentParser();p.add_argument('--controls',action='store_true');p.add_argument('--group');a=p.parse_args()
    assert bool(a.controls)!=bool(a.group)
    print(json.dumps(controls()if a.controls else wait(a.group,os.environ),indent=2))
if __name__=='__main__':main()
