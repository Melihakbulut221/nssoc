#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Create or verify this hosted job's immutable result release at its tested SHA."""
import argparse, copy, json, os, re, subprocess
REPO='Melihakbulut221/nssoc'
def context(group,env):
    assert env.get('GITHUB_ACTIONS')=='true'
    assert env['GITHUB_REPOSITORY']==REPO
    assert re.fullmatch(r'[a-z0-9_-]{1,80}',group)
    run,attempt,sha=env['GITHUB_RUN_ID'],env['GITHUB_RUN_ATTEMPT'],env['GITHUB_SHA']
    assert re.fullmatch(r'[1-9][0-9]*',run) and re.fullmatch(r'[1-9][0-9]*',attempt)
    assert re.fullmatch(r'[0-9a-f]{40}',sha)
    return 'cloud-results-'+run+'-'+attempt+'-'+group,sha
def api(path,missing=False):
    r=subprocess.run(['gh','api','repos/'+REPO+'/'+path],capture_output=True,text=True)
    if r.returncode:
        assert missing and '(HTTP 404)' in r.stderr, r.stderr
        body=json.loads(r.stdout)
        assert body['message']=='Not Found'
        return None
    return json.loads(r.stdout)
def validate_release(info,ref,tag,sha):
    assert info['tag_name']==tag and info['target_commitish']==sha
    assert info['draft'] is False and info['prerelease'] is True
    assert ref['ref']=='refs/tags/'+tag and ref['object']['type']=='commit'
    assert ref['object']['sha']==sha
    assets=info['assets']
    assert len({a['id']for a in assets})==len(assets)
    assert len({a['name']for a in assets})==len(assets)
    # Existing partial publication is preserved, never replaced or uploaded here.
    for a in assets:
        assert type(a['size'])is int and a['size']>=0
        assert isinstance(a.get('digest'),str) and re.fullmatch(r'sha256:[0-9a-f]{64}',a['digest'])
    return dict(tag=tag,tested_source=sha,release_id=info['id'],
        existing_assets=[dict(id=a['id'],name=a['name'],bytes=a['size'],digest=a['digest'])for a in assets],
        target_verified=True,assets_overwritten=False)
def ensure(group,env,read=api,create=None):
    tag,sha=context(group,env)
    info=read('releases/tags/'+tag,missing=True)
    if info is None:
        # A tag without a release is checked before create; never move any tag.
        prior=read('git/ref/tags/'+tag,missing=True)
        if prior is not None:
            assert prior['ref']=='refs/tags/'+tag
            assert prior['object']['type']=='commit' and prior['object']['sha']==sha
        if create is None:
            subprocess.run(['gh','release','create',tag,'-R',REPO,'--target',sha,
                '--prerelease','--latest=false','--title',tag,
                '--notes','Immutable hosted job evidence at the exact tested source. Failure evidence is retained; this release is not production signoff.'],check=True)
        else: create(tag,sha)
        info=read('releases/tags/'+tag)
    ref=read('git/ref/tags/'+tag)
    return validate_release(info,ref,tag,sha)
def controls():
    env=dict(GITHUB_ACTIONS='true',GITHUB_REPOSITORY=REPO,GITHUB_RUN_ID='123',
        GITHUB_RUN_ATTEMPT='1',GITHUB_SHA='a'*40)
    tag,sha=context('fixture',env);bad=[]
    info=dict(id=5,tag_name=tag,target_commitish=sha,draft=False,prerelease=True,
        assets=[dict(id=9,name='existing.summary.json',size=3,digest='sha256:'+'b'*64)])
    ref=dict(ref='refs/tags/'+tag,object=dict(type='commit',sha=sha,url='fixture'))
    positive=validate_release(info,ref,tag,sha)
    def reject(label,fn):
        try:fn()
        except (AssertionError,KeyError,ValueError):bad.append(label)
        else:raise AssertionError('Accepted publication fault '+label)
    for label,key,value in [('local-context','GITHUB_ACTIONS','false'),('other-repo','GITHUB_REPOSITORY','other/repo'),
        ('missing-source','GITHUB_SHA',''),('mutable-source','GITHUB_SHA','main'),
        ('invalid-run','GITHUB_RUN_ID','123/other'),('invalid-attempt','GITHUB_RUN_ATTEMPT','0')]:
        q=dict(env);q[key]=value;reject(label,lambda:context('fixture',q))
    reject('invalid-group',lambda:context('../escape',env))
    for label,mutate in [
        ('different-release-target',lambda i,r:i.__setitem__('target_commitish','c'*40)),
        ('different-tag-object',lambda i,r:r['object'].__setitem__('sha','c'*40)),
        ('annotated-tag',lambda i,r:r['object'].__setitem__('type','tag')),
        ('different-tag-name',lambda i,r:i.__setitem__('tag_name','other')),
        ('draft-release',lambda i,r:i.__setitem__('draft',True)),
        ('production-release',lambda i,r:i.__setitem__('prerelease',False)),
        ('duplicate-asset-name',lambda i,r:i['assets'].append(dict(i['assets'][0],id=10))),
        ('asset-digest-missing',lambda i,r:i['assets'][0].__setitem__('digest',None))]:
        i,r=copy.deepcopy((info,ref));mutate(i,r);reject(label,lambda:validate_release(i,r,tag,sha))
    calls=[]
    def existing(path,missing=False):return info if path.startswith('releases/')else ref
    assert ensure('fixture',env,existing,lambda *a:calls.append(a))==positive and not calls
    state={}
    def absent(path,missing=False):
        if not state:return None
        return dict(info,assets=[]) if path.startswith('releases/')else ref
    def create(t,s):assert(t,s)==(tag,sha);state['created']=True;calls.append((t,s))
    created=ensure('fixture',env,absent,create)
    assert calls==[(tag,sha)]and created['existing_assets']==[]
    wrong=dict(ref,object=dict(ref['object'],sha='c'*40))
    def wrong_tag(path,missing=False):return None if path.startswith('releases/')else wrong
    reject('preexisting-wrong-tag',lambda:ensure('fixture',env,wrong_tag,lambda *a:calls.append(a)))
    def denied(path,missing=False):raise AssertionError('HTTP 403')
    reject('read-denied-never-creates',lambda:ensure('fixture',env,denied,lambda *a:calls.append(a)))
    assert calls==[(tag,sha)]and len(bad)==17
    return dict(status='PASS_EXACT_TESTED_SOURCE_RELEASE_AND17_CONTROLS',rejected=bad,
        existing_partial_assets_preserved=True,existing_release_not_recreated=True,
        new_release_uses_tested_sha=True,no_permissions_expanded=True)
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true','Cloud-only'
    p=argparse.ArgumentParser();p.add_argument('--controls',action='store_true');p.add_argument('--group');a=p.parse_args()
    assert bool(a.controls)!=bool(a.group)
    print(json.dumps(controls() if a.controls else ensure(a.group,os.environ),indent=2),flush=True)
if __name__=='__main__':main()
