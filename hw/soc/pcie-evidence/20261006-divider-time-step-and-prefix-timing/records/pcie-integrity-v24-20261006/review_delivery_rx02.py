# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent finite saved-member/source/control review; no native rerun."""
import collections
import hashlib
import json
from pathlib import Path
import tarfile
import xml.etree.ElementTree as ET

R=Path('/home/hasanmelih/Documents/ChatGPT/nnsoc')
B=Path(__file__).resolve().parent
O=B/'delivery02'
O.mkdir(exist_ok=False)


def pin(p):
    p=Path(p)
    with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())


def j(p):return json.loads(p.read_text())


def save(p,v):
    with p.open('x')as f:json.dump(v,f,indent=2);f.write('\n')


def counts(p):
    cases=list(ET.parse(p).iter('testcase'))
    return dict(passed=sum(not any(c.find(t)is not None for t in ('failure','error','skipped'))for c in cases),
                failed=sum(any(c.find(t)is not None for t in ('failure','error'))for c in cases),
                skipped=sum(c.find('skipped')is not None for c in cases),cases=[c.attrib for c in cases])


source=j(B/'source-freeze03.json')
for collection in ('product_sources','sources'):
    for p,h in source[collection].items():assert pin(R/p)==h,p
assert len(source['product_sources'])==10 and source['excluded_MAX4118_predicates']==2
sourcepeer=j(B/'source-only-peer-vco03.json')
assert sourcepeer['freeze']==pin(B/'source-freeze03.json')and sourcepeer['findings']==[]
nativepeer=j(B/'native-saved-peer-vco.json')
assert nativepeer['status']=='PASS_SAVED_V24_FINITE_NATIVE_RECOUNT_TIMING_REJECTED'and not nativepeer['findings']
assert nativepeer['validation']==pin(B/'pcie-integrity-v24-native-validation-20261006.json')
for p,h in nativepeer['source_receipts'].items():assert pin(p)==h,p
policy=j(B/'continuation-policy01.json')
assert nativepeer['policy']==pin(B/'continuation-policy01.json')
component=j(B/'component-validation01.json')
controls=j(B/'pcie-integrity-v24-composite-controls-validation-20261006.json')
native=j(B/'pcie-integrity-v24-native-validation-20261006.json')
finalhist=j(B/'controls01-final-validation.json')
initialhist=j(B/'controls01-initial-seal-correction.json')
definitions=[('component',component['archive'],True),('controls',controls['archive'],True),
             ('native',native['archive'],True),('history_final',finalhist['archive'],False),
             ('history_initial',initialhist['original_archive'],False)]
# Enumerated chronological snapshots only; every other original remains strict.
drift_inventory=j(B/'delivery01/member-original-drift-inventory01.json')
assert len(drift_inventory)==8
allowed={(x['archive'],x['member']):x for x in drift_inventory}
for p,h in policy['method_pins'].items():assert pin(p)==h
with tarfile.open(B/'pcie-integrity-v24-composite-controls-20261006.tar.xz')as t:
    old_timing=t.extractfile('evidence/review_timing.py').read().decode()
new_timing=(B/'review_timing.py').read_text()
extra="""previous23_path=B.parent / 'pcie-integrity-v23-20261006/timing-comparison.json'
assert hashlib.sha256(previous23_path.read_bytes()).hexdigest()=='88bb268620e50544e608cce9ec6b72848a4c80833045f1390d5165711df89ab9'
previous23=json.loads(previous23_path.read_text())
old23={(r['corner'],r['direction']):r['worst_slack_ns'] for r in previous23['groups'] if r['stage']=='PREPLACEMENT_REPAIRED'}
delta23={r['corner']+'_'+r['direction']:r['worst_slack_ns']-old23[r['corner'],r['direction']] for r in rows if r['stage']=='PREPLACEMENT_REPAIRED'}
"""
assert new_timing.count(extra)==1
assert new_timing.replace(extra,'').replace('delta_vs_v19=delta19, delta_vs_v23=delta23,','delta_vs_v19=delta19,')==old_timing
assert pin(B.parent/'pcie-integrity-v23-20261006/timing-comparison.json')['sha256']=='88bb268620e50544e608cce9ec6b72848a4c80833045f1390d5165711df89ab9'
assert pin(B/'source-before-diagnostic03/sw/tests/test_pcie_gen3_integrity_v24_miter.py')['sha256']=='585a46ae8c549ee0797679f7ca97863af59501a48515aa7e88d6a396d85a2f98'
archive_maps={};archive_records={};coverage=set();drifts=[]
for label,row,primary in definitions:
    p=Path(row['path']);assert pin(p)=={k:row[k]for k in ('bytes','sha256')}
    with tarfile.open(p,'r:xz')as t:
        manifest=json.load(t.extractfile('members.json'))
    seen={}
    with tarfile.open(p,'r|xz')as t:
        for member in t:
            assert member.isfile()and member.name not in seen
            expected=manifest.get(member.name)
            actual=dict(bytes=member.size,sha256=hashlib.file_digest(t.extractfile(member),'sha256').hexdigest())
            if expected is not None:assert actual=={k:expected[k]for k in ('bytes','sha256')},(label,member.name)
            else:assert member.name=='members.json'
            seen[member.name]=actual
    assert set(seen)==set(manifest)|{'members.json'}
    for name,h in manifest.items():
        original=Path(h.get('original',h.get('original_path')))
        if not original.exists()or pin(original)!={k:h[k]for k in ('bytes','sha256')}:
            drifts.append(dict(archive=label,member=name,original=str(original),saved_pin={k:h[k]for k in ('bytes','sha256')},current=pin(original)if original.exists()else None))
            d=allowed[(p.name,name)]
            assert d['saved']=={k:h[k]for k in ('bytes','sha256')}and d['current']==pin(original)and d['original']==str(original)
            if primary:assert label=='controls'and name=='evidence/review_timing.py'

    archive_maps[label]=manifest
    archive_records[label]=dict(path=str(p),**pin(p),member_count=len(seen),members=seen)
    if primary:coverage.update((h['bytes'],h['sha256'])for h in seen.values())

