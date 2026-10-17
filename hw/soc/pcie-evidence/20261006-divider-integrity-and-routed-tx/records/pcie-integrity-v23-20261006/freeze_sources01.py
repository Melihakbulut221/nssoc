from pathlib import Path
import ast,hashlib,json,datetime,runpy,shutil
R=Path.cwd();B=Path(__file__).resolve().parent
files=['scripts/generate_pcie_integrity_header_v23.py','hw/soc/rtl/pcie/soc_pcie_gen3_framer_rx_integrity_v23.v','hw/soc/rtl/pcie/soc_pcie_gen3_continuous_rx_integrity_v23.v','hw/soc/tb/cocotb/Makefile.soc_pcie_gen3_continuous_rx_integrity_v23','scripts/check_pcie_gen3_continuous_rx_integrity_v23.py','hw/soc/tb/cocotb/test_soc_pcie_gen3_continuous_rx_integrity_v23.py','sw/tests/test_pcie_gen3_continuous_rx_integrity_v23.py','sw/tests/test_pcie_gen3_integrity_v23_miter.py','sw/tests/test_pcie_gen3_integrity_v23_header.py']
def pin(p):
 with Path(p).open('rb') as f:return dict(bytes=Path(p).stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
for p in files:
 if p.endswith('.py'):ast.parse((R/p).read_text())
q=runpy.run_path(str(R/files[-1]));q['test_exact_generated_inverse_and_wrapper_bridge']()
u=runpy.run_path(str(R/files[-3]));rtl=R/'hw/soc/rtl/pcie'
for name,module,before,after,count,case in u['FAULTS']:assert (rtl/(module+'.v')).read_text().count(before)==count,name
m=runpy.run_path(str(R/files[-2]))
for name,(before,after) in m['HEADER_FAULTS'].items():assert (R/files[1]).read_text().count(before)==1,name
out=B/'sources01';out.mkdir()
for p in files:
 t=out/p;t.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(R/p,t)
f=dict(status='FROZEN_V23_ADJACENT_ACCEPTED_HEADER_EXPERIMENT',utc=datetime.datetime.now(datetime.UTC).isoformat(),sources={p:pin(R/p) for p in files},baseline={'path':'hw/soc/rtl/pcie/soc_pcie_gen3_framer_rx_integrity_v22.v',**pin(q['GEN']['SOURCE'])},contracts={n:pin(B/n)for n in ['architecture-contract01.json','architecture-contract02-observer.json','architecture-source-only-peer-rx01.json','measured-cone-diagnosis04.json']},predicates=dict(public_cases=18,original_prefix_cases=17,public_mutants=12,cycle_miter_positive=1,miter_product_mutants=12,observer_negative=1,literal_positive=1,literal_mutants=5,source_inverse_checks=2,total_pytest_selected=35,excluded_MAX4118=2),resources=dict(cpu=6,address_space_bytes=2*1024**3,clock_ns=4,maximum=150,ring_dwords=64,healthy_elapsed_timeout=None),scope='No HDL or physical controls yet. Fresh header relation banks from failed V22 timing baseline; V11 stable baseline unchanged. Temporal reference uses old accepted predecessor validity carried with exact bank IDs, same-edge cache write observer compares before/after because V22 andV23 caches are identical. Original cache literal4096 result reusable only for byte-identical cache body, not claimed new execution. All initial17public cases prefix exact after version normalization; added18th real line-rate/all16positions and strict predecessor/minimum-boundary witnesses. Four-state component covers557056 declared binary tuples and1440 selectedX/Z cases, not arbitrary sequentialstate equivalence.')
p=B/'source-freeze01.json';assert not p.exists();p.write_text(json.dumps(f,indent=2)+'\n');print(pin(p))
# Whole-source launch derivative; no process execution here.
old=R/'hw/soc/out/pcie-integrity-v22-20261006/launch_controls02.py';s=old.read_text();s=s.replace('V22','V23').replace('v22','v23').replace('source-freeze02','source-freeze01').replace('source-only-peer-vco02','source-only-peer-rx01').replace('QUARANTINED_CACHE','ADJACENT_HEADER_RELATION').replace('integrity_v23_cache.py','integrity_v23_header.py').replace('fe7b6055e64f1498052da96b5e1d8da2bbe67667dbedf411cf94240b40ebc02d',pin(p)['sha256']).replace('Separate V23 cache writer qualification fromV21; same latency, allpublic cyclemiter and cachefault quarantine;','Separate V23 adjacent accepted header relation fromV22; same latency, allpublic cyclemiter and predecessor ownership;')
(B/'launch_controls01.py').write_text(s)
old=R/'hw/soc/out/pcie-integrity-v22-20261006/detach_controls02.py';s=old.read_text();s=s.replace('V22','V23').replace('v22','v23').replace('launch_controls02','launch_controls01').replace('source-freeze02','source-freeze01').replace('source-only-peer-vco02','source-only-peer-rx01').replace('QUARANTINED_CACHE','ADJACENT_HEADER_RELATION')
s=s.replace("{'bytes': 3378, 'sha256': 'c743ff7643d66487bb96ab60d1b4fa01cf9cbb28756009c454db6b30685eae88'}",repr(pin(B/'launch_controls01.py'))).replace("{'bytes': 2533, 'sha256': 'fe7b6055e64f1498052da96b5e1d8da2bbe67667dbedf411cf94240b40ebc02d'}",repr(pin(p)))
(B/'detach_controls01.py').write_text(s)
print('Frozen9sources and narrow launch/detach derivatives; no HDL/native')
