"""Bind complete saved controls and static actual native inputs before source peer."""
from pathlib import Path
import hashlib,json
R=Path.cwd();B=Path(__file__).resolve().parent;OLD=B.parent/'pcie-integrity-v24-20261006'
def pin(p):
 p=Path(p)
 with p.open('rb') as s:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(s,'sha256').hexdigest())
f=json.loads((B/'source-freeze04.json').read_text());validation=B/'pcie-integrity-v25-current-controls02-validation-20261006.json';saved=B/'saved-controls-peer-vco04.json'
s=json.loads(saved.read_text());assert s['status']=='PASS_INDEPENDENT_SAVED_V25_CURRENT_43_FUNCTIONAL_PREDICATES' and not s['findings'] and s['validation']==pin(validation)
names=['native_lifecycle02.py','measure_registered_boundary.py','balanced_import02.py','prove_balanced_import.py','balanced_preplacement02.py','review_timing.py','analyze_critical_path.py','run_balanced_map03.py','continue_native03.py']
methods={str(B/n):pin(B/n) for n in names}
methods[str(B/'native-source-bridges-draft01.json')]=pin(B/'native-source-bridges-draft01.json')
parentpeer=json.loads((OLD/'native-source-only-peer01.json').read_text());static=dict(parentpeer['observed_static_native_input_pins'])
T=R/'hw/soc/tools/oss-cad-suite';P=Path('/home/hasanmelih/.ciel/ciel/ihp-sg13g2/versions/c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c/ihp-sg13g2/libs.ref/sg13g2_stdcell')
extra=[T/'libexec/yosys',T/'libexec/yosys-abc',T/'lib/ld-linux-x86-64.so.2',R/'hw/soc/tools/physical/librelane-3.0.5-x86_64.AppImage',R/'hw/soc/out/pcie-loop-wide-delivery-20261004/yosys-abc-help.txt',P/'lef/sg13g2_tech.lef',P/'lef/sg13g2_stdcell.lef']
extra += [P/'lib'/name for name in ['sg13g2_stdcell_slow_1p08V_125C.lib','sg13g2_stdcell_typ_1p20V_25C.lib','sg13g2_stdcell_fast_1p32V_m40C.lib']]
extra += [B.parent/f'pcie-integrity-v{n}-20261005/timing-comparison.json' for n in (11,17,19)]
extra += [B.parent/'pcie-integrity-v4-20261005/review_timing_groups.py',OLD/'native-source-only-peer01.json',B/'source-only-peer-rx04.json']
static.update({str(p):pin(p) for p in extra})
for path,p in static.items():assert pin(path)==p,path
sources=dict(f['sources']);sources.update(static)
policy=dict(status='FROZEN_V25_NATIVE_CONTINUATION_REQUIRES_SOURCE_PEER',boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),method_pins=methods,source_pins=sources,controls=dict(validation=dict(path=str(validation),**pin(validation)),independent_peer=dict(path=str(saved),**pin(saved))),PLL=dict(scope='Existing V5 local native and separate V2 publisher untouched; no adoption/signals/duplicate',checkpoint=str(R/'hw/soc/out/pcie-pll-local-spool-v1-20261006/launch01/active-checkpoint.json')),CPU=6,AS_bytes=2*1024**3,clock_period_ns=4.0,actual_stage_paths={n:pin(B/n) for n in names if n not in ('native_lifecycle02.py','continue_native03.py')},fresh_outputs=[f'/dev/shm/nssoc-integrity-v25-balanced-{kind}-01'for kind in ('map','import','sta')],native_lifecycle_ancestry=json.loads((OLD/'continuation-policy01.json').read_text())['native_lifecycle_ancestry'],additional_static_actual_native_inputs=static,no_new_native_started=True)
p=B/'continuation-policy01.json';assert not p.exists();p.write_text(json.dumps(policy,indent=2)+'\n')
old=OLD/'detach_native01.py';body=old.read_text().replace('integrity-v24','integrity-v25').replace('V24','V25').replace(repr(pin(OLD/'continuation-policy01.json')),repr(pin(p)))
# Bind boot explicitly before any prospective new session, with the old native
# birth guard and all method/source/peer gates unchanged.
marker="policy=json.loads(p.read_text())";assert body.count(marker)==1
body=body.replace(marker,marker+"\nassert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==policy['boot_id']")
out=B/'detach_native01.py';assert not out.exists();out.write_text(body)
(B/'native-launch-source-bridge01.json').write_text(json.dumps(dict(parent=str(old),parent_pin=pin(old),candidate=str(out),candidate_pin=pin(out),parent_body=old.read_text(),candidate_body=body,policy=pin(p)),indent=2)+'\n')
print(json.dumps(dict(policy=pin(p),detacher=pin(out),methods=len(methods),sources=len(sources))))
