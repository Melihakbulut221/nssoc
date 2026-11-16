import os,pathlib,json,hashlib,subprocess
assert os.environ.get('GITHUB_ACTIONS')=='true'
root=pathlib.Path.cwd();out=root/'sram-sequence-qualification';out.mkdir()
sha=lambda p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
lock=json.loads((root/'hw/soc/pnr/ihp-native-boot.lock.json').read_text());assert lock['commit']=='c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c'
models=[];model_hashes={}
for item in lock['files']:
 if '/verilog/RM_IHPSG13_1P_' in item['path']:
  p=root/'hw/soc/tools/ihp-native-boot-c4b8b4e'/item['path'];assert sha(p)==item['sha256'];models.append(str(p));model_hashes[str(p)]=sha(p)
assert len(models)==2
bench=root/'scripts/tb_native_sram_sequence.v';cvc=root/'cvc-source/build64/cvc64'
r=dict(source_head=os.environ['GITHUB_SHA'],passed=False,chip_accepted=False,models=model_hashes,bench_sha256=sha(bench),cases=[],scope='Untouched functional 1P SRAM stable-input sequence and same-edge downstream capture comparison. No SDF, BIST mux switching, two-port SRAM, arbitrary X transitions or whole-chip equivalence claim.')
def run(cmd,log):
 with log.open('w')as f:return subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,timeout=180).returncode
try:
 traces={}
 for engine in ['iverilog','cvc']:
  for mutant in [False,True]:
   folder=out/(engine+('-mutant'if mutant else'-positive'));folder.mkdir();exe=folder/'sim'
   cmd=([str(cvc),'-sv','+nospecify','+define+FUNCTIONAL']+(['+define+MUTATE_ADDRESS']if mutant else[])+['-o',str(exe),str(bench)]+models if engine=='cvc' else ['iverilog','-g2012','-DFUNCTIONAL']+(['-DMUTATE_ADDRESS']if mutant else[])+['-s','tb_sram_sequence','-o',str(exe),str(bench)]+models)
   case=dict(engine=engine,mutation=mutant,compile_returncode=run(cmd,folder/'compile.log'));r['cases'].append(case);assert case['compile_returncode']==0 and exe.is_file()
   code=run([str(exe)]if engine=='cvc'else['vvp',str(exe)],folder/'run.log');text=(folder/'run.log').read_text();case.update(run_returncode=code,log_sha256=sha(folder/'run.log'))
   if mutant:
    case['detected']='SRAM_SEQUENCE_FAIL'in text and 'SRAM_SEQUENCE_PASS'not in text;assert case['detected']
   else:
    trace=[line for line in text.splitlines()if line.startswith('SRAM_TRACE ')];assert code==0 and 'SRAM_SEQUENCE_PASS cycles=12289'in text and 'SRAM_SEQUENCE_FAIL'not in text and len(trace)==12289
    traces[engine]=trace;case.update(passed=True,trace_rows=len(trace),trace_sha256=hashlib.sha256(('\n'.join(trace)).encode()).hexdigest())
 assert traces['iverilog']==traces['cvc']
 assert all(sha(p)==h for p,h in model_hashes.items()) and sha(bench)==r['bench_sha256'];r.update(passed=True,sources_unchanged=True,identical_traces=True)
finally:
 (out/'result.json').write_text(json.dumps(r,indent=2))
