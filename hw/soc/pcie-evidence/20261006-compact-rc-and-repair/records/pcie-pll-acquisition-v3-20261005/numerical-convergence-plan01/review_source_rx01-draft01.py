# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Source/closed-control peer only: never call native producer or replay."""
from pathlib import Path
import hashlib,json,sys,inspect,xml.etree.ElementTree as ET
R=Path.cwd();B=Path(__file__).resolve().parent
sys.path.insert(0,str(R/'scripts'))
import characterize_pcie_pll_acquisition_v4 as m
import review_pcie_pll_acquisition_v2 as v
import compare_pcie_pll_acquisition_pair_v2 as p
def pin(x):
 x=Path(x)
 with x.open('rb')as f:return dict(bytes=x.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
fpath=B/'source-freeze01.json';assert pin(fpath)==dict(bytes=3144,sha256='db47d293442b236b2a11774d264d6651023a1bf39077adc98a33a29fa876f84e');f=json.loads(fpath.read_text())
for name in ('sources','parent_methods'):assert f[name]=={x:pin(R/x)for x in f[name]}
assert pin(B/'method-controls03.log')==f['controls']['log'];assert pin(B/'method-controls03.xml')==f['controls']['xml'];t=ET.parse(B/'method-controls03.xml');cases=t.findall('.//testcase');assert len(cases)==43 and not t.findall('.//failure')and not t.findall('.//error')and not t.findall('.//skipped')
assert pin(B/'test-source02-collection-failure.py')==f['retained_harness_collection_failure']['source']
assert pin(B/'method-controls02.log')==f['retained_harness_collection_failure']['log']
assert pin(B/'saved-startup-and-max125-proposal01.json')==f['proposal']
originals={'Meter':inspect.getsource(m.previous.namespace['Meter']),'startup_proof':inspect.getsource(m.base.startup_proof),'run':m.previous.run_source,'main':m.previous.main_source}
generated={'Meter':m.meter_source,'startup_proof':m.startup_source,'run':m.run_source,'main':m.main_source}
for name,z in generated.items():
 a=z
 for old,new in reversed(m.BRIDGES[name]['exact_replacements']):assert a.count(new)==1;a=a.replace(new,old)
 assert a==originals[name]
 assert hashlib.sha256(a.encode()).hexdigest()==m.BRIDGES[name]['original_sha256']
 assert hashlib.sha256(z.encode()).hexdigest()==m.BRIDGES[name]['modified_sha256']
assert m.capture.__globals__ is m.namespace and m.run.__globals__ is m.namespace
assert m.namespace['Meter']is m.Meter and m.namespace['capture']is m.capture and m.namespace['startup_proof']is m.startup_proof and m.namespace['stream_deck']is m.stream_deck
assert m.namespace['STOP']==1e-6 and m.namespace['TSTEP']==2.5e-12 and m.namespace['TMAX']==1.25e-12
assert hashlib.sha256(m.capture_source.encode()).hexdigest()==m.base.BRIDGES['capture']['modified_sha256']
for name in ('native_wait','guard','FLOOR','CAP','PART_BYTES','life','OwnedPublisherV3'):assert m.namespace[name]is m.previous.namespace[name]
for name,b in v.BRIDGES.items():
 a=inspect.getsource(getattr(v.previous,name));z=a
 for old,new in b['exact_replacements']:assert z.count(old)==1;z=z.replace(old,new)
 assert hashlib.sha256(z.encode()).hexdigest()==b['modified_sha256']
 for old,new in reversed(b['exact_replacements']):assert z.count(new)==1;z=z.replace(new,old)
 assert z==a
assert v.review.__globals__['producer']is m and v.review.__globals__['bind_completed_capture']is v.bind_completed_capture
assert p.compare is p.previous.compare and p.WINDOWS==((800e-9,900e-9),(900e-9,1e-6))and p.FREQUENCY_LIMIT_PPM==100and p.PHASE_LIMIT_S==50e-12
old=inspect.getsource(p.previous.load_verified);new=old.replace("Path(p).name == 'review_pcie_pll_acquisition_v1.py'","Path(p).name == 'review_pcie_pll_acquisition_v2.py'")
assert hashlib.sha256(new.encode()).hexdigest()==p.BRIDGE['modified_sha256'];assert p.load_tight_verified.__globals__['REVIEWER_SHA']==pin(R/'scripts/review_pcie_pll_acquisition_v2.py')['sha256']
r=dict(status='PASS_SOURCE_ONLY_PLL_RETAINED_TSTEP_MAXSTEP125',freeze=pin(fpath),findings=[],method=pin(__file__),verified_sources=f['sources'],verified_parent_count=len(f['parent_methods']),actual_saved_controls=43,whole_producer_method_inverses=list(generated),whole_reviewer_method_inverses=list(v.BRIDGES),private_capture_meter_run_bindings_checked=True,scope='Full four sources and relevant frozen parent bodies read; source imports only, no tests rerun, production function, SPICE, public replay, or comparison executed. Exact retained2.5ps TSTEP / new1.25ps TMAX, same1us/539devices/100ppm/50ps and no phase-offset removal. Changed Meter enforces TMAX; startup advisory remains TSTEP. Declaration must be pinned before new run. Wholedeck onlyTMAX and byte-identical825-value OP payload are final pair gates. Prior failed timestep comparison remains failed; this permits a distinct experiment, not numerical or physical closure.')
(B/'source-only-peer-rx01.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
