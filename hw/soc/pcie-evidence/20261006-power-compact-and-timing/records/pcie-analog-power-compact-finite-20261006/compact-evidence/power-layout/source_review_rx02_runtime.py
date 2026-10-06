"""Read-only closure of launch runtime pins after the full powerV2 source peer."""
from pathlib import Path
import hashlib
import json
R=Path('/home/hasanmelih/Documents/ChatGPT/nnsoc')
B=Path(__file__).resolve().parent
def pin(p):
    p=Path(p)
    with p.open('rb') as f:
        return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
f=json.loads((B/'source-freeze02.json').read_text())
body=json.loads((B/'source-body-review02-rx.json').read_text())
assert body['freeze']==pin(B/'source-freeze02.json')
runtime=B/'launch-runtime-freeze02.json'
assert pin(runtime)==dict(bytes=27298,sha256='a6188540be493b7bad1af95df57f03bcc631ffa3efdb99c396a49681067d20cb')
rr=json.loads(runtime.read_text())
assert rr['source_freeze']==body['freeze']
for p,v in rr['inputs'].items():assert pin(p)==v
assert str(Path(rr['selected_python']).resolve())==rr['selected_python_realpath']
assert rr['selected_pdk_input_prefix']==rr['selected_pdk']+'/'
assert rr['PDK_files_already_in_source_freeze']=={p:v for p,v in f['inputs'].items() if p.startswith(rr['selected_pdk_input_prefix'])}
assert len(rr['PDK_files_already_in_source_freeze'])==rr['selected_pdk_input_count']==90
prior=json.loads(Path(rr['prior_manifest']).read_text())
assert prior['python']==rr['selected_python'] and prior['pdk']==rr['selected_pdk']
prep=B/'prepare_launch02.py'
assert pin(prep)==dict(bytes=2288,sha256='a12200111929b07a58a541b77ab15384918d1328f9a235faf6162a2ec58f0c7a')
assert 'inputs.update(runtime[\'inputs\'])' in prep.read_text()
for p,v in f['product_sources'].items():assert pin(p)==v
assert pin(B/'launch02.py')==f['launcher']
r=dict(status='PASS_SOURCE_ONLY_DIVIDER_V7_POWER_V2',
       freeze=pin(B/'source-freeze02.json'),source_pins=f['product_sources'],launcher=pin(B/'launch02.py'),findings=[],
       methods={str(p):pin(p) for p in [B/'source_review_rx02.py',Path(__file__),prep]},
       full_source_review=pin(B/'source-body-review02-rx.json'),
       prior_rejected_candidate=pin(B/'source-only-peer-rx-candidate01-findings.json'),
       launch_runtime_addendum=pin(runtime),runtime_inputs=rr['inputs'],selected_frozen_pdk_inputs=90,
       review='Full five product sources, six complete whole-byte bridges and launcher read;313 frozen inputs plus three selected launch runtime/manifest paths independently rehashed. All47 actual added native via leaves must bind uniquely at exact transforms with complete independent PDK cut/enclosure regions; all678 original leaf placements and geometry are retained, old drawings/texts/pins remain exact or allowed-layer subsets. Four predeclared real geometry corruptions include removing one added Via4 array. Independent Decimal arithmetic confirms old2x1 Via4 middle row exactly retained by2x3 and correct enclosure containment. Twelve old checker helper/lifecycle ASTs and all21 old native gates unchanged. Saved60 source/parser/lifecycle tests inspected, including six actual owned-process receipts; not rerun. Supplemental preparation now pins both selected Python/symlink target, old manifest and already frozen90-file selected PDK prefix before constructing launch manifest.',
       limits=dict(cpu=10,native_AS_bytes=2*1024**3,own_scratch_bytes=80*1024**2,launch_reserve_bytes=24*1024**2,entry_free_bytes=1024**3,continuous_free_bytes=512*1024**2,healthy_elapsed_watchdog=None),
       authorization_scope='Source-only approval for fresh actual standalone powerV2 generation and its owned geometry/mainDRC/deep-flatLVS/LEF/fault campaign. Require the reviewed prepare_launch02/runtime-addendum before the reviewed samePIDexec launcher.',
       limitations='No native physical generation, GDS audit, DRC/LVS, RC extraction or loaded analog simulation executed in this peer. Source-derived via-spacing correction is not a measured DRC result. Fresh actual geometry/DRC/LVS and then new RC plus loaded455 screening remain mandatory. No qualifiedPEX, fullPHY, mainchip or manufacturing acceptance.')
p=B/'source-only-peer02-rx.json';assert not p.exists();p.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(path=str(p),**pin(p))))
