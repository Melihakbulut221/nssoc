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
from ihp_functional_nba import adapt,SOURCE_SHA
lib=root/'hw/soc/tools/ihp-native-boot-c4b8b4e/ihp-sg13g2/libs.ref/sg13g2_stdcell/verilog/sg13g2_stdcell.v'
assert sha(lib)==SOURCE_SHA
model_hashes[str(lib)]=sha(lib)
derived=out/'derived.v';derived.write_text(adapt(lib.read_text())[0])
bench=root/'scripts/tb_native_sram_sequence.v';cvc=root/'cvc-source/build64/cvc64'
r=dict(source_head=os.environ['GITHUB_SHA'],passed=False,chip_accepted=False,models=model_hashes,bench_sha256=sha(bench),cases=[],scope='Untouched functional 1P SRAM stable-input sequence and same-edge RTL and standard-cell capture across 0..8 clock buffers comparison. No SDF, BIST mux switching, two-port SRAM, arbitrary X transitions or whole-chip equivalence claim.')
def run(cmd,log):
 with log.open('w')as f:return subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,timeout=180).returncode
try:
 import zipfile,io
 def api(path):return json.loads(subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/'+path]))
 pr=api('actions/runs/43804069756');assert pr['head_sha']=='9759bb82e933e73fe70a3687a0ef0edb0fce249b' and pr['conclusion']=='failure' and pr['run_attempt']==1
 meta=api('actions/artifacts/14197712837');h='0036c6745330290efa319b0f9781ab83f86ec7a7aef660187ccbf3b9f40ed8ac'
 assert not meta['expired'] and meta['digest']=='sha256:'+h and meta['workflow_run']['id']==pr['id'] and meta['workflow_run']['head_sha']==pr['head_sha']
 blob=subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/actions/artifacts/14197712837/zip']);assert hashlib.sha256(blob).hexdigest()==h
 proof=json.loads(zipfile.ZipFile(io.BytesIO(blob)).read('case-condition-probe/result.json'))
 assert proof['source_head']==pr['head_sha'] and proof['bankwise_passed'] and not proof['passed'] and len(proof['cases'])==5
 assert all(c['trace_rows']==512 and c['bankwise_mismatch_count']==0 for c in proof['cases'])
 assert {c['kind']:c['mismatch_count']for c in proof['cases']}=={'iverilog':0,'cvc':128,'cvc-Ogate':128,'cvc-O':128,'cvc-interp':0}
 r['comparison_workaround']=dict(proof_run=pr['id'],artifact=meta['id'],sha256=h,scope='All 576 capture bits compared as nine 64-bit case-inequalities; preserves X/Z distinction and original scoreboard. No model or reset change. Original wide compiled expression known incorrect.')
 traces={}
 for engine in ['iverilog','iverilog-derived','cvc','cvc-interp']:
  for mutant in [False,True]:
   folder=out/(engine+('-mutant'if mutant else'-positive'));folder.mkdir();exe=folder/'sim'
   cmd=([str(cvc),'-sv','+nospecify','+define+FUNCTIONAL','+define+NSSOC_CVC_ZERO_DELAY']+(['+define+MUTATE_ADDRESS']if mutant else[])+['-o',str(exe),str(bench)]+models if engine.startswith('cvc') else ['iverilog','-g2012','-DFUNCTIONAL']+(['-DNSSOC_CVC_ZERO_DELAY']if engine=='iverilog-derived'else[])+(['-DMUTATE_ADDRESS']if mutant else[])+['-s','tb_sram_sequence','-o',str(exe),str(bench)]+models)
   cmd += ['-v',str(derived)]if engine.startswith('cvc')else[str(derived if engine=='iverilog-derived'else lib)]
   case=dict(engine=engine,mutation=mutant);r['cases'].append(case)
   if engine=='cvc-interp':
    idx=cmd.index('-o');del cmd[idx:idx+2];cmd.insert(2,'+interp')
    case['compile_and_run_combined']=True;code=run(cmd,folder/'run.log')
   else:
    case['compile_returncode']=run(cmd,folder/'compile.log');assert case['compile_returncode']==0 and exe.is_file()
    code=run([str(exe)]if engine.startswith('cvc')else['vvp',str(exe)],folder/'run.log')
   text=(folder/'run.log').read_text();case.update(run_returncode=code,log_sha256=sha(folder/'run.log'))

   if mutant:
    case['detected']='SRAM_SEQUENCE_FAIL'in text and 'SRAM_SEQUENCE_PASS'not in text
    case['meaningful_control']=any(x.get('passed') and x['engine']==engine and not x['mutation']for x in r['cases'])
   else:
    trace=[line for line in text.splitlines()if line.startswith('SRAM_TRACE ')]
    good=code==0 and 'SRAM_SEQUENCE_PASS cycles=12289'in text and 'SRAM_SEQUENCE_FAIL'not in text and len(trace)==12289
    traces[engine]=trace;case.update(passed=good,trace_rows=len(trace),trace_sha256=hashlib.sha256(('\n'.join(trace)).encode()).hexdigest())
 r['interpreter_matches_native']=traces['iverilog']==traces['cvc-interp']
 r['identical_traces']=traces['iverilog']==traces['cvc']==traces['iverilog-derived']==traces['cvc-interp']
 assert all(x.get('detected') and x.get('meaningful_control') if x['mutation']else x.get('passed')for x in r['cases']), 'At least one engine fails the original scoreboard; retain every diagnostic'
 assert r['identical_traces']
 assert all(sha(p)==h for p,h in model_hashes.items()) and sha(bench)==r['bench_sha256'];r.update(passed=True,sources_unchanged=True,identical_traces=True)
finally:
 (out/'result.json').write_text(json.dumps(r,indent=2))
