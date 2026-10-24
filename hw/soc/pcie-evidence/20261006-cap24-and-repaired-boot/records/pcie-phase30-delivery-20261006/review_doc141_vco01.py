"""Saved-evidence numerical/doc review, no EDA, simulator or waveform replay."""
from pathlib import Path
import hashlib,json,re
R=Path.cwd();B=Path(__file__).resolve().parent;F=R/'hw/soc/out/pcie-cap24-layout-wire-loaded-finite-20261006';BOOT=R/'hw/soc/out/npu-eco-boot-final-20261006';W=R/'hw/soc/out/pcie-cap24-wave-root-20261006';L=R/'hw/soc/out/pcie-vco-v6-divider-cap24-v1-wire-v1-20261006';N=Path('/dev/shm/nssoc-vco-v6-divider-cap24-v1-wire-06-01')
inputs={}
def pin(p):
 p=Path(p)
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def read(p):inputs[str(p)]=pin(p);return p.read_text()
def load(p):return json.loads(read(p))
doc=read(R/'docs/141-pcie-capacitor-layout-and-repaired-boot.md');d137=read(R/'docs/137-npu-initialization-reconvergence.md');wave=load(W/'result.json');method=read(W/'review.py');native=load(N/'result.json');validation=load(L/'validation-06-01.json');finite=load(F/'ready-finite01.json');inventory=load(B/'closed-review01.json')
assert wave['capture']['values']==native['values']==6523869 and native['rows']==6817
assert wave['capture']['result']==pin(N/'result.json') and native['status']=='FAIL_NATIVE_LOADED_FEEDBACK_SCREEN' and native['safety']['passed'] and len(native['safety']['all_device_bounds'])==455
assert len(wave['capture']['all64_HBT_bounds_recomputed'])==64
assert f"{wave['capture']['minimum_hbt_vce']:.6f}"=='0.485642' and 'all 64 HBTs over 4–34 ns is 0.485642 V' in doc and 'minimum settled' in doc
assert 'mask=(t>=4e-9)&(t<=34e-9)' in method
signals=['VCO source','First latch slave collector /2','Second latch MASTER collectors','Second latch SLAVE collectors']
for label,interval in [('early',(4,20)),('late',(22,34))]:
 window=wave['diagnostic_windows'][label];assert (window['start_ns'],window['end_ns'])==interval
 for name in signals:assert f"{window['signals'][name]['mean_crossing_rate_hz']/1e9:.6f}"in doc
assert 'Both full-run divider function checks' in doc and 'diagnostic windows do not replace' in doc and 'does not establish a unique analog cause' in doc
for relative in re.findall(r'!\[[^]]*\]\(([^)]+)\)',doc):
 p=(R/'docs'/relative).resolve();assert p.is_file();assert pin(p)==wave['plot'];inputs[str(p)]=pin(p)
