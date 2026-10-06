# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent saved-graph/geometry/control review; no native execution."""
from pathlib import Path
from collections import Counter,defaultdict
import hashlib,json,re,math
B=Path(__file__).resolve().parent;C=B/'binding-controls01';N=Path('/dev/shm/nssoc-div4-v10-tail-v1-wire-native-01');G=Path('/dev/shm/nssoc-div4-v10-tail-v1-layout-01')
def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def read(p):return json.loads(Path(p).read_text())
def hashes(d):assert d=={p:pin(p) for p in d}
f=read(B/'geometry-source-freeze.json');hashes(f['inputs']);hashes(f['producer_sources']);g=read(B/'geometry-execution.json');hashes(g['outputs']);assert g['status']=='PASS_DIVIDER_V10_TAIL115_SAVED_NATIVE_GEOMETRY_AND_SOURCE_BIJECTION_ONLY'
assert g['freeze']==pin(B/'geometry-source-freeze.json');assert g['peer']==pin(B/'geometry-source-only-peer.json');assert read(B/'geometry-source-only-peer.json')['findings']==[]
assert not any(g[k] for k in ['rc_extraction_executed','qualified_pex','main_chip_integrated','native_comparison_executed'])
assert [(s['name'],s['execution']['returncode']) for s in g['steps']]==[(n,0) for n in ['native_unsimplified_extraction','probe_native_cells','probe_device_locations','probe_wire_components','probe_terminal_anchors','prepare_anchors','bind_source_ids']]
assert g['native_device_extraction_executed'] is True
raw=(N/'result.l2n').read_text();nets=dict((int(i),n) for i,n in re.findall(r'^ N\((\d+) I\(([^)]+)\)',raw,re.M));ports=dict((n,int(i)) for i,n in re.findall(r'^ P\((\d+) I\(([^)]+)\)\)',raw,re.M));assert len(nets)==72 and len(ports)==7
native={};terms={}
for ident,cls,body in re.findall(r'^ D\((\d+) D\$([^\s]+)\n(.*?)^ \)\n',raw,re.M|re.S):
 ident=int(ident);model=cls.split('$')[0];ts={n:int(i) for n,i in re.findall(r'^  T\((\S+) (\d+)\)$',body,re.M)};native[ident]=dict(model=model,terminals=ts)
 for n,i in ts.items():terms[(ident,n)]=(model,i)
assert len(native)==91 and len(terms)==283
v=read(B/'wire-component-geometry.json');hashes(v['inputs']);assert v['native_net_count']==72 and v['native_electrical_net_count']==38 and v['retained_auxiliary_native_net_count']==34 and v['raw_native_clusters_purged'] is False

assert set(v['native_layer_mapping'])=={'8','10','30','50','67','126','134'}
assert not v['layers']['134']['explicitly_empty'] and not v['layers']['133']['explicitly_empty']
leaves=read(B/'native-pcell-inventory.json');assert len(leaves)==725
assert Counter(x['cell'].split('$')[0]for x in leaves)==dict(npn13G2=34,rppd=33,cmim=6,ptap1=18,via_stack=634)
coverage=v['native_net_coverage'];assert {r['native_cluster']:r['name'] for r in coverage}==nets
covered={}
for row in coverage:
 for t in row['device_terminals']:
  key=(t['device'],t['terminal']);assert key not in covered;covered[key]=(t['model'],row['native_cluster'])
 assert set(row['public_ports'])=={n for n,i in ports.items() if i==row['native_cluster']}
 if not row['device_terminals']:assert not row['metal_area_dbu2'] and not row['wire_components'] and not row['public_ports']
assert covered==terms
components={r['component']:r for r in v['wire_components']};assert set(components)==set(range(1,38));assert len({r['native_cluster'] for r in components.values()})==37
for r in coverage:
 if r['metal_area_dbu2']:assert len(r['wire_components'])==1 and components[r['wire_components'][0]]['native_cluster']==r['native_cluster']
t=read(B/'terminal-reference-planes.json');hashes(t['inputs']);assert not t['unresolved'] and len(t['rows'])==283
assert {(r['device'],r['terminal']):(r['model'],r['native_cluster']) for r in t['rows']}==terms
assert Counter(r['disposition'] for r in t['rows'])==dict(ACTUAL_METAL_POINT_REFERENCE=198,UNCHANGED_INTRINSIC_BODY_TERMINAL_NO_ADDED_SUBSTRATE_R=85)
for r in t['rows']:
 if r['disposition']=='ACTUAL_METAL_POINT_REFERENCE':
  assert components[r['wire_component']]['native_cluster']==r['native_cluster'];x,y=r['point_dbu'];left,bottom,right,top=r['access_box_dbu'];assert left<x<right and bottom<y<top
 else:assert (r['model'],r['terminal']) in {('npn13G2','S'),('rppd','rppd_sub'),('ptap1','WELL')}
