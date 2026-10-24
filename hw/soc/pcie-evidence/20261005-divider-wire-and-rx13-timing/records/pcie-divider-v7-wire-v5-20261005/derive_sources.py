# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Retain all raw clusters and explicitly classify the complete electrical graph."""
from pathlib import Path
import difflib,hashlib,json
B=Path(__file__).resolve().parent;OLD=B.parent/'pcie-divider-v7-wire-v4-20261005'
def pin(p):
 with Path(p).open('rb') as f:return dict(bytes=Path(p).stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
oldfreeze=json.loads((OLD/'geometry-source-freeze.json').read_text());assert oldfreeze['inputs']=={p:pin(p) for p in oldfreeze['inputs']}
previous=json.loads((OLD/'geometry-execution.json').read_text());assert previous['status']=='FAIL_GEOMETRY_RETAINED'
assert [(x['name'],x['execution']['returncode']) for x in previous['steps']]==[('native_unsimplified_extraction',0),('probe_native_cells',0),('probe_device_locations',0),('probe_wire_components',1)]
for name in ['native-pcell-inventory.json','device-location-geometry.json']:
 target=B/name;assert not target.exists();target.write_bytes((OLD/name).read_bytes());assert pin(target)==pin(OLD/name)
bridges=[]
for path in oldfreeze['producer_sources']:
 old=Path(path);new=B/old.name;before=old.read_text();after=before.replace('/dev/shm/nssoc-div4-v7-wire-geometry-04','/dev/shm/nssoc-div4-v7-wire-geometry-05')
 if old.name=='probe_wire_components.py':
  needle='coverage=[]\nfor n in c.each_net():'
  addition="""coverage=[]
terminal_members=defaultdict(list);public_members=defaultdict(list)
for d in c.each_device():
 for td in d.device_class().terminal_definitions():
  terminal_members[d.net_for_terminal(td.id()).cluster_id].append(dict(device=d.id(),model=d.device_class().name,terminal=td.name))
for port in c.each_pin():public_members[c.net_for_pin(port.id()).cluster_id].append(port.name())
assert sum(len(v) for v in terminal_members.values())==283
assert sum(len(v) for v in public_members.values())==7
assert len(terminal_members)==38
for n in c.each_net():"""
  assert after.count(needle)==1;after=after.replace(needle,addition)
  needle=" coverage.append(dict(native_cluster=n.cluster_id,name=n.name,metal_area_dbu2=a,wire_components=owners.get(n.cluster_id,[])))\nassert len(rows)==37 and len(coverage)==38"
  addition=""" terminals=terminal_members.get(n.cluster_id,[]);ports=public_members.get(n.cluster_id,[])
 if not terminals:assert not a and not ports and n.cluster_id not in owners,('Unbound real native net',n.cluster_id,n.name,a,ports)
 coverage.append(dict(native_cluster=n.cluster_id,name=n.name,metal_area_dbu2=a,wire_components=owners.get(n.cluster_id,[]),device_terminals=terminals,public_ports=ports,classification='ELECTRICAL_DEVICE_TERMINAL_NET' if terminals else 'RETAINED_AUXILIARY_NO_METAL_DEVICE_TERMINAL_OR_PUBLIC_PIN'))
assert len(rows)==37 and len(coverage)==72
assert len({r['native_cluster'] for r in coverage})==72
assert {r['native_cluster'] for r in coverage if r['device_terminals']}==set(terminal_members)
assert set(public_members)<=set(terminal_members)
aux=[r for r in coverage if not r['device_terminals']]
assert len(aux)==34 and all(not r['metal_area_dbu2'] and not r['wire_components'] and not r['public_ports'] for r in aux)
body=[r for r in coverage if r['device_terminals'] and not r['metal_area_dbu2']]
assert len(body)==1 and len(body[0]['device_terminals'])==85 and not body[0]['public_ports']
assert all((t['model'],t['terminal']) in {('npn13G2','S'),('rppd','rppd_sub'),('ptap1','WELL')} for t in body[0]['device_terminals'])
assert set(owners)==set(terminal_members)-{body[0]['native_cluster']}"""
  assert after.count(needle)==1;after=after.replace(needle,addition)
  after=after.replace('native_layer_mapping=mapping,layers=layers,wire_components=rows,native_net_coverage=coverage,','native_layer_mapping=mapping,layers=layers,wire_components=rows,native_net_coverage=coverage,\n native_electrical_net_count=len(terminal_members),retained_auxiliary_native_net_count=len(aux),raw_native_clusters_purged=False,')
 if old.name=='run_geometry.py':
  after=after.replace('Owned unsimplified native extraction and geometry; no comparison/RC/SPICE run.','Continue geometry from exact completed native extraction; no extraction rerun.')
  after=after.replace("NAMES = ['probe_native_cells', 'probe_device_locations', 'probe_wire_components',\n         'probe_terminal_anchors', 'prepare_anchors', 'bind_source_ids']","NAMES = ['probe_wire_components', 'probe_terminal_anchors',\n         'prepare_anchors', 'bind_source_ids']")
  after=after.replace('assert not W.exists() and not N.exists()','assert not W.exists() and N.is_dir()')
  start=after.index('        N.mkdir()\n');end=after.index('        for name in NAMES:',start)
  after=after[:start]+"""        previous = json.loads((B.parent / 'pcie-divider-v7-wire-v4-20261005/geometry-execution.json').read_text())
        assert previous['status'] == 'FAIL_GEOMETRY_RETAINED'
        assert [(s['name'], s['execution']['returncode']) for s in previous['steps']] == [('native_unsimplified_extraction', 0), ('probe_native_cells', 0), ('probe_device_locations', 0), ('probe_wire_components', 1)]
        for name in ['native-pcell-inventory.json', 'device-location-geometry.json']:
            assert pin(B / name) == pin(B.parent / 'pcie-divider-v7-wire-v4-20261005' / name)
        record['reused_completed_native_extraction_and_location_reads'] = dict(prior_receipt=pin(B.parent / 'pcie-divider-v7-wire-v4-20261005/geometry-execution.json'), native_outputs={str(p): pin(p) for p in N.iterdir() if p.is_file()}, repeated_native_extraction=False)
        record['native_comparison_executed'] = False
        save()
"""+after[end:]
 assert not new.exists();new.write_text(after)
 a,z=before.splitlines(True),after.splitlines(True);ops=[dict(tag=t,before=''.join(a[i:j]),after=''.join(z[k:l])) for t,i,j,k,l in difflib.SequenceMatcher(None,a,z,autojunk=False).get_opcodes()]
 assert ''.join(x['before'] for x in ops)==before and ''.join(x['after'] for x in ops)==after
 bridges.append(dict(before=dict(path=str(old),**pin(old)),after=dict(path=str(new),**pin(new)),opcodes=ops))
bp=B/'geometry-source-bridge.json';bp.write_text(json.dumps(bridges,indent=2)+'\n')
inputs={p:h for p,h in oldfreeze['inputs'].items() if not Path(p).is_relative_to(OLD)}
inputs.update({str(p):pin(p) for p in [*(B/Path(p).name for p in oldfreeze['producer_sources']),Path(__file__),bp,B/'native-pcell-inventory.json',B/'device-location-geometry.json',OLD/'geometry-source-freeze.json',OLD/'geometry-execution.json',OLD/'geometry-source-only-peer.json',OLD/'native-pcell-inventory.json',OLD/'device-location-geometry.json',OLD/'probe_wire_components.log',OLD/'probe_wire_components.owned.json',OLD/'diagnostic01-source.json',OLD/'diagnostic01-execution.json',OLD/'wire-component-geometry-diagnostic.json',OLD/'native_unsimplified.lvs',*Path('/dev/shm/nssoc-div4-v7-wire-native-02').iterdir()] if p.is_file()})
r=dict(status='FROZEN_DIVIDER_V7_EXPLICIT_UNPURGED_NATIVE_CLUSTER_CENSUS_V5',inputs=inputs,producer_sources={str(B/Path(p).name):pin(B/Path(p).name) for p in oldfreeze['producer_sources']},source_expected_census=oldfreeze['source_expected_census'],actual_prior_hierarchy_census=oldfreeze['actual_prior_hierarchy_census'],expected_complete_native_cluster_partition=dict(raw_clusters=72,device_terminal_clusters=38,metal_components=37,body_only_clusters=1,retained_no_metal_no_device_terminal_no_public_pin_clusters=34),unmeasured_terminal_reference_planes=True,scope='Reuse exact completed V4 flat native extraction and91device/283terminal PCell location reads; no native extraction or previous successful reads rerun. Preserve all72rawnativeclusters. Actual source/device graph has38terminal-connected clusters; require37metalcomponents+1bodyonly85terminals, explicitly retain34auxclusters with no metal/device terminal/public pin. Never purge or rewrite native graph. Same full geometry/native/source quantities and terminal-reference checks; no RC/extracted timing or qualifiedPEX.')
out=B/'geometry-source-freeze.json';out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(path=str(out),**pin(out),inputs=len(inputs))))
