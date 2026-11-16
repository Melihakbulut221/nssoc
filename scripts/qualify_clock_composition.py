import os,pathlib,json,hashlib,subprocess,re
from ihp_zero_delay_aliases import adapt,SOURCE_SHA
assert os.environ.get('GITHUB_ACTIONS')=='true'
root=pathlib.Path.cwd();out=root/'clock-composition-qualification';out.mkdir()
sha=lambda p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
lib=root/'hw/soc/tools/ihp-native-boot-c4b8b4e/ihp-sg13g2/libs.ref/sg13g2_stdcell/verilog/sg13g2_stdcell.v';assert sha(lib)==SOURCE_SHA
model=out/'derived.v';derived,changes=adapt(lib.read_text());model.write_text(derived)
bench=root/'scripts/tb_clock_composition.v';cvc=root/'cvc-source/build64/cvc64'
r=dict(source_head=os.environ['GITHUB_SHA'],passed=False,chip_accepted=False,source_sha256=SOURCE_SHA,derived_sha256=sha(model),bench_sha256=sha(bench),cases=[],scope='Zero-delay sequential cell composition across direct, gated and buffered clocks. Compare native Icarus and explicitly enabled derived aliases; classify differences from ideal RTL, not SDF or chip acceptance.')
def run(cmd,log):
 with log.open('w')as f:return subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,timeout=180).returncode
try:
 traces={}
 for kind in ['iverilog-original','iverilog-derived-disabled','iverilog-derived-enabled','cvc-derived','cvc-Ogate','cvc-O','cvc-interp']:
  folder=out/kind;folder.mkdir();exe=folder/'sim';library=lib if kind=='iverilog-original' else model
  is_cvc=kind.startswith('cvc')
  options={'cvc-derived':[],'cvc-Ogate':['-Ogate'],'cvc-O':['-O'],'cvc-interp':['+interp']}.get(kind,[])
  cmd=([str(cvc),'-sv','+nospecify','+define+NSSOC_CVC_ZERO_DELAY']+options+([]if kind=='cvc-interp'else['-o',str(exe)])+[str(bench),'-v',str(library)] if is_cvc else ['iverilog','-g2012']+(['-DNSSOC_CVC_ZERO_DELAY']if kind=='iverilog-derived-enabled' else [])+['-s','clock_composition','-o',str(exe),str(bench),str(library)])
  case=dict(kind=kind,command=cmd);r['cases'].append(case)
  if kind=='cvc-interp':
   case['compile_and_run_combined']=True;code=run(cmd,folder/'run.log')
  else:
   case['compile_returncode']=run(cmd,folder/'compile.log');assert case['compile_returncode']==0 and exe.is_file()
   code=run([str(exe)]if is_cvc else ['vvp',str(exe)],folder/'run.log')
  text=(folder/'run.log').read_text();case.update(run_returncode=code,log_sha256=sha(folder/'run.log'))
  done=re.findall(r'COMPOSITION_DONE cycles=(\d+) ideal_mismatches=(\d+)',text);assert code==0 and len(done)==1 and int(done[0][0])==513
  trace=[line for line in text.splitlines()if line.startswith('COMPOSITION_TRACE ')];assert len(trace)==513;traces[kind]=trace;case.update(trace_rows=513,ideal_mismatch_count=int(done[0][1]))
 gold=traces['iverilog-original'];r['comparison']={}
 for kind,trace in traces.items():
  diffs=[dict(row=i,native=x,candidate=y)for i,(x,y)in enumerate(zip(gold,trace))if x!=y];r['comparison'][kind]=dict(mismatch_count=len(diffs),first_mismatches=diffs[:12])
 r['sources_unchanged']=sha(lib)==SOURCE_SHA and sha(bench)==r['bench_sha256'];assert r['sources_unchanged']
 r['passed']=all(x['mismatch_count']==0 for x in r['comparison'].values()) and all(x['ideal_mismatch_count']==0 for x in r['cases'])
 assert r['passed'],'Sequential zero-delay composition differs from reference or ideal cycle behavior'
finally:
 (out/'result.json').write_text(json.dumps(r,indent=2))
