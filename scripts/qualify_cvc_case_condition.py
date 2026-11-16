import os,pathlib,subprocess,json,hashlib,random
assert os.environ.get('GITHUB_ACTIONS')=='true'
root=pathlib.Path.cwd();out=root/'case-condition-probe';out.mkdir()
rng=random.Random(12345);patterns=['0'*64,'1'*64,'x'*64,'z'*64,'x0'*32,'z1'*32,'0'*63+'1','1'+'x'*63]
lines=['`timescale 1ns/1ps','module probe;','reg [63:0] a,b,c,d,p;reg [575:0] v;reg direct,staged,fa,fb,fv;','initial begin'];gold=[]
for i in range(512):
 p=patterns[2]if i==0 else rng.choice(patterns);aa=patterns[2]if i==0 else rng.choice(patterns);cc=patterns[2]if i==0 else rng.choice(patterns)
 bb=aa;dd=cc;vv=p*9
 if i and i%4==1:bb=rng.choice(patterns)
 if i and i%4==2:dd=rng.choice(patterns)
 if i and i%4==3:
  pos=rng.randrange(576);vv=vv[:pos]+rng.choice('01xz')+vv[pos+1:]
 expect=int(aa!=bb or cc!=dd or vv!=p*9);gold.append(expect)
 lines+=['a=64\'b'+aa+';b=64\'b'+bb+';c=64\'b'+cc+';d=64\'b'+dd+';p=64\'b'+p+';v=576\'b'+vv+';#1;',
 'direct=0;if(a!==b || c!==d || v!=={9{p}})direct=1;',
 'fa=(a!==b);fb=(c!==d);fv=(v!=={9{p}});staged=fa||fb||fv;',
 '$display("COND_TRACE '+str(i)+' %b %b %b %b %b",direct,staged,fa,fb,fv);']
lines+=['$display("COND_DONE");$finish;end','endmodule'];bench=out/'probe.v';bench.write_text('\n'.join(lines)+'\n')
sha=lambda p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
r=dict(source_head=os.environ['GITHUB_SHA'],passed=False,scope='Model-free four-state case-inequality compound-if compiler comparison; no chip acceptance',bench_sha256=sha(bench),cases=[])
def run(cmd,log):
 with log.open('w')as f:return subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,timeout=180).returncode
try:
 for kind in ['iverilog','cvc','cvc-Ogate','cvc-O','cvc-interp']:
  folder=out/kind;folder.mkdir();exe=folder/'sim';cvc=root/'cvc-source/build64/cvc64'
  cmd=['iverilog','-g2012','-s','probe','-o',str(exe),str(bench)]if kind=='iverilog'else[str(cvc),'-sv']+({'cvc':[],'cvc-Ogate':['-Ogate'],'cvc-O':['-O'],'cvc-interp':['+interp']}[kind])+([]if kind=='cvc-interp'else['-o',str(exe)])+[str(bench)]
  case=dict(kind=kind,command=cmd);r['cases'].append(case)
  if kind=='cvc-interp':code=run(cmd,folder/'run.log')
  else:
   case['compile_returncode']=run(cmd,folder/'compile.log');assert case['compile_returncode']==0
   code=run(['vvp',str(exe)]if kind=='iverilog'else[str(exe)],folder/'run.log')
  text=(folder/'run.log').read_text();rows=[x.split()for x in text.splitlines()if x.startswith('COND_TRACE ')];assert code==0 and len(rows)==512 and 'COND_DONE'in text
  mismatches=[dict(row=i,expected=gold[i],observed=row)for i,row in enumerate(rows)if row[1]!=str(i) or row[2]!=str(gold[i]) or row[3]!=str(gold[i]) or int(row[4])|int(row[5])|int(row[6])!=gold[i]]
  case.update(run_returncode=code,trace_rows=len(rows),mismatch_count=len(mismatches),first_mismatches=mismatches[:12],log_sha256=sha(folder/'run.log'))
 r['passed']=all(c['mismatch_count']==0 for c in r['cases']);assert r['passed'],'Compound case condition differs from bitwise Python oracle'
finally:(out/'result.json').write_text(json.dumps(r,indent=2))
