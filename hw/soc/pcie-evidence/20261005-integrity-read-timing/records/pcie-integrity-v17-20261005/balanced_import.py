# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Discard only signed wire metadata unsupported by OpenSTA; map actual ties."""
from pathlib import Path
import json,hashlib,subprocess,resource,signal,os,time,shutil
def interrupted(signum,frame):raise InterruptedError(f'Signal{signum}')
for sig in (signal.SIGINT,signal.SIGTERM):signal.signal(sig,interrupted)
R=Path.cwd();OLD=Path('/dev/shm/nssoc-integrity-v17-balanced-map-01');OUT=Path('/dev/shm/nssoc-integrity-v17-balanced-import-01');assert shutil.disk_usage('/dev/shm').free>=700*1024**2;OUT.mkdir()
TOP='soc_pcie_gen3_continuous_rx_integrity_v17';YOSYS=R/'hw/soc/tools/oss-cad-suite/bin/yosys';LIB=Path('/home/hasanmelih/.ciel/ciel/ihp-sg13g2/versions/c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c/ihp-sg13g2/libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_typ_1p20V_25C.lib')
def pin(p):
 with p.open('rb') as f:return {'bytes':p.stat().st_size,'sha256':hashlib.file_digest(f,'sha256').hexdigest()}
d=json.loads((OLD/'mapped.json').read_text());m=d['modules'][TOP];changes=[]
for name,net in m['netnames'].items():
 if net.get('signed'):
  changes.append(name);net['signed']=0
census=json.loads((R/'hw/soc/out/pcie-integrity-v17-20261005/signed-wire-census.json').read_text())
assert pin(OLD/'mapped.json')==census['source']
assert sorted(changes)==sorted(census['signed'])
for name,bits in census['signed'].items():assert m['netnames'][name]['bits']==bits
assert all(c['type'].startswith('sg13g2_') for c in m['cells'].values())
assert not any(row.get('signed') for row in m['ports'].values())
# JSON describes native primitive pin-bit connectivity, independent of wire signedness.
before=json.loads((OLD/'mapped.json').read_text());assert before['modules'][TOP]['cells']==m['cells'] and before['modules'][TOP]['ports']==m['ports']
for name in changes:before['modules'][TOP]['netnames'][name]['signed']=0
assert before==d
(OUT/'unsigned-wire-metadata.json').write_text(json.dumps(d,separators=(',',':'))+'\n')
ys=OUT/'map.ys';ys.write_text(f'read_json {OUT}/unsigned-wire-metadata.json\nhierarchy -check -top {TOP}\nhilomap -singleton -hicell sg13g2_tiehi L_HI -locell sg13g2_tielo L_LO\ncheck -assert\nwrite_verilog -noattr -noexpr {OUT}/mapped.v\nwrite_json {OUT}/mapped.json\n')
files=[Path(__file__),R/'hw/soc/out/pcie-integrity-v17-20261005/signed-wire-census.json',OLD/'mapped.json',OLD/'mapped.v',OUT/'unsigned-wire-metadata.json',ys,YOSYS,LIB]
assert os.sched_getaffinity(0)=={6},'Launch taskset -c 6'
r={'controller_allowed_cpus':sorted(os.sched_getaffinity(0)),'native_cpu_limit':1,'status':'RUNNING','inputs':{str(p):pin(p) for p in files},'changed_wire_metadata_only':changes,'exact_native_cells_and_ports_before_ties':True,'command':[str(YOSYS),'-Q','-T','-s',str(ys)],'scope':'Same mapped native primitive bit graph; exact recorded wire-label signed metadata removed for OpenSTA, no ports/cells/operations changed. Full inverse JSON equality checked before actual literal ties, no resynthesis. Exhaustive native pin-driver graph proof follows.'}
def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
def limit():
 resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,2*1024**3));resource.setrlimit(resource.RLIMIT_CORE,(0,0));os.sched_setaffinity(0,{6});signal.pthread_sigmask(signal.SIG_UNBLOCK,{signal.SIGINT,signal.SIGTERM})
save()
try:
 with (OUT/'native.log').open('x') as log:
  p=None
  try:
   oldmask=signal.pthread_sigmask(signal.SIG_BLOCK,{signal.SIGINT,signal.SIGTERM})
   try:p=subprocess.Popen(r['command'],stdout=log,stderr=subprocess.STDOUT,start_new_session=True,preexec_fn=limit,env={**os.environ,'YOSYS_MAX_THREADS':'1'})
   finally:signal.pthread_sigmask(signal.SIG_SETMASK,oldmask)
   r['native_allowed_cpus']=sorted(os.sched_getaffinity(p.pid));assert r['native_allowed_cpus']==[6]
   while p.poll() is None:
    if shutil.disk_usage('/dev/shm').free<528*1024**2:raise RuntimeError('Shared scratch floor breached')
    time.sleep(.2)
   r['returncode']=p.wait()
  except BaseException:
   if p is not None:
    try:os.killpg(p.pid,signal.SIGKILL)
    except ProcessLookupError:pass
    p.wait()
   raise
 assert r['returncode']==0
 new=json.loads((OUT/'mapped.json').read_text())['modules'][TOP];ties={n:c['type'] for n,c in new['cells'].items() if c['type'].startswith('sg13g2_tie')};assert set(ties.values())=={'sg13g2_tiehi','sg13g2_tielo'}
 assert len(new['cells'])==len(m['cells'])+2 and 'wire signed' not in (OUT/'mapped.v').read_text()
 assert r['inputs']=={str(p):pin(p) for p in files};r.update(status='PASS_GRAPH_METADATA_AND_LITERAL_TIE_IMPORT',ties=ties,mapped_cells=len(new['cells']))
except BaseException as e:r.update(status='FAILED_RETAINED',error=repr(e));raise
finally:
 r['outputs']={p.name:pin(p) for p in OUT.iterdir() if p.is_file() and p.name!='result.json'};save()
