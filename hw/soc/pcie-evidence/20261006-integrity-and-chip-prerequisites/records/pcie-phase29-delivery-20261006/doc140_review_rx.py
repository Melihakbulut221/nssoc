#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Read-only document fact review; no EDA, test, producer or document edits."""
import datetime,hashlib,json,tarfile
from pathlib import Path
from collections import Counter
import xml.etree.ElementTree as ET
R=Path.cwd();B=R/'hw/soc/out/pcie-phase29-delivery-20261006'
V=R/'hw/soc/out/pcie-integrity-v22-20261006';N=R/'hw/soc/out/npu-eco-physical-readiness-20261006';P=R/'hw/soc/out/npu-eco-physical-runner-20261006'
D=R/'docs/140-pcie-integrity-and-chip-prerequisites.md'
def pin(p):
 p=Path(p)
 with p.open('rb') as f:return {'bytes':p.stat().st_size,'sha256':hashlib.file_digest(f,'sha256').hexdigest()}
evidence={}
def load(p):
 evidence[str(p.relative_to(R))]=pin(p);return json.loads(p.read_text())
closed=load(B/'closed-review01.json');v=load(V/'ready-finite.json');n=load(N/'ready-finite.json')
archives=[]
for a in closed['archives']:
 assert pin(a['path'])==a['pin']
 seen={}
 with tarfile.open(a['path'],'r|xz') as tar:
  for m in tar:
   assert m.isfile() and m.name not in seen
   seen[m.name]={'bytes':m.size,'sha256':hashlib.file_digest(tar.extractfile(m),'sha256').hexdigest()}
 assert seen==a['member_pins'] and len(seen)==a['members']
 archives.append({'path':a['path'],'pin':a['pin'],'members':len(seen),'full_independent_member_rehash':True})
assert len(archives)==4 and sum(a['members'] for a in archives)==874
for group in ('sources','compact'):
 for name,p in closed[group].items():assert pin(R/name)==p,name
freeze=load(P/'source-freeze03.json');peer=load(P/'source-only-peer-pll03.json')
assert peer['freeze']==pin(P/'source-freeze03.json') and peer['findings']==[]
for group in ('sources','dependencies'):
 for name,p in freeze[group].items():assert pin(name)==p,name
for name,p in freeze['controls'].items():assert pin(P/name)==p,name
assert len(set(closed['sources'])|{str(Path(x).relative_to(R)) for x in freeze['sources']})==14
controls=[]
for path,wanted in [(V/'controls01.xml',(26,3,0)),(V/'controls03.xml',(9,0,0)),(N/'controls01.xml',(47,0,0)),(N/'root-controls01.xml',(47,0,0)),(P/'controls03.xml',(57,0,0))]:
 cases=ET.parse(path).findall('.//testcase');bad=sum(c.find('failure') is not None or c.find('error') is not None for c in cases);skip=sum(c.find('skipped') is not None for c in cases);got=(len(cases)-bad-skip,bad,skip)
 assert got==wanted
 controls.append({'path':str(path.relative_to(R)),'pin':pin(path),'passed_failed_skipped':got})
validation=load(V/'pcie-integrity-v22-controls-validation-20261006.json');saved=load(V/'native-saved-peer-vco.json');timing=load(V/'timing-comparison.json');critical=load(V/'critical-path-attribution.json')
assert validation['pytest_executions']==38 and validation['pytest_passed_executions']==35 and validation['historical_failed_executions']==3
assert validation['public_positive_composite']=={'original_unchanged_cases':16,'targeted_corrected_case':1,'complete_direct_profile_rerun':False,'complete_cycle_miter_cases':17}
assert len(validation['meaningful_miter_mutants'])==6
for row in validation['meaningful_miter_mutants']:
 assert pin(row['path'])=={k:row[k] for k in ('bytes','sha256')}
 assert row['diagnostic'] in Path(row['path']).read_text()
