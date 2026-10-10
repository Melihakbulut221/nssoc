# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent bounded saved archive/origin/transport recount; never EDA/network."""
from pathlib import Path
import collections
import gzip
import hashlib
import json
import lzma
import os
import resource
import tarfile
import xml.etree.ElementTree as ET

resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,)*2)
resource.setrlimit(resource.RLIMIT_CORE,(0,0))
assert os.sched_getaffinity(0)=={2}
R=Path.cwd()
B=R/'hw/soc/out/pcie-integrity-v25-20261006'
S=Path(__file__).resolve().parent
checked={}


def digest(stream):
    h=hashlib.sha256();size=0
    while data:=stream.read(1024*1024):h.update(data);size+=len(data)
    return dict(bytes=size,sha256=h.hexdigest())


def pin(path):
    p=Path(path)
    with p.open('rb') as f:actual=digest(f)
    checked[str(p)]=actual
    return actual


def check(path,expected):
    value=pin(path)
    assert value=={k:expected[k] for k in ('bytes','sha256')},str(path)
    return value


def read(path,expected=None):
    p=Path(path)
    if expected is None:pin(p)
    else:check(p,expected)
    return json.loads(p.read_text())


def xml_count(path):
    root=ET.parse(path).getroot();cases=list(root.iter('testcase'))
    failures=sum(x.find('failure') is not None or x.find('error') is not None for x in cases)
    skipped=sum(x.find('skipped') is not None for x in cases)
    return dict(passed=len(cases)-failures-skipped,failed=failures,skipped=skipped,total=len(cases))


def archive(label,row):
    path=Path(row['path']);check(path,row)
    mp=Path(row['manifest']['path']);manifest=read(mp,row['manifest'])
    if 'validation' in row:check(row['validation']['path'],row['validation'])
    seen=set();total=0;drifts=[];xml=[];manifest_members=[]
    with lzma.open(path,'rb') as payload,tarfile.open(fileobj=payload,mode='r|') as tar:
        for m in tar:
            assert m.isfile() and m.name not in seen and not m.name.startswith('/') and '..' not in Path(m.name).parts
            seen.add(m.name);f=tar.extractfile(m);actual=digest(f)
            assert actual['bytes']==m.size;total+=m.size
            if m.name not in manifest:
                assert actual==pin(mp),'extra_manifest_member'
                manifest_members.append(m.name);continue
            expected=manifest[m.name];assert actual=={k:expected[k] for k in ('bytes','sha256')},m.name
            origin=expected.get('original',expected.get('original_path'))
            assert origin, m.name
            current=pin(origin)
            if current!=actual:drifts.append(dict(member=m.name,original=origin,archived=actual,current=current))
            if m.name.endswith(('/controls01.xml','/controls02.xml')):xml.append(dict(member=m.name,origin=origin,counts=xml_count(origin)))
        # Force decoder to EOF/CRC even after tar zero end blocks.
        assert not payload.read().strip(b'\0'),'nonzero_tar_trailing_payload'
    assert set(manifest)<=seen and len(manifest_members)==1
    assert len(seen)==row['member_count'] and total==row['logical_bytes']
    assert sorted(drifts,key=lambda d:d['member'])==sorted(row['original_path_drifts'],key=lambda d:d['member'])
    print(json.dumps({'archive':label,'members':len(seen),'qualified_drifts':len(drifts)}),flush=True)
    return dict(archive=pin(path),manifest=pin(mp),members=len(seen),logical_bytes=total,qualified_drifts=drifts,
                embedded_manifest=manifest_members[0],xml=xml)


