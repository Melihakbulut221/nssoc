import os,json,hashlib,subprocess
from pathlib import Path
assert os.environ.get('GITHUB_ACTIONS')=='true'
out=Path('ack-delta-proof');out.mkdir()
p=Path('hw/soc/rtl/pcie/soc_pcie_replay_tx.v');source=p.read_text()
body=source.split('// BEGIN ACK_DELTA_GROUP_PREFIX',1)[1].split('// END ACK_DELTA_GROUP_PREFIX',1)[0]
result=dict(source_head=os.environ['GITHUB_SHA'],rtl_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),accepted=False,final_timing_complete=False,full_phy_accepted=False,scope='Two-state combinational modular subtraction only; full replay traffic, four-state behavior, mapping and physical timing remain required.',cases=[])
try:
 for name,b in [('exact',body),('mutant_borrow',body.replace("assign ack_delta_borrow[1]=ack_delta_g[0];","assign ack_delta_borrow[1]=1'b0;"))]:
  assert name=='exact' or b!=body
  v=out/(name+'.v')
  v.write_text('module proof(input [11:0] ack_sequence_i,acknowledged_sequence_o,output ok);\n'+b+'\nassign ok=ack_delta==(ack_sequence_i-acknowledged_sequence_o);\nendmodule\n')
  cmd=['yosys','-p','read_verilog -sv '+str(v)+'; prep -top proof; flatten; sat -verify -prove ok 1 -show-inputs']
  p1=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
  (out/(name+'.log')).write_bytes(p1.stdout)
  text=p1.stdout.decode()
  if name=='exact':
   assert p1.returncode==0 and 'SUCCESS!' in text,text[-2000:]
  else:
   assert p1.returncode!=0 and 'proof did fail' in text,text[-2000:]
  result['cases'].append(dict(name=name,returncode=p1.returncode,status='PASS' if name=='exact' else 'REJECTED_EXPECTED_MUTANT'))
 result['status']='PASS_24BIT_ARITHMETIC_EQUIVALENCE_WITH_MUTATION_NOT_CHIP_ACCEPTANCE'
finally:
 (out/'result.json').write_text(json.dumps(result,indent=2))
