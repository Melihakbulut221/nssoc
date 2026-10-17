#!/usr/bin/env python3
"""Independent six-source/compact-record/XML/public-receipt review; no network/native."""
from pathlib import Path
import ast
import collections
import gzip
import hashlib
import json
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

R=Path('/home/hasanmelih/Documents/ChatGPT/nnsoc')
B=R/'hw/soc/out/pcie-pll-local-spool-v1-20261006'
O=R/'hw/soc/out/pcie-phase35-delivery-20261006'
inputs={}
def pin(path):
    p=Path(path);p=p if p.is_absolute() else R/p
    h=hashlib.sha256();size=0
    with p.open('rb') as f:
        while b:=f.read(1024*1024):h.update(b);size+=len(b)
    v={'bytes':size,'sha256':h.hexdigest()};inputs[str(p)]=v;return v

def bind(path,expected):
    actual=pin(path)
    assert all(actual[k]==expected[k] for k in ('bytes','sha256')),(str(path),actual,expected)
    return actual

def read(path):
    p=Path(path);p=p if p.is_absolute() else R/p
    pin(p);return json.loads(p.read_text())

ready=read(B/'ready-finite.json')
assert pin(B/'ready-finite.json')=={'bytes':30056,'sha256':'6e6d8ab24579f5336b54e55f2b0c2954350aab4678e84fbf426aea550c85ef71'}
assert len(ready['source_allowlist'])==6 and len(ready['evidence'])==125
for p,q in (ready['source_allowlist']|ready['evidence']).items():bind(p,q)
freeze=read(B/'source-freeze02.json');bind(B/'source-freeze02.json',ready['source_freeze'])
assert {str(Path(x['path']).relative_to(R)):{k:x[k] for k in ('bytes','sha256')} for x in freeze['sources']}==ready['source_allowlist']
for name in ready['source_allowlist']:
    ast.parse((R/name).read_text())
assert ready['native_completion'] is False and ready['numerical_convergence'] is False and ready['physical_acceptance'] is False

package=read(ready['finite_package']['path']);bind(ready['finite_package']['path'],ready['finite_package'])
assert package['source_allowlist']==ready['source_allowlist']
assert package['active_native_excluded'] and package['active_publication_excluded']
validation=read(B/'finite01/pcie-pll-local-spool-v1-controls-and-launch-validation-20261006.json')
peer=read(ready['saved_delivery_peer']['path']);bind(ready['saved_delivery_peer']['path'],ready['saved_delivery_peer'])
assert peer['findings']==[] and peer['readback_members']==3967 and peer['logical_data_bytes']==3132649663
assert peer['source_files']==6 and peer['total_executions']==303 and peer['total_historical_failures']==2
assert validation['member_count']==ready['archive_total_members']==3967
assert validation['logical_data_bytes']==ready['full_logical_data_bytes']==3132649663
archive=ready['archives']['controls_and_launch'];bind(archive['path'],archive)
assert all(archive[k]==peer['archive'][k]==validation['archive'][k] for k in ('bytes','sha256'))
members=read(validation['members']['path']);bind(validation['members']['path'],validation['members'])
assert len(members['files'])==3966
assert sum(x['bytes'] for x in members['files'].values())==3132649663
excluded_roots=[Path(p) for p in members['excluded_active_roots']]
excluded_files={Path(p) for p in members['excluded_active_paths']}
assert Path(ready['active_native_checkpoint']) in excluded_files
for row in members['files'].values():
    p=Path(row['path'])
    assert p not in excluded_files and not any(p.is_relative_to(root) for root in excluded_roots),p

campaigns=[];all_cases=[];current={};historical_failures=[]
for row in validation['campaigns']:
    path=B/(row['name']+'.xml');pin(path)
    cases=list(ET.parse(path).getroot().iter('testcase'))
    passed=failed=skipped=0
    for c in cases:
        key=(c.get('classname'),c.get('name'))
        if any(x.tag in ('failure','error') for x in c):
            failed+=1
            historical_failures.append({'campaign':row['name'],'module':key[0],'name':key[1],'diagnostics':[x.text for x in c if x.tag in ('failure','error')]})
        elif any(x.tag=='skipped' for x in c):skipped+=1
        else:passed+=1
        if row['name'] in ('complete-controls03','bridge-controls05'):
            assert not any(x.tag in ('failure','error','skipped') for x in c)
            current[key]=row['name']
    actual=dict(name=row['name'],cases=len(cases),passed=passed,failed=failed,skipped=skipped)
    assert actual==row
    campaigns.append(actual);all_cases.extend(cases)
assert len(all_cases)==303 and len(historical_failures)==2
assert sum(x['passed'] for x in campaigns)==301
assert all('Explicit owned process kind' in ''.join(x['diagnostics']) for x in historical_failures)
assert len(current)==69
counts=dict(collections.Counter(x[0] for x in current))
assert counts=={'sw.tests.test_pcie_durable_spool_v1':30,'sw.tests.test_pcie_pll_local_capture_v1':18,'sw.tests.test_pcie_local_spool_publisher_v1':21}
assert set(current)=={(x['module'],x['name']) for x in peer['current_actual_xml_predicates']}
aggregate=read(B/'source-saved-peer-root02.json');bind(B/'source-saved-peer-root02.json',ready['source_peer'])
assert aggregate['findings']==[] and aggregate['freeze']==ready['source_freeze'] and aggregate['distinct_current_predicates']==69
bind(B/'launch01/source-peer-vco01.json',ready['support_peer'])

