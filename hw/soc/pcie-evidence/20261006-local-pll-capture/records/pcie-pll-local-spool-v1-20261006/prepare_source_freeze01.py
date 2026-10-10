from pathlib import Path
import hashlib,json,sys,xml.etree.ElementTree as ET
R=Path.cwd();B=R/'hw/soc/out/pcie-pll-local-spool-v1-20261006';sys.path.insert(0,str(R/'scripts'))
import characterize_pcie_pll_acquisition_v5 as m
import publish_pcie_local_spool_v1 as worker

def pin(path):
 p=Path(path);h=hashlib.sha256();n=0
 with p.open('rb')as f:
  while b:=f.read(1024**2):n+=len(b);h.update(b)
 return dict(path=str(p.resolve()),bytes=n,sha256=h.hexdigest())
products=['scripts/durable_pcie_spool_v1.py','scripts/characterize_pcie_pll_acquisition_v5.py','scripts/publish_pcie_local_spool_v1.py','sw/tests/test_pcie_durable_spool_v1.py','sw/tests/test_pcie_pll_local_capture_v1.py','sw/tests/test_pcie_local_spool_publisher_v1.py']
snapshot=B/'source-final01';snapshot.mkdir()
for name in products:
 p=snapshot/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((R/name).read_bytes())
dependencies={}
for module in list(sys.modules.values()):
 p=getattr(module,'__file__',None)
 if p and Path(p).resolve().is_relative_to(R/'scripts') and Path(p).is_file():dependencies[str(Path(p).resolve())]=pin(p)
for name in ['.venv/bin/python','.venv/pyvenv.cfg','sw/tests/test_pcie_native_publisher_v4.py','sw/tests/test_pcie_native_publisher_v3.py','sw/tests/fixtures/pcie_pll_acquisition_v3/connected-loop-bench.cir']:
 dependencies[str(R/name)]=dict(pin(R/name),path=str(R/name))
controls=[]
for stem in ['local-controls02','local-controls03','local-controls04','bridge-controls01','bridge-controls02','publisher-controls01','publisher-controls02','publisher-controls03','publisher-controls04']:
 p=B/(stem+'.xml');x=ET.parse(p).getroot();cases=list(x.iter('testcase'));fail=sum(bool(list(c.iter('failure'))or list(c.iter('error')))for c in cases)
 controls.append(dict(name=stem,xml=pin(p),log=pin(B/(stem+'.log')),cases=len(cases),passed=len(cases)-fail,failed=fail))
raw=[]
for root in sorted(Path('/dev/shm').glob('nssoc-spool-*controls*')):
 for p in sorted(root.rglob('*')):
  if p.is_file()and not p.is_symlink():raw.append(pin(p))
evidence=[]
for p in sorted(B.rglob('*')):
 if p.is_file()and p!=Path(__file__)and not p.name.endswith('.pending') and p.name not in ['prepare-source-freeze01.log','source-freeze01.json']:
  evidence.append(pin(p))
f=dict(status='FROZEN_LOCAL_CAPTURE_V5_AND_INDEPENDENT_PUBLISHER_FOR_PEER',sources=[pin(R/p)for p in products],dependencies=dependencies,evidence=evidence,actual_fixture_files=raw,controls=controls,distinct_current_predicates=60,bridge_ledger=m.BRIDGES,unchanged_physics=['539devices','TSTEP2.5ps','TMAX1.25ps','1us','100ppm','50ps','no_phase_offset_removal','original_OP/startup/safety/acquisition'],native_not_launched=True,public_network_not_used_by_controls=True,scope='Local core28 + capture/ownedFIFO15 + independentworker17 distinct current predicates. Worker03 two generic guard-injection tests replaced by04 actual near-cap file and free-space input predicates; other15 unchanged. Initial publisher01 had12PASS2FAIL from unsupported owner kind publication, corrected to inherited publisher. No real SPICE/native waveform, no public GitHub controls. Full independent source/saved peer and fresh detached launcher gates still required.')
p=B/'source-freeze01.json';p.write_text(json.dumps(f,indent=2)+'\n');print(json.dumps(dict(freeze=pin(p),sources=len(products),dependencies=len(dependencies),evidence=len(evidence),actualfiles=len(raw),controls=controls),indent=2))
