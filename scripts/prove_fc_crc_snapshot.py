import os,subprocess,json,hashlib,re
from pathlib import Path
assert os.environ.get('GITHUB_ACTIONS')=='true'
out=Path('fc-crc-formal');out.mkdir()
candidate=Path('hw/soc/rtl/pcie/soc_pcie_fc_tx.v');reference=Path('tests/fc_crc_snapshot/reference.v');crc=Path('hw/soc/rtl/pcie/soc_pcie_crc16_byte.v')
fields=dict(crc=16,index=3,active=1,header=8,data_credit=12,frame_phase=2,frame_class=2,phase=2,class_index=2)
extra={f'payload_crc{i}':16 for i in range(4)}
def observed(src,extra_fields,dest):
 fs=dict(fields,**extra_fields)
 needle='    input wire tx_ready_i\n);'
 assert src.count(needle)==1
 ports=',\n'.join('    output wire ['+str(w-1)+':0] obs_'+n for n,w in fs.items())
 text=src.replace(needle,'    input wire tx_ready_i,\n'+ports+'\n);')
 assert text.count('endmodule')==1
 text=text.replace('endmodule','\n'.join('assign obs_'+n+'='+n+';' for n in fs)+'\nendmodule')
 dest.write_text(text);return fs
gold=out/'reference.v';gate=out/'candidate.v'
gf=observed(reference.read_text(),{},gold);df=observed(candidate.read_text(),extra,gate)
text=Path('tests/fc_crc_snapshot/miter-template.v').read_text()
decl=[]
for prefix,fs in [('d',df),('r',gf)]:
 for n,w in fs.items():decl.append('wire ['+str(w-1)+':0] '+prefix+'_'+n+';')
text=text.replace('wire [77:0] a,b;','wire [77:0] a,b;\n'+'\n'.join(decl))
# Connect read-only formal observation outputs; functional ports and state logic unchanged.
for bus,prefix,fs in [('a','d',df),('b','r',gf)]:
 needle='.tx_valid_o('+bus+'[0]),.tx_ready_i(ready));'
 assert text.count(needle)==1
 text=text.replace(needle,'.tx_valid_o('+bus+'[0]),.tx_ready_i(ready),'+','.join('.obs_'+n+'('+prefix+'_'+n+')'for n in fs)+');')
text=text.replace('ref_dut.','r_').replace('dut.','d_')
miter=out/'miter.v';miter.write_text(text)
r=dict(source_head=os.environ['GITHUB_SHA'],passed=False,full_phy_accepted=False,final_timing_complete=False,cases=[],scope='Direct sequential miter with active-frame data-CRC invariants, two-state sampled reset proof; not physical timing.',inputs={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in [candidate,reference,crc]},formal_copies={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in [gold,gate,miter]})
def save():(out/'result.json').write_text(json.dumps(r,indent=2))
def prove(label,refresh,source):
 ys=out/(label+'.ys');ys.write_text(f"""
read_verilog -formal {crc} {gold} {source} {miter}
chparam -set REFRESH {refresh} fc_miter
prep -top fc_miter -flatten
async2sync
memory_map
opt_clean
sat -seq 1 -tempinduct -maxsteps 12 -prove-asserts -set-at 1 rst 0 -set-def-inputs -verify -timeout 600
""")
 with(out/(label+'.log')).open('w')as log:
  p=subprocess.run(['yosys','-s',str(ys)],stdout=log,stderr=subprocess.STDOUT,timeout=900)
 return p.returncode,(out/(label+'.log')).read_text()
try:
 for refresh in [8,128]:
  rc,log=prove('miter-'+str(refresh),refresh,gate)
  assert rc==0 and 'Induction step proven: SUCCESS!'in log,('Unproven direct miter',refresh)
  r['cases'].append(dict(refresh=refresh,proved=True));save()
 fault=out/'fault.v';s=gate.read_text();assert s.count('data_crc=c;')==1
 fault.write_text(s.replace('data_crc=c;',"data_crc=c^16'h0001;"))
 rc,log=prove('fault',128,fault)
 assert rc!=0 and 'proof did fail'in log,'Negative control not decisively rejected'
 r['fault_rejected']=True;r['passed']=True
finally:save()
