"""Compare every affected cell across all four-state single-pin transitions.
Original Icarus vs derived Icarus vs derived CVC. Functional-only, no SDF.
"""
import pathlib,re,os,json,hashlib,subprocess,time
from ihp_zero_delay_aliases import adapt,SOURCE_SHA
assert os.environ.get('GITHUB_ACTIONS')=='true'
root=pathlib.Path.cwd();out=root/'cvc-cell-qualification';out.mkdir(exist_ok=False)
lib=root/'hw/soc/tools/ihp-native-boot-c4b8b4e/ihp-sg13g2/libs.ref/sg13g2_stdcell/verilog/sg13g2_stdcell.v'
sha=lambda p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
original=lib.read_text();derived,changed=adapt(original);model=out/'derived-zero-delay.v';model.write_text(derived)
cvc=root/'cvc-source/build64/cvc64';records=[]
r=dict(source_head=os.environ['GITHUB_SHA'],source_sha256=SOURCE_SHA,derived_sha256=sha(model),compiler_sha256=sha(cvc),scope='Exhaustive four-state single-input transitions over every other input combination, with sequentially settled initialization and context pin transitions; original and derived Icarus vs derived CVC. Not arbitrary simultaneous-edge formal proof, timing/SDF or whole-chip acceptance.',native_model_compatible=False,chip_accepted=False,cells=records)
def save():(out/'result.json').write_text(json.dumps(r,indent=2))
def run(command,folder,filename,timeout):
 start=time.monotonic()
 with(folder/filename).open('w')as log:p=subprocess.run(command,cwd=folder,stdout=log,stderr=subprocess.STDOUT,timeout=timeout)
 return dict(command=command,returncode=p.returncode,elapsed_s=time.monotonic()-start,log_sha256=sha(folder/filename))
def bench(name,body):
 inputs=[x.strip()for line in re.findall(r'\binput\s+([^;]+);',body)for x in line.split(',')]
 outputs=[x.strip()for line in re.findall(r'\boutput\s+([^;]+);',body)for x in line.split(',')]
 assert inputs and outputs and len(inputs)<=6 and all(re.fullmatch(r'\w+',x)for x in inputs+outputs)
 n=len(inputs);num=4**n;initial=[];release=[];capture=[];hold=[]
 for i,pin in enumerate(inputs):
  initial.append(f"i[{i}]=1'b{1 if pin in ['SET_B','GATE']else 0};")
  if pin=='RESET_B':release.append(f"i[{i}]=1'b1;")
  if pin=='CLK':capture.append(f"i[{i}]=1'b1;");hold.append(f"i[{i}]=1'b0;")
  if pin=='GATE':hold.append(f"i[{i}]=1'b0;")
  if pin=='GATE_N':hold.append(f"i[{i}]=1'b1;")
 ports=','.join('.'+p+'(i['+str(j)+'])'for j,p in enumerate(inputs))+','+','.join('.'+p+'(o['+str(j)+'])'for j,p in enumerate(outputs))
 text='`timescale 1ns/1ps\nmodule cell_probe;\n'+f'reg [{n-1}:0] i; wire [{len(outputs)-1}:0] o; integer a,p,v,b;\n'+name+' dut('+ports+');\n'
 text+='function val; input integer x; begin case(x) 0:val=0;1:val=1;2:val=1\'bx;3:val=1\'bz;endcase end endfunction\ninitial begin\n'
 text+=f'for(a=0;a<{num};a=a+1) for(p=0;p<{n};p=p+1) for(v=0;v<4;v=v+1) begin\n'
 text+=' #1; '.join(initial)+' #2; '+' #1; '.join(release)+' #2; '+' #1; '.join(capture)+' #2; '+' #1; '.join(hold)+' #2;\n'
 text+=f'for(b=0;b<{n};b=b+1)begin i[b]=val((a>>(2*b))&3); #1; end\n#2; $display("TRACE %0d %0d %0d 0 %b",a,p,v,o); i[p]=val(v); #2; $display("TRACE %0d %0d %0d 1 %b",a,p,v,o);\nend\n$display("CELL_TRANSITIONS_COMPLETE");$finish;end\nendmodule\n'
 return text,2*num*n*4,inputs,outputs
def execute(name,kind,src,library,expected):
 folder=out/(name+'-'+kind);folder.mkdir();exe=folder/'sim'
 command=([str(cvc),'-sv','+define+NSSOC_CVC_ZERO_DELAY','-o',str(exe),str(src),'-v',str(library)]if kind.startswith('cvc')else['iverilog','-g2005-sv','-s','cell_probe','-o',str(exe),str(src),str(library)])
 result={'compile':run(command,folder,'compile.log',300)};assert result['compile']['returncode']==0 and exe.is_file(),result
 result['run']=run([str(exe)]if kind.startswith('cvc')else['vvp','-i',str(exe)],folder,'run.log',300)
 log=(folder/'run.log').read_text();assert result['run']['returncode']==0 and 'CELL_TRANSITIONS_COMPLETE'in log
 lines=[x for x in log.splitlines()if x.startswith('TRACE ')];assert len(lines)==expected and len({tuple(x.split()[1:5])for x in lines})==expected
 result.update(trace_rows=len(lines),trace_sha256=hashlib.sha256(('\n'.join(lines)+'\n').encode()).hexdigest());return result,lines
try:
 bodies={name:body for name,body in re.findall(r'module\s+(\w+)\s*\([^;]*;(.*?)endmodule',original,re.S)}
 for change in changed:
  name=change['module'];text,expected,ins,outs=bench(name,bodies[name]);src=out/(name+'.v');src.write_text(text)
  item=dict(module=name,inputs=ins,outputs=outs,expected_trace_rows=expected,bench_sha256=sha(src),runs={});records.append(item);gold=None
  for kind,library in [('iverilog-original',lib),('iverilog-derived',model),('cvc-derived',model)]:
   result,lines=execute(name,kind,src,library,expected);item['runs'][kind]=result
   if gold is None:gold=lines
   else:
    mismatches=[dict(row=i,original=a,derived=b)for i,(a,b)in enumerate(zip(gold,lines))if a!=b]
    item[kind+'_mismatch_count']=len(mismatches)
    if mismatches:(out/(name+'-'+kind+'-mismatches.json')).write_text(json.dumps(mismatches[:100],indent=2))
    assert not mismatches,(name,kind,mismatches[:3])
  save()
 # A single functional D alias inversion must fail against the original trace.
 first=changed[0]['module'];needle='assign delayed_D = D;';assert needle in derived
 mutant=out/'mutant-zero-delay.v';mutant.write_text(derived.replace(needle,'assign delayed_D = ~D;',1))
 text,expected,_,_=bench(first,bodies[first]);src=out/(first+'.v')
 _,gold=execute(first,'iverilog-negative-reference',src,lib,expected)
 mr,lines=execute(first,'cvc-mutant',src,mutant,expected);diff=sum(a!=b for a,b in zip(gold,lines));assert diff>0
 r.update(status='ALL_16_AFFECTED_CELLS_TRACE_EQUIVALENT_WITH_NEGATIVE_CONTROL',passed=True,mutation=dict(result=mr,mismatches=diff),total_reference_trace_rows=sum(x['expected_trace_rows']for x in records))
except BaseException as e:r.update(passed=False,error=repr(e));raise
finally:r['source_unchanged']=sha(lib)==SOURCE_SHA;save()
