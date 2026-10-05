# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Additive source-only actual-native syntax correction peer; no EDA/tests."""
from pathlib import Path
import ast,json,hashlib,datetime
B=Path(__file__).resolve().parent;R=B.parents[3]
def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
pins=json.loads((B/'native-schema-source-freeze01.json').read_text());assert len(pins)==7
for n,p in pins.items():assert pin(R/n)==p
bridge=json.loads((B/'native-schema-bridge01.json').read_text())
texts={}
for side in ['before','after']:
 text=''.join(x[side] for x in bridge['opcodes']);b=text.encode();p=dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest());assert p=={k:bridge[side][k] for k in ['bytes','sha256']};assert pin(bridge[side]['path'])==p;ast.parse(text);texts[side]=text
old={n.name:ast.dump(n) for n in ast.parse(texts['before']).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))};new={n.name:ast.dump(n) for n in ast.parse(texts['after']).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))};assert set(old)==set(new);assert [k for k in old if old[k]!=new[k]]==['validate_expanded_devices','main']
assert ast.dump(ast.parse(texts['after'].replace('        "check_pcie_clock_div4_v7_v2.py",\n','')).body[-2])==ast.dump(ast.parse(texts['before']).body[-2])
fixture=R/'sw/tests/fixtures/pcie_clock_div4_v7/native-deep-extracted.cir';actual=Path('/dev/shm/nssoc-div4-v7-checks-01/lvs/extracted.cir');assert pin(fixture)==pin(actual)==bridge['fixture']==bridge['fixture_actual_extracted']
log=B/'native-schema-controls01.log';assert '18 passed' in log.read_text()
launcher=B/'launch02.py';assert pin(launcher)==dict(bytes=3974,sha256='081d82e475278e5497bef32e35c1c7caeaec9a892dfba80dc866b086969e18cf')
prior=B/'source-only-peer03-rx.json';assert pin(prior)==dict(bytes=6415,sha256='c130db933d3594afe01790885debf3b770ae24f917e406e3c1c49e9f84a63307')
result=dict(status='PASS_SOURCE_ONLY_DIVIDER_V7_NATIVE_SCHEMA_V2',reviewer='/root/rx_route_resume',utc=datetime.datetime.now(datetime.UTC).isoformat(),findings=[],source_pins=pins,launcher=pin(launcher),source_freeze=pin(B/'native-schema-source-freeze01.json'),source_bridge=pin(B/'native-schema-bridge01.json'),prior_peer=dict(path=str(prior),**pin(prior)),method=pin(__file__),actual_fixture=dict(path=str(actual),**pin(actual)),saved_tests=dict(log=pin(log),count=18,rerun_by_peer=False),checks=['Entire original/new source reconstructed from exact byte bridge; all7 source pins and actual native extracted fixture rehashed. Only validate_expanded_devices and self-pinning main differ among all function/class ASTs.','Auxiliary parser now requires exact actual rppd ps=0u, b=0, m=1 and MIM A/P plus m=1; rejects duplicate fields, undeclared dimensions/units/nonpositive/nonfinite values. Decimal equality enforces A=W*L and P=2*(W+L).','All33 resistor and6MIM W/L pairs must equal the unchanged frozen circuit census; HBT Nx/we/le and34count plus18-tap A72p/P144u and74total gates unchanged. Passive geometry Counter supplements actual topology LVS; it does not replace connectivity comparison.','18 saved test outcomes correspond to one actual fixture test (prior parser still rejects) and17 real fixture text mutations covering ps, multiplier, b, W/L, A/P, duplicate, unit, NaN, taparea/perimeter andHBT. No ideal/reference substitution or native result overwritten.','Full launcher02 read: final exact peer/source/self gate unchanged; adds complete existing layout relative-file pin map equality, requires fresh checks root, usesV2 checker without generation, and samePID fsynced checkpoint/exec. CPU10/2GiB/1GiBentry/512MiBlive/80MiBown/nohealthytimeout/5scleanup code remains exact.','All prior fixed terminal cancellation/resource guards, independent actual560mainDRC/deep+flatLVS/negative controls/LEF flow unchanged. Old native01 failed auxiliary parser outcome is preserved; V2 still requires fresh complete nativechecks on exact existing GDS.'],native_eda_executed=False,tests_rerun=False,physical_acceptance=False,qualified_pex=False,scope='Source correction and saved local controls only. No fresh native02 DRC/LVS/LEF acceptance, extracted division, qualified PEX, chip/PHY or manufacturing signoff. Launch manifest must bind final exact peer and complete unchanged layout/runtime/input census before execution.')
p=B/'native-schema-source-only-peer01-rx.json';assert not p.exists();p.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(path=str(p),**pin(p))))
