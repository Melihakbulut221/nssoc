import os,subprocess,json,hashlib
from pathlib import Path
assert os.environ.get('GITHUB_ACTIONS')=='true'
out=Path('fc-crc-snapshot-results');out.mkdir()
root=Path('hw/soc/rtl/pcie')
reference=Path('tests/fc_crc_snapshot/reference.v')
candidate=root/'soc_pcie_fc_tx.v'
crc=root/'soc_pcie_crc16_byte.v'
tb=Path('tests/fc_crc_snapshot/tb.v')
r=dict(source_head=os.environ['GITHUB_SHA'],passed=False,full_phy_accepted=False,final_timing_complete=False,cases=[],source_hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in [reference,candidate,crc,tb]})
def save():(out/'result.json').write_text(json.dumps(r,indent=2))
try:
 for refresh in [8,128]:
  exe=out/('sim-'+str(refresh))
  subprocess.run(['iverilog','-g2012','-s','tb','-Ptb.REFRESH='+str(refresh),'-o',str(exe),str(tb),str(reference),str(candidate),str(crc)],check=True)
  for seed in [17,12345,987654]:
   p=subprocess.run(['vvp',str(exe),'+SEED='+str(seed)],capture_output=True,text=True,timeout=180)
   (out/('r'+str(refresh)+'s'+str(seed)+'.log')).write_text(p.stdout+p.stderr)
   assert p.returncode==0 and 'FC_CRC_SNAPSHOT_PASS'in p.stdout,(refresh,seed,p.stdout,p.stderr)
   r['cases'].append(dict(refresh=refresh,seed=seed,passed=True,tail=p.stdout[-500:]));save()
 fault=out/'fault.v';text=candidate.read_text();assert text.count('data_crc=c;')==1
 fault.write_text(text.replace('data_crc=c;','data_crc=c^16\'h0001;'))
 exe=out/'fault'
 subprocess.run(['iverilog','-g2012','-s','tb','-o',str(exe),str(tb),str(reference),str(fault),str(crc)],check=True)
 p=subprocess.run(['vvp',str(exe),'+SEED=17'],capture_output=True,text=True,timeout=180)
 (out/'fault.log').write_text(p.stdout+p.stderr)
 assert p.returncode!=0 and ('FC_DIFFERENTIAL_MISMATCH'in p.stdout or 'FC_CRC_CONTRIBUTION_MISMATCH'in p.stdout)
 r['fault_rejected']=True;r['passed']=True
finally:save()
