"""Read completed mapped bytes and execute pure graph checks; never Yosys."""
from pathlib import Path
import collections,hashlib,json,os,resource,sys
R=Path.cwd();B=Path(__file__).resolve().parent;D=B/'native01'
resource.setrlimit(resource.RLIMIT_AS,(3*1024**3,3*1024**3));assert os.sched_getaffinity(0)=={0}
sys.path.insert(0,str(R/'scripts'))
import run_cloud_alu_qualification as q
import check_npu_physical_eco_mapping as bridge

def pin(p):
 p=Path(p)
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
f=json.loads((B/'source-freeze01.json').read_text());controls=json.loads((B/'controls-freeze01.json').read_text());r=json.loads((D/'result.json').read_text())
assert r['status']=='PASS_MATCHED32SRAM_MAPPING_AND_EXACT_ECO_BRIDGE_BOOT_PHYSICAL_PENDING'and not r['full_soc_functional_accepted']and not r['timing_accepted']
assert r['source_freeze']==pin(B/'source-freeze01.json')
inputs={**f['inputs'],**controls['inputs']}
for p,v in inputs.items():assert pin(p)==v,p
lock=json.loads((R/q.LOCK).read_text());syn=q.alu.validate_lock(json.loads((R/q.alu.LOCK).read_text()));bundle=D/'inputs';snapshot=D/'snapshot';physical=json.loads((bundle/'physical-config.json').read_text())
restored=0
for root,files in[(bundle,lock['files']),(snapshot,syn['files'])]:
 for n,v in files.items():assert pin(root/n)=={k:v[k]for k in['bytes','sha256']};restored+=1
outputs={};recomputed={}
for name in['original','candidate','factored']:
 stage=r['stages'][name];out=D/name;assert stage['status']=='PASS_MAPPING_CONTRACT'and stage['returncode']==0
 for n,v in stage['outputs'].items():assert pin(out/n)==v;outputs[str(out/n)]=v
 assert stage['recipe']==pin(out/'map.ys')
 expected=q.mapping_recipe((bundle/'recipe/original-map.ys').read_text(),Path(f['netlists'][name]),out,bundle,snapshot,syn)
 assert expected==(out/'map.ys').read_text()
 log=(out/'native.log').read_text();assert 'Executing Verilog backend.'in log and 'ERROR:'not in log
 a=json.loads((out/'before.json').read_text())['modules']['soc_top'];b=json.loads((out/'after.json').read_text())['modules']['soc_top']
 recomputed[name]=q.mapping_contract(a,b,physical);assert recomputed[name]==stage['mapping_contract'];del a,b
 assert stage['netlist']==pin(out/'soc_top.netlist.v')
 if name!='factored':assert stage['netlist']['sha256']==f['expected_mapping'][name]
a=json.loads((D/'candidate/after.json').read_text())['modules']['soc_top'];b=json.loads((D/'factored/after.json').read_text())['modules']['soc_top'];positive=bridge.check(a,b);assert positive==r['exact_combinational_bridge']
assert len(b['cells'])==len(a['cells'])+2 and len(b['ports'])==79
assert collections.Counter(c['type']for c in b['cells'].values()if c['type']in['SP6TSRAM512x64','DP8TSRAMDP256x16'])=={'SP6TSRAM512x64':16,'DP8TSRAMDP256x16':16}
mutants=[]
mem=next(n for n,c in b['cells'].items()if c['type']=='SP6TSRAM512x64');mp=next(p for p,bits in b['cells'][mem]['connections'].items()if bits and isinstance(bits[0],int))
for label,name,port in[('real_mux_select','_103492_','S'),('real_inverter_input','nssoc_npu_init_invert','A'),('real_SRAM_pin',mem,mp)]:
 cell=b['cells'][name];old=cell['connections'][port];replacement=['1'if old[0]!='1'else'0']+old[1:];cell['connections'][port]=replacement
 try:bridge.check(a,b)
 except ValueError as e:mutants.append(dict(label=label,cell=name,port=port,before=old,after=replacement,rejected=True,diagnostic=str(e)))
 else:raise AssertionError('Actual graph corruption accepted')
 finally:cell['connections'][port]=old
assert len(mutants)==3 and bridge.check(a,b)==positive
for p,v in {**inputs,**outputs}.items():assert pin(p)==v,p
record=dict(status='PASS_SAVED_MATCHED_NPU_MAPPING_GRAPH_AND_THREE_ACTUAL_GRAPH_MUTANTS',findings=[],method=pin(Path(__file__)),native_result=pin(D/'result.json'),source_freeze=pin(B/'source-freeze01.json'),controls_freeze=pin(B/'controls-freeze01.json'),input_pins_rehashed=len(inputs),restored_files_rehashed=restored,output_pins_rehashed=outputs,recomputed_mapping_contracts=recomputed,recomputed_exact_bridge=positive,actual_graph_controls=mutants,full_soc_functional_accepted=False,timing_accepted=False,scope='All three completed native outputs/logs/recipes rehashed; exact frozen mapping_recipe and mapping_contract rerun as pure Python on savedgraph, no Yosys/synthesis/boot/physical run. Original13dd andcandidateef20 hashes reproduced; factoredactualdcf832 bound. Frozen graph checker recomputed exact76714retainedcell equations/79ports/32SRAM withthree realinmemory mutations rejected; sourcefiles/outputgraphs unchanged. This verifies finite SRAM-mapping stage, not NPU boot or chip timing adoption.')
(B/'saved-native-peer-pll.json').write_text(json.dumps(record,indent=2)+'\n');print(record['status'],pin(B/'saved-native-peer-pll.json'))
