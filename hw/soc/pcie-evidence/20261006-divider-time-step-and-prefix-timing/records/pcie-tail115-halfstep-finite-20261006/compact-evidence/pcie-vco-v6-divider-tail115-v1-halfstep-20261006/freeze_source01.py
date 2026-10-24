# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import hashlib,json,shutil,sys
R=Path.cwd();B=Path(__file__).resolve().parent;L=B.parent/'pcie-vco-v6-divider-tail115-v1-wire-v1-20261006';F=B.parent/'pcie-tail115-layout-wire-loaded-finite-20261006'
def pin(p):
 p=Path(p)
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
assert not(B/'source-freeze01.json').exists()
old=json.loads((L/'source-freeze01.json').read_text());assert all(pin(p)==v for p,v in old['pins'].items())
paths=set(map(Path,old['pins']))
paths.update([L/'source-freeze01.json',L/'source-only-peer01-rx.json',L/'sealer-source-only-peer-rx.json',L/'validation-06-01.json',L/'members-06-01.json',L/'review-06-01.json',L/'release-06-01.json',F/'event-boundary-diagnosis06.json',F/'event-diagnosis-summary06.json'])
assert json.loads((L/'release-06-01.json').read_text())['status']=='PASS_IMMUTABLE_RELEASE_ROUNDTRIPS'
control=json.loads((B/'derivative-controls01.json').read_text());assert control['status']=='PASS_HALFSTEP_EXACT_RECIPE_DECK_AND_RESOURCE_CONTROLS'and len(control['checks'])==7
for root in [B,L/'pytest-handoff01',L/'pytest01']:
 paths.update(p for p in root.rglob('*')if p.is_file()and '__pycache__'not in p.parts and p.suffix!='.pyc')
paths.update([R/'hw/soc/tools/cocotb-venv/bin/python',R/'hw/soc/tools/cocotb-venv/pyvenv.cfg'])
N=Path('/dev/shm/nssoc-vco-v6-divider-tail115-v1-wire-06-01');r=json.loads((N/'result.json').read_text());paths.update(Path(p)for p in r['inputs']);paths.update([N/'result.json',N/'wave.raw.gz'])
assert not Path('/dev/shm/nssoc-vco-v6-divider-tail115-v1-halfstep-06-01').exists()
record=dict(status='FROZEN_SAME_PHYSICS_455_HALFSTEP_COMPLETE_34NS_PENDING_PEER',pins={str(p.resolve()):pin(p)for p in sorted(paths)},new_sources={str(p.resolve()):pin(p)for p in [B/'characterize_halfstep01.py',B/'launch_probe01.py',B/'seal_probe01.py',B/'compare_saved_steps01.py']},parent_source_freeze=pin(L/'source-freeze01.json'),actual_derivative_controls=control,inherited_controls=dict(source=old['controls'],handoff=old['actual_handoff_controls']),predeclared=dict(vctrl=.6,stop_s=34e-9,step_s=2.5e-12,window_s=[4e-9,34e-9],intrinsics=455,HBT=64,contacts=31,vectors=956,wire_R=1271,wire_C=1414,CPU=10,AS=2*1024**3,own_limit=128*1024**2,entry_floor=1024**3,shared_floor=512*1024**2,receipt_reserve=2*1024**2,elapsed_watchdog=None),acceptance_changes=False,physical_changes=False,resource_reason='Full5ps compressed raw48.56MB; doubled full2.5ps raw does not fit original80MiB. Root explicitly approved separately bounded128MiB namespace, keeping AS/shared floors unchanged.',scope='Source-only full34ns restart fromtime0 with unchanged devices/bias/wires/initialization/455safety/strictcount predicates. Original5psFAIL and raw retained. Fixedordinal and period diagnostics add no acceptance override.')
(B/'source-freeze01.json').write_text(json.dumps(record,indent=2)+'\n');print(len(paths),pin(B/'source-freeze01.json'))
