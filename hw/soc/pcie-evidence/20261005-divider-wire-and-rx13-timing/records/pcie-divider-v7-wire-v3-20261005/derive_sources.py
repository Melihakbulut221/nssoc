# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Acquire unsimplified native graph, preserving the completed LVS comparison."""
from pathlib import Path
import difflib,hashlib,json
B=Path(__file__).resolve().parent;OLD=B.parent/'pcie-divider-v7-wire-v2-20261005'
def pin(p):
 with Path(p).open('rb') as f:return dict(bytes=Path(p).stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
oldfreeze=json.loads((OLD/'geometry-source-freeze.json').read_text());assert oldfreeze['inputs']=={p:pin(p) for p in oldfreeze['inputs']}
assert json.loads((OLD/'geometry-execution.json').read_text())['status']=='FAIL_GEOMETRY_RETAINED'
bridges=[]
for path in oldfreeze['producer_sources']:
 old=Path(path);new=B/old.name;before=old.read_text()
 after=before.replace('/dev/shm/nssoc-div4-v7-wire-geometry-02','/dev/shm/nssoc-div4-v7-wire-geometry-03').replace('/dev/shm/nssoc-div4-v7-checks-02/lvs/result.lvsdb','/dev/shm/nssoc-div4-v7-wire-native-01/result.lvsdb')
 if old.name=='run_geometry.py':
  after=after.replace('Owned exact saved-layout geometry reading only; no Magic/SPICE/DRC/LVS run.','Owned unsimplified native extraction and geometry; no comparison/RC/SPICE run.')
  after=after.replace("C = Path('/dev/shm/nssoc-div4-v7-checks-02')","C = Path('/dev/shm/nssoc-div4-v7-checks-02')\nN = Path('/dev/shm/nssoc-div4-v7-wire-native-01')")
  after=after.replace('assert not W.exists()','assert not W.exists() and not N.exists()')
  after=after.replace('SCRATCH_ROOTS=(B, W)','SCRATCH_ROOTS=(B, W, N)')
  after=after.replace("status='RUNNING_SAVED_DIVIDER_V7_GEOMETRY'","status='RUNNING_UNSIMPLIFIED_DIVIDER_V7_GEOMETRY'")
  after=after.replace("rc_extraction_executed=False, qualified_pex=False,","rc_extraction_executed=False, native_device_extraction_executed=False, qualified_pex=False,")
  needle='    try:\n        for name in NAMES:'
  addition="""    try:
        N.mkdir()
        deck = ROOT / 'hw/soc/tools/ihp-lvs-5e6d592/ihp-sg13g2/libs.tech/klayout/tech/lvs/sg13g2.lvs'
        command = [A, 'klayout', '-b', '-zz', '-r', deck]
        options = dict(input=G / 'nssoc_clock_div4_v7_layout.gds',
                       topcell='nssoc_clock_div4_v7_layout', log=N / 'deck.log',
                       run_mode='deep', report=N / 'result.lvsdb',
                       target_netlist=N / 'extracted.cir', thr=1,
                       net_only='True', no_simplify='True', top_lvl_pins='True',
                       combine_devices='False', purge='False', purge_nets='False',
                       purge_devices='False', disable_tap_extraction='False')
        for key, value in options.items():
            command += ['-rd', f'{key}={value}']
        execution = ns['execute'](command, B, 'native_unsimplified_extraction')
        record['steps'].append(dict(name='native_unsimplified_extraction', options={k: str(v) for k, v in options.items()}, execution=execution))
        save()
        assert execution['returncode'] == 0
        log = (N / 'deck.log').read_text()
        assert 'NET_ONLY enabled: apply extraction netlist options and skip comparison.' in log
        for name in ['simplify', 'combine_devices', 'purge', 'purge_nets', 'purge_devices']:
            assert f'[layout_netlist] {name}: SKIPPED' in log
        assert '[layout_netlist] make_top_level_pins: ENABLED' in log
        assert 'ERROR' not in log and 'Error:' not in log
        assert (N / 'result.lvsdb').is_file() and (N / 'extracted.cir').is_file()
        record['native_device_extraction_executed'] = True
        record['native_comparison_executed'] = False
        assert freeze['inputs'] == {p: pin(p) for p in freeze['inputs']}
        save()
        for name in NAMES:"""
  assert after.count(needle)==1;after=after.replace(needle,addition)
  after=after.replace("*(p for p in W.rglob('*') if p.is_file())]}","*(p for directory in (W, N) for p in directory.rglob('*') if p.is_file())]}")
 assert not new.exists();new.write_text(after)
 a,z=before.splitlines(True),after.splitlines(True);ops=[dict(tag=t,before=''.join(a[i:j]),after=''.join(z[k:l])) for t,i,j,k,l in difflib.SequenceMatcher(None,a,z,autojunk=False).get_opcodes()]
 assert ''.join(x['before'] for x in ops)==before and ''.join(x['after'] for x in ops)==after
 bridges.append(dict(before=dict(path=str(old),**pin(old)),after=dict(path=str(new),**pin(new)),opcodes=ops))
bp=B/'geometry-source-bridge.json';bp.write_text(json.dumps(bridges,indent=2)+'\n')
inputs={p:h for p,h in oldfreeze['inputs'].items() if not Path(p).is_relative_to(OLD)}
inputs.update({str(p):pin(p) for p in [*(B/Path(p).name for p in oldfreeze['producer_sources']),Path(__file__),bp,OLD/'geometry-source-freeze.json',OLD/'geometry-execution.json',OLD/'geometry-source-only-peer.json',OLD/'probe_device_locations.log',OLD/'probe_device_locations.owned.json']})
completed=json.loads(Path('/dev/shm/nssoc-div4-v7-checks-02/result.json').read_text())
for path,sha in completed['inputs'].items():
 if 'ihp-lvs' in path:
  assert pin(path)['sha256']==sha;inputs[path]=pin(path)
f=dict(status='FROZEN_DIVIDER_V7_NATIVE_UNSIMPLIFIED_GRAPH_AND_GEOMETRY_V3',inputs=inputs,producer_sources={str(B/Path(p).name):pin(B/Path(p).name) for p in oldfreeze['producer_sources']},source_expected_census=oldfreeze['source_expected_census'],actual_prior_hierarchy_census=oldfreeze['actual_prior_hierarchy_census'],unmeasured_predicted_empty_layers=[134,133],scope='Final native comparison graph combines parallel ptaps and cannot witness18separatecontacts. Fresh same-GDS native device extraction uses unmodified pinned officialdeck net_only/no_simplify/top_lvl_pins options, no comparison/no RC. All91devices/283terminals/38nets/37conductors remain mandatory independent measurements. Completed deep/flat LVS and original artifacts unchanged; all18physical finite contacts preserved; no substrate spreading or qualifiedPEX.')
out=B/'geometry-source-freeze.json';out.write_text(json.dumps(f,indent=2)+'\n');print(json.dumps(dict(path=str(out),**pin(out),inputs=len(inputs))))
