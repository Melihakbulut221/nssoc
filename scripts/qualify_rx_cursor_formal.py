"""Actual RX state/output proof under documented equal reset-copy contract."""
import pathlib,subprocess,json,hashlib,os,re
assert os.environ.get('GITHUB_ACTIONS')=='true'
out=pathlib.Path('out-formal');out.mkdir(exist_ok=True)
source=pathlib.Path('hw/soc/rtl/pcie/soc_pcie_rx_credit.v').read_text()
# Bind the existing port contract explicitly in BOTH full RTL modules.
# Link, ready, training, data and verdict inputs remain unconstrained.
assert source.count('    input wire rst_copy_ni,')==1
bound=source.replace('    input wire rst_copy_ni,','')
bound=re.sub(r'\brst_copy_ni\b','rst_ni',bound)
normal=out/'bound.v';normal.write_text(bound)
needle='wire r2_handshake=rst_ni && link_up_i && out_ready_i &&'
assert bound.count(needle)==1
mutant=out/'mutant.v';mutant.write_text(bound.replace(needle,'wire r2_handshake=rst_ni && link_up_i && !out_ready_i &&'))
common='-D SYNTHESIS -D SOC_PCIE_RX_READ2 -D SOC_PCIE_RESET_COPIES -D SOC_PCIE_RX_COMMIT_COPIES'
result={'source_sha256':hashlib.sha256(source.encode()).hexdigest(),'contract':'rst_copy_ni == rst_ni (existing parent contract); no other input assumptions','signoff':False,'cases':[]}
for dw,slots in [(4,1),(8,2)]:
 for fault in [False,True]:
  tag=f'dw{dw}-s{slots}-'+('mutant'if fault else'positive');commands=[]
  for name,flags,path in [('gold','',normal),('gate','-D SOC_PCIE_RX_CURSOR_LOCAL_RESET',mutant if fault else normal)]:
   commands += [f'read_verilog -sv {common} {flags} {path}',f'chparam -set MAX_TLP_DWORDS {dw} -set SLOTS_PER_CLASS {slots} soc_pcie_rx_credit','prep -top soc_pcie_rx_credit','setattr -mod -unset keep_hierarchy','setattr -unset keep_hierarchy','flatten','select -assert-none t:*soc_pcie*','memory_map','opt','async2sync','opt',f'rename soc_pcie_rx_credit {name}',f'design -stash {name}']
  commands += ['design -copy-from gold -as gold gold','design -copy-from gate -as gate gate','equiv_make gold gate equiv','hierarchy -top equiv','equiv_simple','equiv_induct -seq 4','equiv_status -assert']
  script=out/(tag+'.ys');script.write_text(';\n'.join(commands)+'\n');log=out/(tag+'.log')
  with log.open('w')as stream:r=subprocess.run(['yosys','-Q','-T','-s',str(script)],stdout=stream,stderr=subprocess.STDOUT,timeout=1500)
  text=log.read_text();passed=r.returncode==0 and 'Equivalence successfully proven!'in text
  rejected=r.returncode!=0 and 'unproven $equiv'in text.lower() and 'syntax error'not in text.lower()
  result['cases'].append({'dw':dw,'slots':slots,'mutation':fault,'returncode':r.returncode,'proven':passed,'mutation_rejected':rejected,'log_sha256':hashlib.sha256(log.read_bytes()).hexdigest()})
  (out/'result.json').write_text(json.dumps(result,indent=2))
  assert rejected if fault else passed,text[-6000:]
result['status']='TWO_FULL_MODULE_PROOFS_AND_TWO_MUTATIONS_COMPLETE_NOT_PHYSICAL_SIGNOFF'
(out/'result.json').write_text(json.dumps(result,indent=2))
