import os,json,subprocess,hashlib,re,shutil
from pathlib import Path
assert os.environ.get('GITHUB_ACTIONS')=='true'
root=Path.cwd();out=root/'peer-ready-qualification';out.mkdir()
src=root/'hw/soc/rtl/pcie/soc_pcie_credit_tx.v'
ref=root/'sw/tests/fixtures/pcie_credit_tx/pre-peer-ready.v'
bench=root/'hw/soc/tb/tb_pcie_credit_pick.v'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
original=ref.read_text();candidate=src.read_text()
r=dict(source_head=os.environ['GITHUB_SHA'],passed=False,full_phy_accepted=False,final_timing_complete=False,inputs={str(p.relative_to(root)):sha(p)for p in [src,ref,bench,Path(__file__)]},cases=[])
def save():(out/'result.json').write_text(json.dumps(r,indent=2))
def run(cmd,folder,name,timeout=900):
 with (folder/name).open('w')as log:p=subprocess.run(cmd,cwd=folder,stdout=log,stderr=subprocess.STDOUT,timeout=timeout)
 return p.returncode,(folder/name).read_text()
def wrapped(text,name,defs):
 text=text.replace('soc_pcie_credit_pick',name+'_pick').replace('module soc_pcie_credit_tx (','module '+name+' (')
 return ''.join('`define '+d+'\n'for d in defs)+text+''.join('\n`undef '+d+'\n'for d in defs)
try:
 assert sha(ref)==os.environ['REFERENCE_SHA']
 r['tools']={t:sha(Path(shutil.which(t)))for t in ['yosys','iverilog','vvp']}
 for idx,defs in enumerate([[],['SOC_PCIE_CREDIT_PICK'],['SOC_PCIE_CREDIT_DATA_SIGN_REG'],['SOC_PCIE_CREDIT_PICK','SOC_PCIE_CREDIT_DATA_SIGN_REG']]):
  folder=out/str(idx);folder.mkdir()
  (folder/'gold.v').write_text(wrapped(original,'gold',defs))
  (folder/'gate.v').write_text(wrapped(candidate,'gate',defs))
  recipe='\n'.join(['read_verilog -sv -DSYNTHESIS gold.v gate.v','proc','setattr -mod -unset keep_hierarchy','flatten gold gate','memory_map','opt','clk2fflogic','opt','equiv_make gold gate equiv','hierarchy -top equiv','equiv_simple','equiv_induct -seq 4','equiv_simple','equiv_induct -seq 8','equiv_status','equiv_status -assert',''])
  (folder/'proof.ys').write_text(recipe)
  rc,log=run(['yosys','-s','proof.ys'],folder,'proof.log')
  counts=re.findall(r'Of those cells (\d+) are proven and (\d+) are unproven',log)
  assert 'No SAT model available' not in log, 'Incomplete flattened formal model'
  formal=rc==0 and bool(counts) and all(int(a)>0 and int(b)==0 for a,b in counts) and 'Equivalence successfully proven!'in log
  case=dict(defines=defs,formal_returncode=rc,formal_passed=formal,counts=counts,seeds=[])
  r['cases'].append(case);save()
  # Collect all traffic evidence even when formal proof is inconclusive.
  # Final acceptance still requires every formal and traffic check.
  (folder/'reference.v').write_text(wrapped(original,'soc_pcie_credit_tx_ref',defs))
  (folder/'candidate.v').write_text(wrapped(candidate,'soc_pcie_credit_tx',defs))
  rc,log=run(['iverilog','-g2012','-s','tb_pcie_credit_pick','-o','sim','reference.v','candidate.v',str(bench)],folder,'compile.log')
  assert rc==0,log[-2000:]
  for seed in [1,2,3,4]:
   rc,log=run(['vvp','-n','sim','+seed='+str(seed),'+cycles=300000'],folder,'seed'+str(seed)+'.log')
   passed=rc==0 and re.search(r'^RESULT PASS$',log,re.M)and not re.search(r'^(MISMATCH|RESULT FAIL|FATAL)',log,re.M)
   case['seeds'].append(dict(seed=seed,returncode=rc,passed=bool(passed),summary=re.findall(r'^SUMMARY.*',log,re.M)));save()
   # Keep collecting all seeds; no failed check is waived.
 # Establish that the same proof recipe can prove the unchanged reference.
 folder=out/'self-reference';folder.mkdir()
 (folder/'gold.v').write_text(wrapped(original,'gold',[]))
 (folder/'gate.v').write_text(wrapped(original,'gate',[]))
 (folder/'proof.ys').write_text(recipe)
 rc,log=run(['yosys','-s','proof.ys'],folder,'proof.log')
 r['self_reference']=dict(returncode=rc,passed=rc==0 and 'Equivalence successfully proven!'in log);save()
 assert r['self_reference']['passed']
 # Output inversion must be rejected by the exact same formal checker.
 folder=out/'mutant';folder.mkdir()
 (folder/'gold.v').write_text(wrapped(original,'gold',[]))
 mutant=candidate.replace('&& peer_ready &&','&& !peer_ready &&');assert mutant!=candidate
 (folder/'gate.v').write_text(wrapped(mutant,'gate',[]))
 (folder/'proof.ys').write_text(recipe)
 rc,log=run(['yosys','-s','proof.ys'],folder,'proof.log')
 r['negative_control']=dict(returncode=rc,detected=rc!=0 and 'unproven' in log and 'Equivalence successfully proven!'not in log);save()
 assert r['negative_control']['detected']
 assert all(sha(root/p)==h for p,h in r['inputs'].items())
 assert all(c['formal_passed'] and len(c['seeds'])==4 and all(x['passed']for x in c['seeds'])for c in r['cases'])
 r.update(passed=True,sources_unchanged=True,status='PASS_PEER_READY_EQUIVALENCE_AND_TRAFFIC',scope='Credit module explicit clock/reset equivalence and four configurations x four seeds x300000cycles; no mapped timing or full PHY acceptance.')
finally:
 r['outputs']={str(p.relative_to(out)):sha(p)for p in out.rglob('*')if p.is_file()and p.suffix in ['.v','.ys','.log']};save()