release_path=next(iter(ready['releases']));release=read(release_path);bind(release_path,ready['releases'][release_path])
assert release['status']=='PASS_IMMUTABLE_RELEASE_ROUNDTRIPS' and release['publisher_revision']==4
assert release['tag']=='evidence-20261006-pcie-closure' and len(release['assets'])==3
assert release['assets']==ready['assets']
for f in release['files']:bind(f['path'],f)
for asset in release['assets']:
    matches=[f for f in release['files'] if f['name']==asset['name']]
    assert len(matches)==1 and all(asset[k]==matches[0][k] for k in ('bytes','sha256'))
    assert asset['authenticated_roundtrip'] and asset['anonymous_roundtrip']
journal=read(release['transport_journal']['path']);bind(release['transport_journal']['path'],release['transport_journal'])
assert len(journal)==15
closed_processes=[];downloads=[]
for a in journal:
    assert a['status']=='PASS' and a['returncode']==0 and not a['deadline_triggered']
    for name in ('stdout','stderr'):
        b=a[name];bind(b['path'],b)
        data=gzip.decompress(Path(b['path']).read_bytes())
        assert {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}==b['uncompressed']
    owned=read(a['owned_processes'])
    assert owned['status']=='HEALTHY'
    for p in owned['processes']:
        assert p['status']=='REAPED_NO_LIVE_MEMBERS' and p['returncode']==0 and p['members_at_leader_exit']==[]
        closed_processes.append(p['identity'])
    if a['kind'] in ('authenticated','anonymous'):
        observed=a['observed_download'];source=a['retained_local_source'];bind(source['path'],source)
        assert all(observed[k]==source[k] for k in ('bytes','sha256'))
        assert observed['matched_local_prefix_bytes']==source['bytes'] and observed['mismatching_chunk'] is None
        asset=a['asset'];assert asset['digest']=='sha256:'+source['sha256'] and asset['size']==source['bytes'] and asset['state']=='uploaded'
        downloads.append({'kind':a['kind'],'asset_id':asset['id'],'name':asset['name'],'bytes':source['bytes'],'sha256':source['sha256']})
        if a['kind']=='anonymous':
            response=read(a['response']['path']);bind(a['response']['path'],a['response'])
assert len(downloads)==6
assert collections.Counter(x['name'] for x in downloads)==collections.Counter({a['name']:2 for a in ready['assets']})
assert len(closed_processes)==15
source_observations={
 'commit_order':'Complete part plus record fsync, directory rename/fsync, SSD canonical ledger atomic replacement before RAM pending bytes clear; staging/orphans exposed and retained.',
 'bounds':'10GiB separately allocated reserve; 8GiB payload+metadata; 1GiB continuous floor; 512part cap; worker512MiB/2048attempt bound. Not quota or unlimited outage tolerance.',
 'native_bridge':'Exact V4 source and local core hashes; explicit complete-body replacements preserve native physics, Meter/startup/threshold functions. Header prefix and native terminal files copied locally before invalid-manifest classification.',
 'worker':'Independent owner and separate output directory, actual byte/digest and dual-readback gates, transient TransportError retries only, preserved permanent failure. Stop shared through owner entry/exit; no native process adoption.',
 'limitations':'Completed committed parts are durable under explicit fsync protocol; file-fault fixtures are not empirical sudden-power-loss validation, pending RAM vulnerable. No solver checkpoint or native completion claim.'
}
result={
 'status':'PASS_INDEPENDENT_LOCAL_PLL_FINITE_SOURCES_RECORDS_AND_PUBLIC_RECEIPTS',
 'utc':datetime.now(timezone.utc).isoformat(),'findings':[],
 'ready':{'path':str(B/'ready-finite.json'),**pin(B/'ready-finite.json')},
 'method':{'path':str(Path(__file__)),**pin(__file__)},'inputs':inputs,
 'current_source_files':6,'compact_records_rehashed':125,
 'current_predicates':69,'current_counts':counts,'current_basis':'Complete03 core30+capture16+worker21; final Bridge05 all18 capture; unchanged final core/worker pinned by aggregate source review.',
 'historical_campaigns':campaigns,'historical_executions':303,'historical_passes':301,'historical_failures':historical_failures,
 'archive_members':3967,'logical_archive_data_bytes':3132649663,
 'archive_review':'Archive file hash and full member manifest count/size/exclusions checked here. Existing independent VCO streaming read of all3967 members and originals is rebound exactly; not duplicated.',
 'assets':ready['assets'],'closed_transport_process_receipts':len(closed_processes),'saved_download_recounts':downloads,
 'source_review':source_observations,
 'active_native_and_publication_excluded':True,'native_completion':False,'numerical_convergence':False,'physical_acceptance':False,
 'scope':'Independent full three production-source reread, exact six source and125compact hash bindings, actual12XML campaign/current69 recount, archive/manifest/peer binding and complete closed15-attempt publication receipts including6lossless download-prefix readbacks. No new network/EDA/tests/producer/native operation, live journal read, signal or Git edits.'
}
(O/'saved-finite-peer-rx01.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:result[k] for k in ('status','findings','current_source_files','compact_records_rehashed','current_predicates','historical_executions','historical_passes','archive_members','closed_transport_process_receipts')}))
