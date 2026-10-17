# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Use documented L2N persistence for flat extraction without comparison."""
from pathlib import Path
import difflib,hashlib,json
B=Path(__file__).resolve().parent;OLD=B.parent/'pcie-divider-v7-wire-v3-20261005'
def pin(p):
 with Path(p).open('rb') as f:return dict(bytes=Path(p).stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
oldfreeze=json.loads((OLD/'geometry-source-freeze.json').read_text());assert oldfreeze['inputs']=={p:pin(p) for p in oldfreeze['inputs']}
previous=json.loads((OLD/'geometry-execution.json').read_text());assert previous['status']=='FAIL_GEOMETRY_RETAINED';assert previous['steps'][0]['execution']['returncode']==0
bridges=[]
for path in oldfreeze['producer_sources']:
 old=Path(path);new=B/old.name;before=old.read_text()
 after=before.replace('/dev/shm/nssoc-div4-v7-wire-geometry-03','/dev/shm/nssoc-div4-v7-wire-geometry-04').replace('/dev/shm/nssoc-div4-v7-wire-native-01/result.lvsdb','/dev/shm/nssoc-div4-v7-wire-native-02/result.l2n').replace('pya.LayoutVsSchematic()','pya.LayoutToNetlist()')
 if old.name=='run_geometry.py':
  after=after.replace('/dev/shm/nssoc-div4-v7-wire-native-01','/dev/shm/nssoc-div4-v7-wire-native-02')
  after=after.replace("deck = ROOT / 'hw/soc/tools/ihp-lvs-5e6d592/ihp-sg13g2/libs.tech/klayout/tech/lvs/sg13g2.lvs'","deck = B / 'native_unsimplified.lvs'")
  after=after.replace("run_mode='deep', report=N / 'result.lvsdb',","run_mode='flat', native_l2n=N / 'result.l2n',")
  after=after.replace("assert (N / 'result.lvsdb').is_file() and (N / 'extracted.cir').is_file()","assert 'NSSOC_UNSIMPLIFIED_GEOMETRY_L2N_EXPORT_REQUESTED' in log\n        assert (N / 'result.l2n').is_file() and (N / 'extracted.cir').is_file()")
 assert not new.exists();new.write_text(after)
 a,z=before.splitlines(True),after.splitlines(True);ops=[dict(tag=t,before=''.join(a[i:j]),after=''.join(z[k:l])) for t,i,j,k,l in difflib.SequenceMatcher(None,a,z,autojunk=False).get_opcodes()]
 assert ''.join(x['before'] for x in ops)==before and ''.join(x['after'] for x in ops)==after
 bridges.append(dict(before=dict(path=str(old),**pin(old)),after=dict(path=str(new),**pin(new)),opcodes=ops))
bp=B/'geometry-source-bridge.json';bp.write_text(json.dumps(bridges,indent=2)+'\n')
inputs={p:h for p,h in oldfreeze['inputs'].items() if not Path(p).is_relative_to(OLD)}
inputs.update({str(p):pin(p) for p in [*(B/Path(p).name for p in oldfreeze['producer_sources']),Path(__file__),B/'native_unsimplified.lvs',bp,OLD/'geometry-source-freeze.json',OLD/'geometry-execution.json',OLD/'geometry-source-only-peer.json',OLD/'native_unsimplified_extraction.log',OLD/'native_unsimplified_extraction.owned.json',Path('/dev/shm/nssoc-div4-v7-wire-native-01/deck.log'),Path('/dev/shm/nssoc-div4-v7-wire-native-01/extracted.cir')]})
r=dict(status='FROZEN_DIVIDER_V7_FLAT_NATIVE_UNSIMPLIFIED_L2N_AND_GEOMETRY_V4',inputs=inputs,producer_sources={str(B/Path(p).name):pin(B/Path(p).name) for p in oldfreeze['producer_sources']},output_wrapper=dict(path=str(B/'native_unsimplified.lvs'),**pin(B/'native_unsimplified.lvs')),source_expected_census=oldfreeze['source_expected_census'],actual_prior_hierarchy_census=oldfreeze['actual_prior_hierarchy_census'],unmeasured_predicted_empty_layers=[134,133],official_persistence_documentation='https://www.klayout.de/doc-qt5/manual/lvs_io.html',scope='V3 completed native deep net_only extraction but report_lvs emits nothing without compare. Its hierarchical SPICE/log and failure retained. V4 uses documented report_netlist to persist native geometry-bearing L2N, unmodified pinned deck included by narrow wrapper, flat extraction to retain91actualdevices without hierarchy/simplification. No comparison, no RC; all91devices/283terminals/38nets/37conductors still mandatory independent measurements. All18finitecontacts retained, no substrate spreading or qualifiedPEX.')
out=B/'geometry-source-freeze.json';out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(path=str(out),**pin(out),inputs=len(inputs))))