a=read(B/'anchors.json');hashes(a['inputs']);assert len(a['anchors'])==205 and len({r['label'] for r in a['anchors']})==205
intrinsic=[r for r in a['anchors'] if r['kind']=='INTRINSIC_DEVICE_TERMINAL_REFERENCE'];public=[r for r in a['anchors'] if r['kind']=='PUBLIC_PORT_REFERENCE'];assert len(intrinsic)==198 and len(public)==7
assert [r['detail'] for r in intrinsic]==[r for r in t['rows'] if r['disposition']=='ACTUAL_METAL_POINT_REFERENCE']
assert a['unmodeled_body_well_terminals']==[r for r in t['rows'] if r['disposition']!='ACTUAL_METAL_POINT_REFERENCE']
assert Counter(r['wire_component'] for r in a['anchors']).keys()==components.keys();assert min(Counter(r['wire_component'] for r in a['anchors']).values())>=2
for r in public:assert components[r['wire_component']]['native_cluster']==ports[r['detail']['name']]
s=read(B/'source-native-bijection.json');hashes(s['inputs']);assert len(s['devices'])==91 and len({r['source_name'] for r in s['devices']})==91
mapping=s['source_net_to_native_cluster'];assert len(mapping)==len(set(mapping.values()))==38;assert mapping['BULK']!=mapping['SUB'];ref=read(G/'result.json');refs={r['name']:r for r in ref['instances']};assert set(refs)=={r['source_name'] for r in s['devices']}
geo={d['native_id']:d for d in read(B/'device-location-geometry.json')['devices']}
for d in s['devices']:
 rawd=native[d['native_id']];assert d['source_device']==refs[d['source_name']] and d['model']==rawd['model'];assert d['native_location']==geo[d['native_id']]['pcell']
 assert set(d['terminal_order'])==set(rawd['terminals']);assert len(d['terminal_order'])==len(d['source_nets'])
 for terminal,net in zip(d['terminal_order'],d['source_nets']):assert mapping[net]==rawd['terminals'][terminal]
assert Counter(d['model'] for d in s['devices'])==dict(npn13G2=34,rppd=33,cap_cmim=6,ptap1=18)
cf=read(C/'source-freeze.json');hashes(cf['inputs']);cr=read(C/'result.json');assert cr['status']=='PASS_BASELINE_AND_FOUR_ACTUAL_COPIED_INPUT_BINDING_CONTROLS';assert cr['freeze']==pin(C/'source-freeze.json');assert cr['positive_geometry']==pin(B/'geometry-execution.json');hashes(cr['fixture_outputs']);assert len(cr['cases'])==5
stages=[(B,r) for r in g['steps']]+[(C,r) for r in cr['cases']]
for directory,row in stages:
 e=row['execution'];owner=read(directory/(row['name']+'.owned.json'));assert pin(directory/(row['name']+'.owned.json'))['sha256']==e['process_owner_sha256'];assert pin(directory/(row['name']+'.log'))['sha256']==e['log_sha256']
 assert owner['status']=='HEALTHY' and len(owner['processes'])==1;child=owner['processes'][0];assert child['status']=='REAPED_NO_LIVE_MEMBERS' and child['returncode']==e['returncode'] and not child['members_at_leader_exit']
for row in cr['cases']:
 hashes(row['inputs']);q=Path(row['execution']['command'][2]).parent;method=(q/'bind_source_ids.py').read_text();replacement=f"G=Path({str(q/'fixture-layout')!r})";assert method.count(replacement)==1 and method.replace(replacement,"G=Path('/dev/shm/nssoc-div4-v10-tail-v1-layout-01')")== (B/'bind_source_ids.py').read_text()
 assert sum(len(v) for v in row['changes'].values())==(0 if row['name']=='positive' else 1)
 if row['name']=='positive':assert row['execution']['returncode']==0 and {k:v for k,v in read(q/'source-native-bijection.json').items() if k!='inputs'}=={k:v for k,v in s.items() if k!='inputs'}
 else:
  assert row['execution']['returncode']==1 and not (q/'source-native-bijection.json').exists();log=(C/(row['name']+'.log')).read_text();assert row['expected_assertion_observed'] in log and 'AssertionError' in log and 'Traceback (most recent call last)' in log
