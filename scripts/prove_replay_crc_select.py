"""Actual full-module CRC select equivalence and semantic mutation rejection."""
import pathlib,subprocess,json,hashlib,os
assert os.environ.get('GITHUB_ACTIONS')=='true'
out=pathlib.Path('out');out.mkdir(exist_ok=True)
rtl=pathlib.Path('hw/soc/rtl/pcie/soc_pcie_replay_tx.v');source=rtl.read_text()
needle='assign next_crc=in_sop_i ? replay_crc_start : replay_crc_continue;'
assert source.count(needle)==1
mutation=out/'mutated.v';mutation.write_text(source.replace(needle,"assign next_crc=(in_sop_i ? replay_crc_start : replay_crc_continue) ^ 32'h1;"))
result={'rtl_sha256':hashlib.sha256(source.encode()).hexdigest(),'accepted':False,'scope':'Full actual replay state/output formal equivalence; memories mapped, no blackboxes. CRC restructure only. Not physical or PHY signoff.','cases':[]}
for mode in ['default','physical']:
 for depth,size in [(2,22),(4,38)]:
  for fault in [False,True]:
   tag=f'{mode}-d{depth}-b{size}-'+('mutant' if fault else 'positive')
   common='' if mode=='default' else '-D SOC_PCIE_REPLAY_EOP_CACHE -D SOC_PCIE_REPLAY_WRITE_PREDECODE -D SOC_PCIE_REPLAY_AHEAD -D SOC_PCIE_REPLAY_INBANK -D SOC_PCIE_RESET_COPIES'
   commands=[]
   for name,flags,path in [('gold','',rtl),('gate','-D SOC_PCIE_REPLAY_CRC_SELECT',mutation if fault else rtl)]:
    commands += [f'read_verilog -sv {common} {flags} hw/soc/rtl/pcie/soc_pcie_crc32_byte.v {path}',f'chparam -set DEPTH {depth} -set MAX_BYTES {size} soc_pcie_replay_tx','prep -top soc_pcie_replay_tx -flatten','memory_map','opt','async2sync','opt',f'rename soc_pcie_replay_tx {name}',f'design -stash {name}']
   commands += ['design -copy-from gold -as gold gold','design -copy-from gate -as gate gate','equiv_make gold gate equiv','hierarchy -top equiv','equiv_simple','equiv_induct -seq 4','equiv_status -assert']
   script=out/(tag+'.ys');script.write_text(';\n'.join(commands)+'\n');log=out/(tag+'.log')
   with log.open('w')as stream:r=subprocess.run(['yosys','-Q','-T','-s',str(script)],stdout=stream,stderr=subprocess.STDOUT,timeout=1200)
   text=log.read_text();passed=r.returncode==0 and 'Equivalence successfully proven!'in text
   rejected=r.returncode!=0 and 'unproven $equiv'in text.lower() and 'syntax error'not in text.lower()
   row={'mode':mode,'depth':depth,'max_bytes':size,'mutation':fault,'returncode':r.returncode,'equivalence_proven':passed,'semantic_mutation_rejected':rejected,'log_sha256':hashlib.sha256(log.read_bytes()).hexdigest()}
   result['cases'].append(row);(out/'equivalence.json').write_text(json.dumps(result,indent=2))
   assert rejected if fault else passed,text[-6000:]
result['status']='FOUR_POSITIVE_PROOFS_AND_FOUR_SEMANTIC_MUTATIONS_COMPLETE_NOT_SIGNOFF';(out/'equivalence.json').write_text(json.dumps(result,indent=2))
