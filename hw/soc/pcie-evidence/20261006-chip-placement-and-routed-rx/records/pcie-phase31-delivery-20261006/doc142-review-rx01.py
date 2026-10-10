# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Bounded doc142 fact/scope review against immutable native and saved peers."""
import csv
import datetime
import hashlib
import json
from pathlib import Path

R=Path.cwd();B=Path(__file__).resolve().parent
N=R/'hw/soc/out/npu-eco-physical-runner-20261006'
X=R/'hw/soc/out/pcie-gen3-receive-prefetch-v2-20261004/repair16one-peer'
D=R/'docs/142-chip-placement-and-routed-receiver.md'
checked={}
def pin(p):
    p=Path(p)
    with p.open('rb') as f:r={'bytes':p.stat().st_size,'sha256':hashlib.file_digest(f,'sha256').hexdigest()}
    checked[str(p)]=r
    return r
def read(p): pin(p);return json.loads(Path(p).read_text())
doc=D.read_text();docpin=pin(D)
rec=read(N/'pair02-comparison-recovered01.json');c=rec['comparison']
assert rec['native_reexecuted'] is False and rec['status']=='RECOVERED_SAVED_COMPARISON_NO_NATIVE_RERUN'
peer=read(N/'comparison-recovery-peer-pll01.json')
assert peer['findings']==[] and peer['all_arm_output_pins_rehashed']==460
assert peer['result']==pin(N/'pair02-comparison-recovered01.json')
assert c['candidate_adopted'] is False and c['timing_accepted'] is False
assert round(-c['factored_minus_original']['setup_wns_seconds']*1e9,6)==2.352110
assert round(c['factored_minus_original']['hold_wns_seconds']*1e12,3)==218.885
recounts={};outputs=0
for label,count in [('original',20138),('factored',20163)]:
    a=read(N/f'pair02-{label}/result.json')
    assert a['status']=='FRESH_NPU_PHYSICAL_COMPLETE_ESTIMATE_ONLY'
    assert a['execution']['returncode']==0 and a['all_inputs_rechecked'] is True
    assert not any(a[k] for k in ('candidate_adopted','timing_accepted','manufacturing_approval','final_route_or_signoff'))
    for name,h in a['outputs'].items(): assert pin(N/f'pair02-{label}'/name)==h;outputs+=1
    p=N/f'pair02-{label}/capture/setup-endpoints.tsv'
    with p.open() as f:rows=list(csv.DictReader(f,delimiter='\t'))
    assert len(rows)==count
    values=[float(r['global_vertex_slack_seconds']) for r in rows if r['global_vertex_slack_seconds']!='UNCONSTRAINED']
    assert min(values)==c[label]['setup_wns_seconds']
    assert sum(v<0 for v in values)==c[label]['setup_violating_endpoints']
    native=a['native_validation']['native']['hold_stage']
    assert native['endpoint_count']==count and native['negative_vertex_endpoints']==c[label]['hold_violating_endpoints']
    assert min(x['native_wns_seconds'] for x in native['corners'])==c[label]['hold_wns_seconds']
    recounts[label]={'endpoints':count,'constrained_setup':len(values),'negative_setup':sum(v<0 for v in values),'native_negative_hold':native['negative_vertex_endpoints']}
assert outputs==460
tmpl=read(N/'saved-template-peer-rx01.json')
assert tmpl['findings']==[]
assert tmpl['prior_failure']['unknown_master_counts']=={'DP8TSRAMDP256x16':16,'SP6TSRAM512x64':16}
assert tmpl['independent_geometry']['macro_instances']==32 and tmpl['independent_geometry']['signal_boxes']==301
freeze=read(N/'source-freeze07.json')
assert freeze['controls']['passed']==70 and freeze['controls']['log']==pin(N/'controls07.log')
assert '70 passed' in (N/'controls07.log').read_text()
package=read(N/'nssoc-npu-eco-fresh-physical-pair02-validation-20261006.json')
assert len(package['members'])==700
assert pin(package['archive']['path'])=={k:package['archive'][k] for k in ('bytes','sha256')}
rx=read(X/'saved-result-peer-rx01.json');release=read(X/'release.json')
assert rx['findings']==[] and rx['individual_report_count']==36 and rx['archive_members']==110
assert rx['input_only_CTS_loads_fully_bound']==78
assert len(release['assets'])==3 and all(a['authenticated_roundtrip'] and a['anonymous_roundtrip'] for a in release['assets'])
assert pin(release['files'][0]['path'])=={k:release['files'][0][k] for k in ('bytes','sha256')}
for corner, title in [('slow','Slow'),('typical','Typical'),('fast','Fast')]:
    values=rx['nominal_cell_corner_slack_ns'][corner]
    fields=[f'{values[k]:+.6f} ns'.replace('-', '−') for k in ('setup','hold','recovery','removal')]
    assert '| '+title+' | '+' | '.join(fields)+' |' in doc
for metric,title,scale,fmt in [('setup_wns_seconds','Worst setup slack',1e9,'.6f'),('hold_wns_seconds','Worst hold slack',1e9,'.6f'),('setup_violating_endpoints','Setup violating endpoints',1,','),('hold_violating_endpoints','Hold violating endpoints',1,','),('slew_violations','Slew violations',1,','),('capacitance_violations','Capacitance violations',1,','),('instance_count','Instances',1,',')]:
    fields=[format(c[k][metric]*scale,fmt).replace('-','−')+(' ns' if scale==1e9 else '') for k in ('original','factored')]
    assert '| '+title+' | '+' | '.join(fields)+' |' in doc,(metric,fields)
for text in ['101.025 ps','2.352110 ns','218.885 ps','20,138','20,163','1,804 state bits','5,443 functions','ten actual negative controls','six native public-port cases','78 CTS input bindings','700 members','158,525,968 bytes','35,857,152 bytes',package['archive']['sha256'],release['files'][0]['sha256']]:assert text in doc,text
for text in ['Neither result closes','target remains unmet','not a\nfoundry rule-deck','nominal RC','black-boxed','unrepresented or unconstrained paths are not counted','omits post-CTS\ntiming repair','without\nrepeating physical work','does not replace the earlier public\narchive','final setup/hold','remain open']:assert text in doc,text
result={'status':'PASS_INDEPENDENT_DOC142_FACTS_AND_SCOPE','findings':[],'document':docpin,'inputs':checked,'independent_endpoint_recounts':recounts,'closed_arm_outputs_rehashed':outputs,'archive_hashes_rechecked':{'physical':package['archive'],'rx':release['files'][0]},'scope':['Full narrative and all numeric tables checked against closed native results, independent peers, actual raw setup endpoint populations, original failure/control records and public archive receipts.','Rounded hold improvement218.885ps is derived from full native precision, not subtraction of rounded table cells.','Archive member counts are checked against exact closed manifests; compressed archive hashes rechecked here. Prior independent full-member reviews are retained, not reexecuted.','No native EDA, controls, proof, publication or document edits. Temporary inventory link is outside this review because root is assembling the packet.','No timing acceptance, qualified SRAM/RC, fullPHY/chip signoff or adoption claimed.'],'method':pin(__file__),'utc':datetime.datetime.now(datetime.UTC).isoformat()}
with (B/'doc142-review-rx01.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps({'status':result['status'],'receipt':pin(B/'doc142-review-rx01.json'),'files':len(checked)}))