assert len(drifts)==8
# Retain any unique historical bytes not covered by the three final capsules.
# These are immutable snapshots under evidence, never active test discovery.
historical=[];unique=O/'historical-unique';unique.mkdir()
for label,row,primary in definitions:
    if primary:continue
    with tarfile.open(row['path'],'r|xz')as t:
        for member in t:
            h=archive_records[label]['members'][member.name];key=(h['bytes'],h['sha256'])
            if key in coverage:continue
            data=t.extractfile(member).read();assert hashlib.sha256(data).hexdigest()==h['sha256']
            dest=unique/(h['sha256']+'-'+Path(member.name).name)
            with dest.open('xb')as f:f.write(data)
            historical.append(dict(archive=label,member=member.name,path=str(dest),**h))
            coverage.add(key)

campaigns={name:counts(B/name)for name in ['component-controls01.xml','controls01.xml','controls03.xml']}
assert {k:campaigns['component-controls01.xml'][k]for k in ('passed','failed','skipped')}==dict(passed=5,failed=0,skipped=0)
assert {k:campaigns['controls01.xml'][k]for k in ('passed','failed','skipped')}==dict(passed=41,failed=1,skipped=0)
assert {k:campaigns['controls03.xml'][k]for k in ('passed','failed','skipped')}==dict(passed=2,failed=0,skipped=0)
assert controls['pytest_executions']==44 and controls['passed_executions']==43 and controls['historical_failed_executions']==1
assert controls['current_42_predicates_covered']and controls['MAX4118_excluded']
assert controls['public_profiles']==dict(direct=18,cycle_miter=18,unchanged_latency=True)
for row in controls['helper_receipts']:
    assert pin(row['path'])=={k:row[k]for k in ('bytes','sha256')}
for row in controls['meaningful_miter_mutants']:
    p=Path(row['path']);assert pin(p)=={k:row[k]for k in ('bytes','sha256')}
    assert 'FATAL:'in p.read_text()
target=controls['targeted_same_mutant_rejection'];p=Path(target['path'])
assert pin(p)=={k:target[k]for k in ('bytes','sha256')}
assert 'V24_CONTEXT_CONSUMED_MODE word=1'in p.read_text()and 'Time: 50000'in p.read_text()
for d in ['test_actual_wide_rx_full_posit0','test_v23_v24_cycle_exact_all_p0']:
    c=counts(Path('/dev/shm/nssoc-integrity-v24-full-controls01')/d/'capture/results.xml')
    assert {k:c[k]for k in ('passed','failed','skipped')}==dict(passed=18,failed=0,skipped=0)
status=j(B/'continuation-status01.json');assert len(status['stages'])==7 and all(x['returncode']==0 for x in status['stages'])
for row in [status['controller'],*[x['identity']for x in status['stages']]]:
    p=Path('/proc')/str(row['pid'])/'stat'
    assert not p.exists()or int(p.read_text().rsplit(')',1)[1].split()[19])!=int(row['start_ticks'])
decision=j(B/'candidate-decision.json')
assert decision['status']=='FINITE_NATIVE_SCREEN_COMPLETE_NOT_ADOPTED'and not decision['adopted']and not decision['physical_acceptance']
assert decision['setup_ns']==dict(slow=-3.634856,typical=-.827638,fast=.823255)
assert abs(decision['delta_vs_V23']['slow_max']+.443174)<1e-12
assert decision['native_cells']==98919 and decision['flops']==9490
record=dict(status='PASS_INDEPENDENT_V24_FINITE_DELIVERY_RECOUNT_REJECTED_CANDIDATE',
            method=pin(Path(__file__)),source_freeze=pin(B/'source-freeze03.json'),
            source_allowlist=source['product_sources'],archives=archive_records,
            historical_unique_snapshots=historical,historical_original_path_drifts=drifts,
            campaigns=campaigns,product_executions=44,product_passed=43,historical_host_failed=1,
            current_predicates_covered=42,excluded_MAX4118=2,component_controls_separate=5,
            native_saved_peer=pin(B/'native-saved-peer-vco.json'),source_peer=pin(B/'source-only-peer-vco03.json'),
            candidate_decision=decision,all_primary_archive_originals_rehashed=True,primary_archived_draft_replacement_explicit=True,findings=[],
            drift_inventory=pin(B/'delivery01/member-original-drift-inventory01.json'),
            draft_timing_change='Only exact source-pinned V23 comparator addition; parsing, constraints and acceptance untouched. Old draft remains inside controls capsule; final helper bound by native policy and native capsule.',
            all_five_archive_members_readback=True,no_native_executed=True,
            scope='Three final capsules fully read back against embedded member maps; all primary originals and ten final product sources rehashed, with exactly one archived pre-native timing-helper draft explicitly distinguished from the final native helper. Historical419-member captures remain byte-exact; unique historical snapshots retained additively. Original41PASS1hostFAIL plus2targetedPASS remains44 executions, never42clean executions. Seven closed native stages and rejected4ns preplacement values preserved. No mapped functional or routed timing/PHY acceptance.')
save(O/'saved-delivery-peer-rx02.json',record)
print(json.dumps(dict(peer=pin(O/'saved-delivery-peer-rx02.json'),members={k:v['member_count']for k,v in archive_records.items()},historical_unique=len(historical),historical_drifts=drifts),indent=2))
