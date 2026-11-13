# SPDX-License-Identifier: Apache-2.0
"""Scoped old-layout-source vs current SRAM boolean-condition equivalence."""
import hashlib,json,pathlib,re,subprocess,time
BASE='ecef9ad7cc9cd38c40b37b2109c2c976c53d1e4b'
out=pathlib.Path('out');out.mkdir(exist_ok=True)
subprocess.run(['git','fetch','--depth=1','origin',BASE],check=True)
version=subprocess.check_output(['yosys','-V'],text=True).strip()
profiles=[
 ('mbist_default','soc_sram_mbist',{},[]),
 ('mbist_eth_unregistered','soc_sram_mbist',{'WIDTH':16,'DEPTH':2048,'ADDR_WIDTH':11,'READ_LATENCY':1,'PIPELINE_COMPARE':1},[]),
 ('mbist_eth_registered','soc_sram_mbist',{'WIDTH':16,'DEPTH':2048,'ADDR_WIDTH':11,'READ_LATENCY':2,'PIPELINE_COMPARE':1},['SOC_SRAM_MBIST_PIPE']),
 ('mbist_system_screen','soc_sram_mbist',{'WIDTH':64,'DEPTH':1024,'ADDR_WIDTH':10,'READ_LATENCY':3,'PIPELINE_COMPARE':1},['SOC_SRAM_MBIST_PIPE']),
 ('mbist_nonbinary_parameter','soc_sram_mbist',{'PIPELINE_COMPARE':2},['SOC_SRAM_MBIST_PIPE']),
 ('zero_default','soc_sram_zero_check',{},[]),
 ('zero_eth_unregistered','soc_sram_zero_check',{'PIPELINE_COMPARE':1},[]),
 ('zero_eth_registered','soc_sram_zero_check',{'PIPELINE_COMPARE':1,'READ_LATENCY':2},['SOC_ETH_FIFO_RDREG']),
 ('zero_nonbinary_parameter','soc_sram_zero_check',{'PIPELINE_COMPARE':-1},[])]
sources={}
for top in ['soc_sram_mbist','soc_sram_zero_check']:
 path='hw/soc/rtl/dft/'+top+'.v';old=subprocess.check_output(['git','show',BASE+':'+path]);new=pathlib.Path(path).read_bytes()
 a=out/(top+'_old.v');b=out/(top+'_new.v');a.write_bytes(old);b.write_bytes(new)
 sources[top]={'old_sha256':hashlib.sha256(old).hexdigest(),'new_sha256':hashlib.sha256(new).hexdigest()}
 def mutate(m):return 'assign req_o = ~('+m[1]+');'
 bad,n=re.subn(r'assign req_o = ([^;]+);',mutate,new.decode());assert n==1
 (out/(top+'_bad.v')).write_text(bad)
def design(path,top,name,params,defines):
 flags=' -D SYNTHESIS '+' '.join('-D '+d for d in defines)
 param=' '.join('-set '+k+' '+str(v) for k,v in params.items())
 lines=[f'read_verilog -sv {flags} {path}']
 if param:lines.append(f'chparam {param} {top}')
 lines += [f'hierarchy -check -top {top}','proc','opt -keepdc','async2sync','opt -keepdc',f'rename {top} {name}',f'design -stash {name}']
 return lines
rows=[]
for label,top,params,defines in profiles:
 for direction in ['forward','reverse']:
  faults=[False,True] if label in ['mbist_default','zero_default'] else [False]
  for fault in faults:
   tag=label+'_'+direction+('_fault' if fault else '')
   lines=design(out/(top+'_old.v'),top,'gold',params,defines)+design(out/(top+('_bad.v' if fault else '_new.v')),top,'gate',params,defines)
   pair='gold gate' if direction=='forward' else 'gate gold'
   lines += ['design -copy-from gold -as gold gold','design -copy-from gate -as gate gate',f'equiv_make {pair} equiv','hierarchy -top equiv','equiv_simple -undef','equiv_induct -undef -seq 4','equiv_status -assert']
   p=out/(tag+'.ys');p.write_text('\n'.join(lines)+'\n');began=time.monotonic()
   with (out/(tag+'.log')).open('w') as f:
    try:rc=subprocess.run(['yosys','-s',str(p)],stdout=f,stderr=subprocess.STDOUT,timeout=120).returncode
    except subprocess.TimeoutExpired:rc=124
   log=(out/(tag+'.log')).read_text();passed=rc==0 and 'Equivalence successfully proven!' in log
   rejected=rc!=0 and bool(re.search(r'ERROR: Found \d+ unproven \$equiv cells',log))
   ok=rejected if fault else passed
   rows.append(dict(profile=label,module=top,parameters=params,defines=defines,direction=direction,fault=fault,returncode=rc,passed=passed,expected_fault_rejected=rejected if fault else None,check_ok=ok,seconds=time.monotonic()-began));print(json.dumps(rows[-1]),flush=True)
result=dict(base=BASE,head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),yosys=version,sources=sources,results=rows,passed=len(rows)==22 and all(x['check_ok'] for x in rows),scope='Nine declared parameter/define profiles, mutual Yosys sequential equivalence under async2sync and explicit undef semantics, plus four inverted-request negative controls. No full-chip equivalence, four-state event simulation, all-parameter proof, SRAM analog qualification, physical timing or LVS approval.')
(out/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps({'passed':result['passed'],'checks':len(rows)}));raise SystemExit(0 if result['passed'] else 1)
