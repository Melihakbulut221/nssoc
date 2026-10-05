# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent exact source bridge and immutable input review; no extraction."""
from pathlib import Path
import json,hashlib,ast,datetime
B=Path(__file__).resolve().parent
P=B.with_name('pcie-divider-v7-wire-v3-20261005')
def pin(path):
 p=Path(path)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
f=json.loads((B/'geometry-source-freeze.json').read_text())
assert pin(B/'geometry-source-freeze.json')==dict(bytes=26213,sha256='d15d4d9515672b8854234eceb31d52f6aacc21ee7be93531ed7cf7558d6eb949')
assert len(f['inputs'])==95
for p,expected in f['inputs'].items():assert pin(p)==expected,p
prior=json.loads((P/'geometry-source-only-peer.json').read_text())
assert prior['status']=='PASS_SOURCE_ONLY_DIVIDER_V7_WIRE_GEOMETRY' and not prior['findings']
rows=json.loads((B/'geometry-source-bridge.json').read_text());assert len(rows)==7
review=[]
for row in rows:
 name=Path(row['after']['path']).name
 before=(P/name).read_text();after=(B/name).read_text()
 assert ''.join(c['before'] for c in row['opcodes'])==before
 assert ''.join(c['after'] for c in row['opcodes'])==after
 for side in ['before','after']:
  x=row[side];assert pin(x['path'])=={k:x[k] for k in ('bytes','sha256')}
 expected=before.replace('nssoc-div4-v7-wire-native-01/result.lvsdb','nssoc-div4-v7-wire-native-02/result.l2n').replace('nssoc-div4-v7-wire-geometry-03','nssoc-div4-v7-wire-geometry-04').replace('l=pya.LayoutVsSchematic();','l=pya.LayoutToNetlist();')
 if name=='run_geometry.py':
  edits=[("N = Path('/dev/shm/nssoc-div4-v7-wire-native-01')","N = Path('/dev/shm/nssoc-div4-v7-wire-native-02')"),("deck = ROOT / 'hw/soc/tools/ihp-lvs-5e6d592/ihp-sg13g2/libs.tech/klayout/tech/lvs/sg13g2.lvs'","deck = B / 'native_unsimplified.lvs'"),("run_mode='deep', report=N / 'result.lvsdb',","run_mode='flat', native_l2n=N / 'result.l2n',"),("        assert (N / 'result.lvsdb').is_file() and (N / 'extracted.cir').is_file()","        assert 'NSSOC_UNSIMPLIFIED_GEOMETRY_L2N_EXPORT_REQUESTED' in log\n        assert (N / 'result.l2n').is_file() and (N / 'extracted.cir').is_file()")]
  for old,new in edits:assert expected.count(old)==1;expected=expected.replace(old,new)
 assert after==expected,name
 ast.parse(after);review.append({'method':name,'full_exact_bridge':True,'pin':pin(B/name)})
wrapper=(B/'native_unsimplified.lvs').read_text()
lines=[x for x in wrapper.splitlines() if x and not x.startswith('#')]
assert lines==["raise 'Unsimplified flat extraction contract' unless NET_ONLY && !SIMPLIFY && !COMBINE_DEVICES && !PURGE && !PURGE_NETS && !PURGE_DEVICES && !DISABLE_TAP_EXTRACTION && TOP_LVL_PINS && $run_mode.to_s == 'flat'","raise 'Fresh explicit geometry export path required' if $native_l2n.to_s.empty?",'report_netlist($native_l2n)',"logger.info('NSSOC_UNSIMPLIFIED_GEOMETRY_L2N_EXPORT_REQUESTED')"]
includes=[x for x in wrapper.splitlines() if x.startswith('# %include ')];assert len(includes)==1
path=includes[0].removeprefix('# %include ');assert path in f['inputs'];deck=Path(path).read_text();assert 'if NET_ONLY' in deck and 'target_netlist.simplify if SIMPLIFY' in deck
assert f['source_expected_census']==dict(physical_devices=91,hbt=34,rppd=33,mim=6,finite_ptap=18,native_terminals=283,metal_terminals=198,unmodeled_body_terminals=85,public_ports=7,wire_anchors=205,named_nets=38,metal_components=37)
record=dict(status='PASS_SOURCE_ONLY_DIVIDER_V7_WIRE_GEOMETRY',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),freeze=pin(B/'geometry-source-freeze.json'),findings=[],method=pin(Path(__file__)),immutable_inputs_rehashed=95,full_method_bridges=review,wrapper=pin(B/'native_unsimplified.lvs'),official_api={'url':'https://www.klayout.de/doc-qt5/manual/lvs_io.html','verified':'Layout-to-Netlist database section: report_netlist exports netlist plus shape and instance information after script success.'},scope='Source-only review. Flat no-simplify extraction and every graph/geometry/anchor census remain actual native guards; no RC/LVS/timing acceptance. Original91electricaldevices and18tapcontacts cannot be removed by simplification; exact inherited lifecycle/resource guards unchanged.')
(B/'geometry-source-only-peer.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps({'status':record['status'],'peer':pin(B/'geometry-source-only-peer.json')},indent=2))
