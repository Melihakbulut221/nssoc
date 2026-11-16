"""Compare unchanged SRAM functional models across simulators; no timing proof."""
import os,pathlib,json,hashlib,re,subprocess,itertools
ROOT=pathlib.Path.cwd();assert os.environ.get('GITHUB_ACTIONS')=='true'
OUT=ROOT/'cvc-sram-qualification';OUT.mkdir(exist_ok=False)
PDK=ROOT/'hw/soc/tools/ihp-native-boot-c4b8b4e'
lock=json.loads((ROOT/'hw/soc/pnr/ihp-native-boot.lock.json').read_text())
sha=lambda p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
pins={str(PDK/x['path']):x['sha256']for x in lock['files']if '/sg13g2_sram/verilog/'in x['path']}
models=list(pins);assert len(models)==5 and all(sha(p)==s for p,s in pins.items())
records=[];result=dict(source_head=os.environ['GITHUB_SHA'],passed=False,models=pins,cases=records,
scope='Unchanged FUNCTIONAL SRAM models; all addresses, four-state control combinations, masked data and unknown addresses. Sequential ports only, no concurrent-write or timing/SDF proof.',native_timing_accepted=False)
def bench(name,w,aw,ports,mutant=False):
 wrapper=pathlib.Path(next(p for p in models if pathlib.Path(p).stem==name)).read_text().split(chr(96)+'ifdef FUNCTIONAL')[0]
 decl=re.findall(r'\b(input|output)\s*(\[[0-9]+:[0-9]+\])?\s*(\w+)\s*;',wrapper)
 assert len(decl)==17*len(ports)
 lines=[chr(96)+'timescale 1ns/1ps','module ram_probe;','integer k,n=0;']
 for direction,width,pin in decl:lines.append(('reg 'if direction=='input'else'wire ')+(width or'')+' '+pin+';')
 connections=['.'+pin+'('+('~A_DIN'if mutant and pin=='A_DIN'else pin)+')'for _,_,pin in decl]
 lines.append(name+' dut('+','.join(connections)+');')
 display=' '.join('%b'for _ in ports);outputs=','.join(p+'_DOUT'for p in ports)
 lines+=['task op;',f'input integer p; input en,men,wen,ren; input [{aw-1}:0] addr; input [{w-1}:0] din,bm;','begin']
 for idx,p in enumerate(ports):
  lines.append(('if'if idx==0 else'else if')+f'(p=={idx})begin')
  lines.append(f'{p}_BIST_EN=en; {p}_ADDR=addr; {p}_BIST_ADDR=addr; {p}_DIN=din; {p}_BIST_DIN=~din; {p}_BM=bm; {p}_BIST_BM=bm; {p}_MEN=men; {p}_BIST_MEN=men; {p}_WEN=wen; {p}_BIST_WEN=wen; {p}_REN=ren; {p}_BIST_REN=ren;')
  lines.append(f'#2; {p}_CLK=1; {p}_BIST_CLK=1; #2; $display("TRACE %0d {display}",n,{outputs}); n=n+1; {p}_CLK=0; {p}_BIST_CLK=0; #2; end')
 lines+=['end endtask','initial begin',' '.join(pin+'=0;'for direction,width,pin in decl if direction=='input'),'#2;']
 lines.append(f"op(0,0,1,0,1,0,0,{{{w}{{1'b1}}}});")
 pattern=f"{w}'h"+('a5'*(w//8))
 lines.append(f"for(k=0;k<{2**aw};k=k+1)op(0,0,1,1,1,k,{pattern}^k,{{{w}{{1'b1}}}});")
 for idx,p in enumerate(ports):
  lines.append(f"for(k=0;k<{2**aw};k=k+1)begin op({idx},0,1,0,1,k,0,0);")
  if not mutant:lines.append(f'if({p}_DOUT!==({pattern}^k))$fatal(1,"ADDRESS_SWEEP_MISMATCH");')
  lines.append('end')
 values=["1'b0","1'b1","1'bx","1'bz"];count=1+2**aw*(1+len(ports))
 for idx,p in enumerate(ports):
  for i,control in enumerate(itertools.product(values,repeat=4)):
   data=[pattern,f"{w}'h0",f"{{{w}{{1'bx}}}}",f"{{{w}{{1'bz}}}}"][i%4]
   bm=[f"{{{w}{{1'b1}}}}",f"{w}'h0",pattern,f"{{{w}{{1'bx}}}}"][i//4%4]
   lines.append('op('+','.join([str(idx),*control,str(i%(2**aw)),data,bm])+');');count+=1
  for en in values:
   lines.append(f"op({idx},{en},1,1,1,{{{aw}{{1'bx}}}},{pattern},{pattern});");count+=1
 lines+=['$display("SRAM_TRACE_COMPLETE");$finish;end endmodule']
 return '\n'.join(lines)+'\n',count
def run(cmd,folder,leaf):
 with(folder/leaf).open('w')as log:p=subprocess.run(cmd,cwd=folder,stdout=log,stderr=subprocess.STDOUT,timeout=300)
 return dict(command=cmd,returncode=p.returncode,log_sha256=sha(folder/leaf))
def execute(name,engine,text,count):
 folder=OUT/(name+'-'+engine);folder.mkdir();src=folder/'bench.v';src.write_text(text);exe=folder/'sim'
 if engine.startswith('cvc'):cmd=[str(ROOT/'cvc-source/build64/cvc64'),'-sv','+nospecify','+define+FUNCTIONAL','-o',str(exe),str(src)]+sum([['-v',p]for p in models],[])
 else:cmd=['iverilog','-g2005-sv','-DFUNCTIONAL','-s','ram_probe','-o',str(exe),str(src)]+models
 r=dict(bench_sha256=sha(src));r['compile']=run(cmd,folder,'compile.log');assert r['compile']['returncode']==0
 r['run']=run([str(exe)]if engine.startswith('cvc')else['vvp','-i',str(exe)],folder,'run.log')
 log=(folder/'run.log').read_text();assert r['run']['returncode']==0 and 'SRAM_TRACE_COMPLETE'in log
 trace=[l for l in log.splitlines()if l.startswith('TRACE ')];assert len(trace)==count
 assert [int(l.split()[1])for l in trace]==list(range(count))
 r.update(trace_rows=count,trace_sha256=hashlib.sha256(('\n'.join(trace)+'\n').encode()).hexdigest())
 return r,trace
try:
 for name,w,aw,ports in [('RM_IHPSG13_1P_2048x64_c2_bm_bist',64,11,['A']),('RM_IHPSG13_2P_256x16_c2_bm_bist',16,8,['A','B'])]:
  row=dict(module=name);records.append(row);text,count=bench(name,w,aw,ports)
  row['icarus'],gold=execute(name,'icarus',text,count);row['cvc'],actual=execute(name,'cvc',text,count)
  diff=[dict(row=i,reference=x,observed=y)for i,(x,y)in enumerate(zip(gold,actual))if x!=y];row['mismatches']=len(diff)
  if diff:(OUT/(name+'-mismatches.json')).write_text(json.dumps(diff[:100],indent=2))
  assert not diff,(name,diff[:3])
  text,count=bench(name,w,aw,ports,True);row['mutation'],bad=execute(name,'cvc-mutant',text,count)
  row['mutation_mismatches']=sum(x!=y for x,y in zip(gold,bad));assert row['mutation_mismatches']>0
 result.update(passed=True,status='PASS_ORIGINAL_SRAM_FUNCTIONAL_DIRECTED_TRACES_AND_MUTATIONS')
except BaseException as e:result['error']=repr(e);raise
finally:
 result['sources_unchanged']=all(sha(p)==s for p,s in pins.items());result['passed']=result['passed'] and result['sources_unchanged']
 (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