# Additive independent Cap24 check against the raw native database and geometric
# terminal shape metadata, not only the producer's source-native binding claim.
raw_params={int(ident):{k:float(v) for k,v in re.findall(r'^  E\((\S+) ([^)]+)\)$',body,re.M)} for ident,cls,body in re.findall(r'^ D\((\d+) D\$([^\s]+)\n(.*?)^ \)\n',raw,re.M|re.S)}
cap24=[]
for d in s['devices']:
 if d['source_name'] not in ('DIV__XCP','DIV__XCN'):continue
 assert d['source_device']['width_um']==d['source_device']['length_um']==24.0
 ident=d['native_id'];assert raw_params[ident]==dict(w=24.0,l=24.0,A=576.0,P=96.0,m=1.0)
 gd=next(x for x in read(B/'device-location-geometry.json')['devices'] if x['native_id']==ident)
 assert gd['parameters']==raw_params[ident]
 for term in gd['terminals']:
  assert len(term['native_layers'])==1
  layer=term['native_layers'][0];assert layer['polygons']==1 and layer['area_dbu2']==576000000
  points=list(map(int,re.findall(r'-?\d+',layer['bbox_dbu'])));assert points[2]-points[0]==points[3]-points[1]==24000
 cap24.append(dict(source_name=d['source_name'],native_id=ident,parameters=raw_params[ident]))
assert len(cap24)==2
bias8=[]
for d in s['devices']:
 if d['source_name']not in ('DIV__XDP','DIV__XDN'):continue
 assert d['source_device']['kind']=='resistor'and d['source_device']['width_um']==1.0 and d['source_device']['length_um']==8.0
 ident=d['native_id'];assert raw_params[ident]==dict(w=1.0,l=8.0,ps=0.0,b=0.0,m=1.0)
 assert geo[ident]['parameters']==raw_params[ident]
 assert d['source_nets']==(['DIV__CKP','AVSS','BULK']if d['source_name']=='DIV__XDP'else['DIV__CKN','AVSS','BULK'])
 assert d['source_device']['nets']==(['DIV__CKP','AVSS','SUB']if d['source_name']=='DIV__XDP'else['DIV__CKN','AVSS','SUB'])
 bias8.append(dict(source_name=d['source_name'],native_id=ident,parameters=raw_params[ident],native_terminals=native[ident]['terminals']))
assert len(bias8)==2
tail=[]
prior_layout=read('/dev/shm/nssoc-div4-v9-bias-v1-layout-01/result.json')
prior_refs={x['name']:x for x in prior_layout['instances']}
assert set(prior_refs)==set(refs)
for name in refs:
 if name!='DIV__XSECOND__XBIAS':assert refs[name]==prior_refs[name],name
 else:
  expected=dict(prior_refs[name]);assert expected['length_um']==12.7
  expected['length_um']=11.5;assert refs[name]==expected
for d in s['devices']:
 if d['source_name']!='DIV__XSECOND__XBIAS':continue
 ident=d['native_id'];assert raw_params[ident]==dict(w=1.0,l=11.5,ps=0.0,b=0.0,m=1.0)
 assert geo[ident]['parameters']==raw_params[ident]
 tail.append(dict(source_name=d['source_name'],native_id=ident,parameters=raw_params[ident]))
assert len(tail)==1
r=dict(actual_second_stage_tail115=tail,prior90source_instances_unchanged=True,reviewer='PLL independent saved-byte review',actual_two_bias8_resistors=bias8,status='PASS_DIVIDER_V10_TAIL115_SAVED_GEOMETRY_AND_BINDING_CONTROLS',findings=[],method=pin(__file__),geometry_execution=pin(B/'geometry-execution.json'),binding_controls=pin(C/'result.json'),source_peer=pin(B/'geometry-source-only-peer.json'),binding_source_peer=pin(C/'source-only-peer-rx.json'),native_database=pin(N/'result.l2n'),source_inputs_rehashed=len(f['inputs']),closed_stage_count=len(stages),raw_native_devices=91,raw_native_terminals=283,raw_clusters_retained=72,electrical_clusters=38,auxiliary_clusters_without_terminal_metal_or_public_pin=34,metal_components=37,metal_terminals=198,body_terminals=85,real_anchors=205,minimum_anchors_per_component=min(Counter(r['wire_component'] for r in a['anchors']).values()),public_ports=7,all_source_device_ids_and_net_bijection_rechecked=True,actual_binding_controls=dict(positive=1,declared_rejections=4),native_reexecution=False,actual_two_cap24_devices=cap24,scope='Saved immutable Tail115 graph/geometry/output; actual second-stage reference W1/L11.5, two native rppd W1/L8 and two retained24um MIM devices independently matched. Remaining90 complete source instance records byte-equivalent to Bias8 native ancestor. Remaining91-device/source mapping verified. Graph/geometry/output and owned lifecycle review, including independent ASCII database terminal recount and complete source-net/terminal join. Actual geometry algorithms were executed by the frozen owned producer, not rerun here. All72 raw clusters retained; no net/device purge. Five copied-input tests verify binder sensitivity; they are not electrical fault simulations. Point-reference wire-only RC remains a future experiment. No distributed intrinsic-terminal, substrate resistance, qualified PEX, extracted clock division, main-chip or full PHY acceptance.')
assert not (B/'saved-geometry-peer.json').exists();(B/'saved-geometry-peer.json').write_text(json.dumps(r,indent=2)+'\n');print(r['status'],pin(B/'saved-geometry-peer.json'))
