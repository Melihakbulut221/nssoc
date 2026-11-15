import os,json,subprocess,hashlib,re
from pathlib import Path
assert os.environ.get('GITHUB_ACTIONS')=='true'
out=Path('out-ack-prefix');out.mkdir()
src=Path('hw/soc/rtl/pcie/soc_pcie_replay_tx.v')
s=src.read_text()
segment=s.split('// BEGIN ACK_STALE_PREFIX',1)[1].split('// END ACK_STALE_PREFIX',1)[0]
assert 'ack_was_stale<=ack_stale_now;'in s
assert "wire [11:0] ack_delta=ack_sequence_i-acknowledged_sequence_o;"in s
assert "wire ack_stale_now=ack_delta>12'd2048;"in s
header="module proof(input [11:0] ack_sequence_i,acknowledged_sequence_o, output ok);\nwire [11:0] ack_delta=ack_sequence_i-acknowledged_sequence_o;\n"
tail="\nassign ok=(ack_stale_prefix==(ack_delta>12'd2048));\nendmodule\n"
results=[]
try:
 for name,body,valid in [('exact',segment,True),('mutant_half_distance',segment.replace(' && ack_low_different',''),False),('mutant_borrow',segment.replace(' ^ ack_borrow10',''),False)]:
  assert valid or body!=segment
  v=out/(name+'.v');v.write_text(header+body+tail)
  ys=out/(name+'.ys');ys.write_text('read_verilog '+str(v)+'\nprep -top proof\nflatten\nsat -verify -prove ok 1 -show-inputs\n')
  p=subprocess.run(['yosys','-s',str(ys)],capture_output=True,text=True,timeout=120)
  text=p.stdout+p.stderr;(out/(name+'.log')).write_text(text)
  if valid: assert p.returncode==0 and 'SUCCESS!'in text,text[-3000:]
  else: assert p.returncode!=0 and 'proof did fail'in text,text[-3000:]
  results.append(dict(case=name,expected_equivalent=valid,returncode=p.returncode,status='PASS'if valid else 'REJECTED_EXPECTED_MUTANT'))
 for defines in [[],['-DSOC_PCIE_ACK_STALE_PREFIX']]:
  name='candidate'if defines else 'reference'
  p=subprocess.run(['iverilog','-g2012',*defines,'-s','soc_pcie_replay_tx','-o',str(out/(name+'.vvp')),*map(str,sorted(Path('hw/soc/rtl/pcie').glob('*.v')))],capture_output=True,text=True,timeout=120)
  (out/(name+'-compile.log')).write_text(p.stdout+p.stderr)
  assert p.returncode==0,p.stderr
 result=dict(status='PASS_COMBINATIONAL_24BIT_EQUIVALENCE_AND_TWO_MUTANTS',source_head=os.environ['GITHUB_SHA'],rtl_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),cases=results,accepted=False,scope='All 2^24 binary sequence pairs; exact combinational substitution at unchanged capture edge. Both actual RTL modes compile. Not full-module sequential traffic, four-state equivalence, mapped timing, route, or full PHY acceptance.',yosys=subprocess.check_output(['yosys','-V'],text=True).strip())
except BaseException as e:
 result=dict(status='FAIL',error=repr(e),cases=results,accepted=False);raise
finally:
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
