import os,json,subprocess,hashlib,shutil
from pathlib import Path
assert os.environ.get('GITHUB_ACTIONS')=='true'
root=Path.cwd();out=root/'peer-ready-invariant';out.mkdir()
source=root/'hw/soc/rtl/pcie/soc_pcie_credit_tx.v'
text=source.read_text()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(source)=='35b0b71994d793797c86f074f4d0d774789d64cf986049c5aec254b29121c530'
r=dict(source_head=os.environ['GITHUB_SHA'],rtl_sha256=sha(source),passed=False,full_equivalence_accepted=False,full_phy_accepted=False,final_timing_complete=False,cases=[])
def save():(out/'result.json').write_text(json.dumps(r,indent=2))
def run(cmd,folder,name):
 with (folder/name).open('w')as f:
  try:rc=subprocess.run(cmd,cwd=folder,stdout=f,stderr=subprocess.STDOUT,timeout=900).returncode
  except subprocess.TimeoutExpired:rc=124
 return rc,(folder/name).read_text()
try:
 rc,helptext=run(['yosys','-Q','-T','-p','help sat; help clk2fflogic'],out,'help.log');assert rc==0
 for option in ['-tempinduct','-maxsteps','-set-at','-prove','-verify','-dump_vcd']:
  assert option in helptext
 r['tool_sha256']=sha(Path(shutil.which('yosys')))
 defs=[[],['SOC_PCIE_CREDIT_PICK'],['SOC_PCIE_CREDIT_DATA_SIGN_REG'],['SOC_PCIE_CREDIT_PICK','SOC_PCIE_CREDIT_DATA_SIGN_REG']]
 for idx,ds in enumerate(defs):
  for mutant in [False,True]:
   folder=out/(str(idx)+('-reset-mutant'if mutant else ''));folder.mkdir()
   body=text.replace('module soc_pcie_credit_tx (','module proof (')
   old='output wire [5:0] infinite_o';assert body.count(old)==1
   body=body.replace(old,old+',\n    output wire proof_invariant_o')
   marker='    reg peer_ready;';assert body.count(marker)==1
   body=body.replace(marker,marker+'\n    assign proof_invariant_o=(peer_ready == ((&seen) && confirmed));')
   if mutant:
    assert body.count('peer_ready<=0;')==2
    body=body.replace('peer_ready<=0;','peer_ready<=1;')
   body=''.join('`define '+x+'\n'for x in ds)+body
   (folder/'input.v').write_text(body)
   pre=['read_verilog -sv -DSYNTHESIS input.v','hierarchy -check -top proof','proc','setattr -mod -unset keep_hierarchy','flatten','memory_map','opt','clk2fflogic','opt','check -assert']
   # Reset is asserted at the first sampled instant; later reset, clock,
   # link and event inputs are unconstrained. No state-matching cutpoints,
   # zero-initialization, skipped base cases or x-as-dont-care proof.
   base='sat -seq 2 -set-at 1 rst_ni 0 -prove proof_invariant_o 1 -verify -timeout 120 -show-ports -dump_vcd base-counterexample.vcd'
   induction='sat -seq 1 -tempinduct -maxsteps 12 -set-at 1 rst_ni 0 -prove proof_invariant_o 1 -verify -timeout 120 -show-ports -dump_vcd induction-counterexample.vcd'
   recipe='\n'.join(pre+[base]+([]if mutant else[induction])+[''])
   (folder/'proof.ys').write_text(recipe)
   rc,log=run(['yosys','-s','proof.ys'],folder,'proof.log')
   complete='No SAT model available'not in log and 'Failed to import cell'not in log
   passed=rc==0 and 'Induction step proven: SUCCESS!'in log and complete
   detected=mutant and rc!=0 and 'model found: FAIL!'in log and complete
   r['cases'].append(dict(defines=ds,mutant=mutant,returncode=rc,passed=passed,negative_control_detected=detected,complete_model=complete));save()
 assert len(r['cases'])==8 and all(c['negative_control_detected']if c['mutant']else c['passed']for c in r['cases'])
 assert sha(source)==r['rtl_sha256']
 r.update(passed=True,sources_unchanged=True,scope='Two-state symbolic peer-ready invariant with explicit sampled clock/reset and base plus induction; initial reset only. NOT full module equivalence, mapped timing, four-state simulation or full PHY acceptance.')
except BaseException as e:r['error']=repr(e);raise
finally:
 r['outputs']={str(p.relative_to(out)):sha(p)for p in out.rglob('*')if p.is_file()and p.name!='result.json'};save()