def main():
    ready=read(B/'ready-finite.json',{'bytes':79004,'sha256':'5d9d68875faabf629851b36f0a191c71fcbd4f052a41340a828da9c2bfb2d3eb'})
    assert ready['status']=='READY_V25_CURRENT43_NATIVE_TIMING_REJECTED_NOT_ADOPTED'
    assert not ready['adopted'] and not ready['physical_acceptance'] and ready['stable_baseline']=='V11'
    assert len(ready['source_allowlist'])==10 and len(ready['evidence'])==309
    for p,v in ready['source_allowlist'].items():check(R/p,v)
    for p,v in ready['evidence'].items():check(R/p,v)
    freeze=read(B/'source-freeze04.json',ready['source_freeze'])
    assert {str(R/p):v for p,v in ready['source_allowlist'].items()}==freeze['product_sources']
    audits={label:archive(label,row) for label,row in ready['archives'].items()}
    assert sum(x['members'] for x in audits.values())==ready['archive_total_members']==1562
    assert len(audits['historical_failed']['qualified_drifts'])==6
    assert all(not audits[k]['qualified_drifts'] for k in ('current_functional','native','peer_supplement'))
    counts=[x for label,a in audits.items() for x in a['xml'] if label in ('historical_failed','current_functional')]
    current=next(x for x in counts if x['member']=='current-evidence/controls02.xml')['counts']
    old=next(x for x in counts if x['member']=='evidence/controls01.xml')['counts']
    assert current==dict(passed=43,failed=0,skipped=0,total=43)
    assert old==dict(passed=40,failed=2,skipped=0,total=42)
    validation=read(B/'pcie-integrity-v25-current-controls02-validation-20261006.json',ready['functional_validation'])
    assert validation['current_pytest']==dict(passed=43,failed=0,skipped=0,deselected_MAX4118=1)
    assert validation['historical_pytest']==dict(passed=40,failed=2,skipped=0)
    assert validation['all_executions']==85 and validation['all_passed_executions']==83 and validation['all_retained_failed_executions']==2
    assert validation['public_profiles']==dict(direct=19,instrumented_transactions=19,nominal_plus_one_cases=2,general_cycle_equivalence=False)
    assert validation['component']['comparisons']==4102 and validation['component']['actual_faults']==12 and validation['component']['unknown_holds']==10
    decision=read(B/'candidate-decision.json');assert decision==ready['native']
    timing=read(B/'timing-comparison.json')
    for g in timing['groups']:
        assert min(g['all_group_slacks_ns'])==g['worst_slack_ns']
        if g['stage']=='PREPLACEMENT_REPAIRED':
            kind='setup_ns' if g['direction']=='max' else 'hold_ns'
            assert decision[kind][g['corner']]==g['worst_slack_ns']
    assert decision['setup_ns']['slow']==-3.421986 and decision['native_cells']==95243 and decision['flops']==9130
    assert abs(decision['delta_vs_V23']['slow_max']+.230304)<1e-12
    release=read(B/'publication-release01.json',ready['releases']['publication-release01.json'])
    assert release['status']=='PASS_IMMUTABLE_RELEASE_ROUNDTRIPS' and release['tag']=='evidence-20261006-pcie-closure'
    assert release['assets']==ready['assets'] and len(release['assets'])==5
    journal=read(B/'publication-release01.transport/attempts.json')
    saved=read(B/'publication-saved-recount01.json',ready['publication_saved_recount'])
    for p,v in saved['closed_transport_pins'].items():check(p,v)
    asset_by_name={a['name']:a for a in ready['assets']};roundtrips=[];closed=[]
    for attempt in journal:
        assert attempt['status']=='PASS' and attempt['returncode']==0 and not attempt['deadline_triggered']
        assert attempt['stdout_capture_complete'] and attempt['stderr_capture_complete'] and not attempt['stderr_limit_triggered']
        for channel in ('stdout','stderr'):
            record=attempt[channel];check(record['path'],record)
            with gzip.open(record['path'],'rb') as f:assert digest(f)==record['uncompressed']
        owner=read(attempt['owned_processes'])
        for process in owner['processes']:
            assert process['status']=='REAPED_NO_LIVE_MEMBERS' and process['returncode']==0 and process['members_at_leader_exit']==[]
            ident=process['identity'];p=Path(f'/proc/{ident["pid"]}/stat')
            assert not p.exists() or p.read_text().rsplit(')',1)[1].split()[19]!=ident['start_ticks']
            closed.append(ident)
        if attempt['kind'] not in ('authenticated','anonymous'):continue
        a=asset_by_name[attempt['asset']['name']]
        actual=check(attempt['retained_local_source']['path'],a)
        assert attempt['asset']['id']==a['asset_id'] and attempt['asset']['state']=='uploaded'
        assert attempt['asset']['size']==a['bytes'] and attempt['asset']['digest']=='sha256:'+a['sha256']
        observation=attempt['observed_download']
        assert {k:observation[k] for k in ('bytes','sha256')}==actual
        assert observation['matched_local_prefix_bytes']==actual['bytes'] and observation['mismatching_chunk'] is None
        if attempt['kind']=='anonymous':
            response=read(attempt['response']['path'],attempt['response'])
            assert response['status']=='COMPLETE_HTTP_STREAM' and response['http_status']==200
        roundtrips.append(dict(name=a['name'],kind=attempt['kind'],full_matched_local_prefix=actual,asset_id=a['asset_id']))
    assert len(journal)==25 and len(roundtrips)==10 and len(closed)==25
    assert collections.Counter((r['name'],r['kind']) for r in roundtrips)==collections.Counter((name,kind) for name in asset_by_name for kind in ('authenticated','anonymous'))
    check(B/'ready-finite.json',{'bytes':79004,'sha256':'5d9d68875faabf629851b36f0a191c71fcbd4f052a41340a828da9c2bfb2d3eb'})
    result=dict(status='PASS_INDEPENDENT_V25_FINITE_DELIVERY_SAVED_REVIEW',findings=[],ready=pin(B/'ready-finite.json'),
                products=10,compact_records=309,archives=audits,total_members=1562,current_pytest=current,historical_pytest=old,
                all_executions=85,all_passed_executions=83,retained_failed_executions=2,excluded_MAX4118=1,
                source_metadata_qualification=validation['metadata_correction'],
                native=decision,publication=dict(assets=5,attempts=25,failed_attempts=0,roundtrips=roundtrips,closed_processes=closed),
                checked_inputs=checked,method=pin(Path(__file__)),cpu=2,address_space_limit_bytes=2*1024**3,
                peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
                scope='Full saved streaming member hashes and origin recount; historical six drifts qualified exactly, current/native origins exact. Saved full-prefix authenticated/anonymous transport receipts reconstructed against complete local files, no fresh network. No HDL/EDA rerun or source change; functional43/current versus40/2 historical separate. SS timing rejected, no adoption.')
    (S/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'status':result['status'],'result':pin(S/'result.json'),'peak_rss_bytes':result['peak_rss_bytes']}),flush=True)


if __name__=='__main__':main()
