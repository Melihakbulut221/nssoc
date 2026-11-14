# SPDX-License-Identifier: Apache-2.0
"""Mutual CRC retiming proof; purge unused wires, retain all live equivalence points.
No RTL changes, assumptions, output masks, or waived equivalence cells.
"""
import pathlib,subprocess,sys,json,hashlib,time,re
BASE='4726df32f2833d1c0ac2d6096ce0160ff7c07995'
DIGEST='f2f31fc16eb3fd6fca3712786cc8518dad4262d1a224c7e8eccbd446d8f10772'
capacity=int(sys.argv[1]);direction=sys.argv[2]
assert capacity in (8,32) and direction in ('forward','reverse')
p=pathlib.Path('hw/soc/rtl/pcie/soc_pcie_lcrc_tx.v');out=pathlib.Path('out');out.mkdir()
subprocess.run(['git','fetch','--depth=1','origin',BASE],check=True)
gold=subprocess.check_output(['git','show',BASE+':'+str(p)]);assert hashlib.sha256(gold).hexdigest()==DIGEST
candidate=p.read_bytes();(out/'gold.v').write_bytes(gold);(out/'gate.v').write_bytes(candidate)
top='soc_pcie_lcrc_tx'
def design(name):
 return f'read_verilog -defer -sv -D SYNTHESIS out/{name}.v; hierarchy -check -top {top} -chparam MAX_TLP_DWORDS {capacity}; proc; flatten; opt -keepdc; memory_map; opt -keepdc; async2sync; opt -keepdc; opt_clean -purge; rename {top} {name}; design -stash {name};'
pair='gold gate' if direction=='forward' else 'gate gold'
ys=design('gold')+design('gate')+f'design -copy-from gold -as gold gold; design -copy-from gate -as gate gate; equiv_make {pair} equiv; hierarchy -top equiv; equiv_simple -undef -seq 2; equiv_status; opt_clean; equiv_induct -undef -seq 8; equiv_status -assert;'
(out/'proof.ys').write_text('\n'.join(x.strip() for x in ys.split(';') if x.strip())+'\n')
start=time.monotonic()
with (out/'proof.log').open('w') as log:
 try:rc=subprocess.run(['yosys','-s',str(out/'proof.ys')],stdout=log,stderr=subprocess.STDOUT,timeout=1800).returncode
 except subprocess.TimeoutExpired:rc=124
text=(out/'proof.log').read_text();counts=re.findall(r'Of those cells (\d+) are proven and (\d+) are unproven',text)
passed=rc==0 and 'Equivalence successfully proven!' in text and counts and int(counts[-1][0])>0 and int(counts[-1][1])==0 and candidate==p.read_bytes()
r={'passed':bool(passed),'base':BASE,'gold_sha256':DIGEST,'candidate_sha256':hashlib.sha256(candidate).hexdigest(),'capacity':capacity,'direction':direction,'returncode':rc,'counts':counts,'seconds':time.monotonic()-start,'scope':'Sequential RTL equivalence under Yosys async2sync/undef semantics; no added input assumptions or valid masking. Requires both directions, simulation, and fresh physical validation.','production_accepted':False}
(out/'result.json').write_text(json.dumps(r,indent=2));print(json.dumps(r));sys.exit(0 if passed else 1)