assert v['controls']['cache_fault_epoch_witnesses']==[8,8,8] and v['controls']['literal_vectors']==4096
assert (saved['actual_native_cells'],saved['actual_native_FFs'])==(101044,9612)
slacks={f"{g['corner']}_{g['direction']}":min(g['all_group_slacks_ns']) for g in timing['groups'] if g['stage']=='PREPLACEMENT_REPAIRED'}
assert slacks==saved['repaired_slacks_ns']=={'slow_max':-3.544282,'slow_min':.370623,'typical_max':-.745996,'typical_min':.260212,'fast_max':.857332,'fast_min':.176}
assert round(saved['delta_SS_vs_V21_ns']*1000,3)==20.441 and round(timing['delta_vs_v17']['slow_max']*1000,3)==-207.999
assert critical['delay_by_cell_family']['buffer']['count']==19 and critical['delay_by_cell_family']['mux']['count']==7
counts=Counter(r['type'].split('_')[1] for r in critical['rows']);assert sum(1 for r in critical['rows'] if '_buf_' in r['type'])==19 and sum(1 for r in critical['rows'] if '_mux' in r['type'])==7
readiness=load(N/'readiness02.json');rp=load(N/'source-saved-peer-root01.json');correction=load(V/'observer-stimulus-correction03.json');oldfail=load(V/'failed-controls01-validation.json')
assert readiness['status']=='BLOCKED' and readiness['binary_relation']['counts']=={'prior':33517,'separate_hard':4,'grouped_new':800,'total':34321,'symbolic_inputs':10828,'batches':64}
assert not readiness['binary_relation']['original_full_graphs_replayed_locally']
assert len(rp['real_saved_catalog_negative_controls'])==3 and readiness['mapped_bridge']['binary_cases']==16
bundle=load(P/'bundle-preparation01.json');assert bundle['status']=='PASS_COMPLETE_PINNED_LOCAL_INPUT_BUNDLE_NO_EDA' and bundle['members']==5180 and bundle['runtime']['bytes']==1398053408 and not bundle['native_executed']
# Source/runtime preparation is scoped to a pinned completed receipt, not a new full 1.4GB restoration/replay.
assert Path(bundle['runtime']['path']).stat().st_size==1398053408
text=D.read_text();findings=[]
if 'sampled after nonblocking updates,\nwhich hid' in text:
 findings.append({'id':'witness-edge-order','severity':'documentation-factual-correction','lines':[30,31],'claim':'Initial witness sampled after nonblocking updates hid fault-state observation.','evidence':str((V/'observer-stimulus-correction03.json').relative_to(R)),'actual':'Old observer increments at following negedge; Ports.cycle returns2ns afterposedge and the assertion ran before that negedge. Corrected observer samples settled NBAs at posedge+0.002ns.','requested':'Explain late falling-edge counter update and the new same-rising-edge settled sample.'})
if 'profile is excluded from this finite V22 campaign and remains a separate job.' in text:
 findings.append({'id':'max4118-version-identity','severity':'documentation-scope-correction','lines':[41,42],'claim':'V22 maximum4118 profile remains a separate job.','evidence':str((V/'failed-controls01-validation.json').relative_to(R)),'actual':'Both V22 MAX4118 predicates are deselected/unrun. Current long MAX4118 campaign is V18 and cannot qualify V22.','requested':'State V22 MAX4118 predicates not run; explicitly label the separate running campaign V18.'})
assert not v['adopted'] and not v['physical_acceptance']
report={'status':'DOC140_REVIEW_REQUIRES_TWO_NARROW_WORDING_CORRECTIONS' if findings else 'PASS_DOC140_FACTS_AND_SCOPE','findings':findings,'document':{'path':str(D.relative_to(R)),**pin(D)},'method':pin(__file__),'utc':datetime.datetime.now(datetime.UTC).isoformat(),'fact_checks':{'delivery_sources':14,'archive_count':4,'archive_members':874,'V22_executions':38,'V22_passed':35,'V22_historical_failures':3,'V22_selected_predicates':29,'V22_direct_profiles_composite':17,'V22_full_cycle_miter_cases':17,'V22_literal_vectors':4096,'V22_meaningful_miter_mutants':6,'V22_cells':101044,'V22_flops':9612,'V22_slacks_ns':slacks,'slow_delta_vs_V21_ps':20.441,'slow_delta_vs_V17_ps':-207.999,'critical_buffers':19,'critical_muxes':7,'NPU_binary_equations':34321,'NPU_distinct_checker_tests':47,'NPU_independent_actual_catalog_mutations':3,'runner_final_tests':57,'source_bundle_members':5180,'runtime_bytes':1398053408},'archives':archives,'raw_XML_recounts':controls,'evidence':evidence,'limitations':['Ignored temporary missing delivery-inventory link at root request; final assembly is root-owned.','Four archives independently streamed/rehashed against completed root member maps. No EDA, producer, simulation or tests rerun.','Runtime size and completed full-restoration receipt verified, not a new1.4GB download or physical execution.','No boot pass, physical placement result, timing adoption, fullPHY or manufacturing acceptance inferred.','Readiness and original historical proof/failedboot guards are unchanged.'],'documents_edited':False}
with (B/'doc140-peer-rx.json').open('x') as f:json.dump(report,f,indent=2);f.write('\n')
print(json.dumps({'receipt':pin(B/'doc140-peer-rx.json'),'status':report['status'],'findings':len(findings),'archives':4,'members':874}))
