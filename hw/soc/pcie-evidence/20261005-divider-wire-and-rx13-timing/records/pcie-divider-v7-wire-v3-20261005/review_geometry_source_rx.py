# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Source-only audit of new unsimplified native extraction; no EDA invocation."""
from pathlib import Path
import ast,hashlib,json,datetime
B=Path(__file__).resolve().parent;OLD=B.parent/'pcie-divider-v7-wire-v2-20261005'
def pin(p):
 with Path(p).open('rb') as f:return dict(bytes=Path(p).stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
f=B/'geometry-source-freeze.json';assert pin(f)==dict(bytes=24050,sha256='a02acb20f66dc9ad28e33409f37a4f48b8c91103d85a483fab14c648d7b3dfdf')
freeze=json.loads(f.read_text());assert len(freeze['inputs'])==87
for p,h in freeze['inputs'].items():assert pin(p)==h,p
bridge=json.loads((B/'geometry-source-bridge.json').read_text());assert len(bridge)==7
for row in bridge:
 old,new=Path(row['before']['path']),Path(row['after']['path'])
 for key,p in [('before',old),('after',new)]:assert pin(p)=={k:row[key][k] for k in ('bytes','sha256')}
 assert ''.join(x['before'] for x in row['opcodes'])==old.read_text()
 assert ''.join(x['after'] for x in row['opcodes'])==new.read_text()
 s=new.read_text().replace('/dev/shm/nssoc-div4-v7-wire-geometry-03','/dev/shm/nssoc-div4-v7-wire-geometry-02').replace('/dev/shm/nssoc-div4-v7-wire-native-01/result.lvsdb','/dev/shm/nssoc-div4-v7-checks-02/lvs/result.lvsdb')
 if new.name=='run_geometry.py':
  s=s.replace('Owned unsimplified native extraction and geometry; no comparison/RC/SPICE run.','Owned exact saved-layout geometry reading only; no Magic/SPICE/DRC/LVS run.')
  s=s.replace("N = Path('/dev/shm/nssoc-div4-v7-wire-native-01')\n",'').replace('assert not W.exists() and not N.exists()','assert not W.exists()').replace('SCRATCH_ROOTS=(B, W, N)','SCRATCH_ROOTS=(B, W)').replace("status='RUNNING_UNSIMPLIFIED_DIVIDER_V7_GEOMETRY'","status='RUNNING_SAVED_DIVIDER_V7_GEOMETRY'").replace('rc_extraction_executed=False, native_device_extraction_executed=False, qualified_pex=False,','rc_extraction_executed=False, qualified_pex=False,')
  begin=s.index('        N.mkdir()\n');end=s.index('        for name in NAMES:',begin);s=s[:begin]+s[end:]
  s=s.replace("*(p for directory in (W, N) for p in directory.rglob('*') if p.is_file())]}","*(p for p in W.rglob('*') if p.is_file())]}")
 assert s==old.read_text(),new
 ast.parse(new.read_text())
tree=ast.parse((B/'run_geometry.py').read_text());options=next(n.value for n in ast.walk(tree) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='options' for t in n.targets))
constants={x.arg:ast.literal_eval(x.value) for x in options.keywords if isinstance(x.value,ast.Constant)}
expected=dict(topcell='nssoc_clock_div4_v7_layout',run_mode='deep',thr=1,net_only='True',no_simplify='True',top_lvl_pins='True',combine_devices='False',purge='False',purge_nets='False',purge_devices='False',disable_tap_extraction='False')
assert constants==expected
assert {x.arg for x in options.keywords}==set(expected)|{'input','log','report','target_netlist'}
deck=Path('hw/soc/tools/ihp-lvs-5e6d592/ihp-sg13g2/libs.tech/klayout/tech/lvs/sg13g2.lvs');text=deck.read_text()
for needle in ["obj.to_s.downcase == 'true'",'SIMPLIFY = !bool_check?($no_simplify)','TOP_LVL_PINS = bool_check?($top_lvl_pins)','DISABLE_TAP_EXTRACTION = bool_check?($disable_tap_extraction)',"if NET_ONLY\n  logger.info('NET_ONLY enabled: apply extraction netlist options and skip comparison.')","apply_netlist_options.call(netlist, 'layout_netlist')"]:assert needle in text
netonly=text.split("if NET_ONLY\n  logger.info('NET_ONLY enabled:",1)[1].split('\nelse\n',1)[0]
assert '\n  align' not in netonly and '\n    success = compare' not in netonly
prior=json.loads((OLD/'geometry-execution.json').read_text());assert prior['status']=='FAIL_GEOMETRY_RETAINED'
assert 'AssertionError' in (OLD/'probe_device_locations.log').read_text()
result=dict(status='PASS_SOURCE_ONLY_DIVIDER_V7_WIRE_GEOMETRY',findings=[],utc=datetime.datetime.now(datetime.UTC).isoformat(),method=pin(__file__),freeze=pin(f),source_pins=freeze['producer_sources'],all_input_pins_rehashed=87,full_seven_source_inverse=True,bridge=pin(B/'geometry-source-bridge.json'),prior_failure=pin(OLD/'geometry-execution.json'),prior_peer=pin(OLD/'geometry-source-only-peer.json'),native_extraction_options=constants,deck=pin(deck),review=['Fresh native device extraction is necessary because original completed comparison graph intentionally simplified18parallel ptaps to1. Original completed LVS, old source freeze and actual V2 rejection remain unchanged. No earlier comparison result is relabeled as an unsimplified91device witness.','Read the pinned runset Boolean parsing, extraction branch, full apply_netlist_options and NET_ONLY path. True/False options explicitly disable simplify/combine/purge, enable top pins/tap extraction, and skip alignment/comparison. No alternate schematic/layout-netlist or implicit-net input supplied. Actual log must attest every operation, exit0 and both native outputs before any geometry stage.','Six readers differ only in fresh wire03/native01 database paths. Full runner inverse allows only new extraction step, fresh N root/guard/accounting, source checks and explicit provenance fields. Same CPU10/2GiB/core0/80MiB+24MiB/1GiB entry/512MiB floor, exact terminal cancellation/resource guards and no healthy elapsed deadline.','All91electricaldevices/283terminals,678totalleaves/587via stacks,38namednets/37metalcomponents and full location/parameter/terminal/net bijection remain mandatory future native assertions. All18physical contacts and85intrinsic body terminals remain explicit; no substrate spreading, qualifiedRC or clock waveform inference.'],native_or_reviewed_method_executed=False,controls_rerun=False,actual_new_extraction_results_claimed=False,qualified_pex=False,main_chip_integrated=False)
with (B/'geometry-source-only-peer.json').open('x') as out:json.dump(result,out,indent=2);out.write('\n')
print(json.dumps(dict(path=str(B/'geometry-source-only-peer.json'),**pin(B/'geometry-source-only-peer.json'))))