# Exact selected physical and graph counts, not merely headline statuses.
P=R/'hw/soc/out/pcie-divider-v8-cap-v1-20261006';c=load(Path('/dev/shm/nssoc-div4-v8-cap-v1-checks-01/result.json'));assert len(c['steps'])==21 and len(c['power_geometry_audit']['controls'])==6
assert c['power_geometry_audit']['unchanged_intrinsics']==89 and c['power_geometry_audit']['changed_mim_dimensions_um']=={'DIV__XCN':[20,24],'DIV__XCP':[20,24]}
p=load(P/'native-saved-peer-rx.json');assert p['findings']==[] and p['checks']==pin(Path('/dev/shm/nssoc-div4-v8-cap-v1-checks-01/result.json'))
assert len(inventory['sources'])==26 and inventory['members']==1294 and len(inventory['archives'])==5 and len(inventory['public_assets'])==6
assert all(a['authenticated_roundtrip']and a['anonymous_roundtrip']for a in inventory['public_assets'])
assert not any(inventory[x]for x in ['full_phy_acceptance','full_chip_final_timing_accepted','production_acceptance'])
assert validation['archive']['bytes']==48827684 and validation['archive']['sha256']=='30e94da711cc76aff8cb5e67fd415f887e3a44b5c3d9208d9d790b89725ae48f' and validation['members']==187
# Boot exact raw tokens, source revision, unchanged-bound acceptance and independent saved peer.
b=load(BOOT/'result.json');v=load(BOOT/'nssoc-npu-eco-full-boot-validation-20261006.json');peer=load(BOOT/'saved-boot-peer-pll01.json');ready=load(BOOT/'readiness01.json');log=read(BOOT/'boot.log')
assert b['status']=='PASS_FOUR_STATE_MAPPED_BOOT_AND_POWER_ON_MBIST_ONLY' and b['boot_execution']['returncode']==0
assert b['cycle_bound']==3000000 and b['github_source_commit']=='c82d1280052c0da65281d87cda9af3b1c6177291'
assert f"{b['boot_execution']['elapsed_s']:,.3f}"in doc
for line in ['QUALIFICATION_MBIST PASS cycles=983043','LOGICROM_GL cycles=1596123 checks=28 fails=00000000 code=00000000 magic=600dc0de watchdog=1/0/0 flash_violations=0 uart_pass=1 framing=0','LOGICROM_GL PASS checks=28']:
 assert log.count(line)==1 and line in doc
assert 'all\n28 firmware checks' in d137 and 'passes at cycle 1,596,123' in d137
assert peer['status']=='PASS_INDEPENDENT_SAVED_STRICT_NPU_ECO_BOOT_AND_MBIST' and peer['findings']==[] and peer['result']==pin(BOOT/'result.json') and peer['raw_boot_log']==pin(BOOT/'boot.log')
assert peer['independent_native_truth_recount']['factored']['vectors']==256 and peer['independent_native_truth_recount']['miswired_mux']['vectors']==256
assert ready['status']=='READY_FOR_REVIEWED_PHYSICAL_EXPERIMENT_ONLY' and not ready['physical_flow_executed'] and not ready['timing_accepted']
assert v['member_count']==211 and v['archive']['bytes']==15941823 and v['archive']['sha256']=='329168d2296c77f92587f3d4baa6c5924eb9944300f1be6fb3529500ff6ef6cf'
for a in [v['archive'],validation['archive']]:
 p=Path(a['path']);assert pin(p)=={k:a[k]for k in ['bytes','sha256']};inputs[str(p)]=pin(p)
assert all(pin(p)==x for p,x in inputs.items())
r=dict(status='PASS_DOC141_ANALOG_AND_STRICT_BOOT_NUMERICAL_SCOPE_REVIEW',findings=[],method=pin(Path(__file__)),inputs=inputs,resolved_findings=[dict(original='VCE minimum did not explicitly name settled4–34ns interval.',resolution='Root revised text to minimum settled VCE across64HBTs over4–34ns; exact original reader mask/native field verified.')],checked=['Eight table frequencies match actual independent early/late mapped-terminal windows at printed precision.','Complete34ns functional FAIL and455 electrical PASS retained;64-HBT minimum scoped4–34ns, no early-window acceptance or unique-cause claim.','Actual21native gates/six geometry faults and89unchanged device count verified.','Exact loaded archive187members48827684bytes and real boot archive211members15941823bytes rehashed.','Real native raw MBIST983043 and28/1596123 qualification lines,return0,5457.272s,sourcecommit and3Mcycle bound agree with docs141/137.','Independent saved boot peer matches current raw log/result; both256-vector native truth tables andreadiness-only scope preserved.','Finite cut26sources/5archives/1294members/6authenticated+anonymous assets checked against root closed readback; no reexecution of full archive/member orwave peers.'],scope='Independent document/source-bound saved-result review only. No producer, native, HDL, EDA or waveform rerun. Updated doc137 boot claims reviewed; earlier unit/mapping paragraphs rely on their already independent saved reviews. No physical adoption, final timing, fullPHY or production acceptance.')
p=B/'doc141-review-vco01.json';assert not p.exists();p.write_text(json.dumps(r,indent=2)+'\n');print(pin(p))
