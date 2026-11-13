# SPDX-License-Identifier: Apache-2.0
"""Inspect pinned simulator solver capability on synthetic RC only."""
import hashlib,json,os,pathlib,subprocess
P=pathlib.Path;out=P('out');out.mkdir();native=P('native');native.mkdir()
with open('engine','rb') as f:assert hashlib.file_digest(f,'sha256').hexdigest()=='103134f6e3bf71771a7f9c94cc43fd5ea2f9d51490116718814aa344e9c51509'
env=dict(os.environ);env.pop('GH_TOKEN',None);env.pop('GITHUB_TOKEN',None)
engine=str(P('engine').resolve())
r={'status':'CAPABILITY_DIAGNOSTIC_ONLY','engine_sha256':'103134f6e3bf71771a7f9c94cc43fd5ea2f9d51490116718814aa344e9c51509','pll_acquisition_accepted':False,'production_accepted':False,'cases':{}}
for label,args in [('version',[engine,'--version']),('linked_libraries',['ldd',engine])]:
 p=subprocess.run(args,env=env,capture_output=True,text=True,timeout=30);r[label]={'returncode':p.returncode,'output':p.stdout+p.stderr}
for option in ['default','klu']:
 case=native/option;case.mkdir()
 circuit='Synthetic solver capability RC\nV1 in 0 pulse(0 1 0 1n 1n 5n 10n)\nR1 in out 1000\nC1 out 0 1p\n'
 if option=='klu':circuit+='.option klu\n'
 circuit+='.tran 0.1n 20n\n.control\nrun\nprint v(out)\nquit\n.endc\n.end\n';(case/'probe.cir').write_text(circuit)
 p=subprocess.run([engine,'-n','-b','probe.cir'],cwd=case,env=env,capture_output=True,text=True,timeout=60)
 text=p.stdout+p.stderr;(case/'run.log').write_text(text)
 r['cases'][option]={'returncode':p.returncode,'diagnostic_lines':[l for l in text.splitlines() if any(w in l.lower() for w in ['klu','sparse','solver','error','warning','rows','unsupported','unknown'])],'log_sha256':hashlib.sha256(text.encode()).hexdigest()}
(out/'solver-capability.json').write_text(json.dumps(r,indent=2));print(json.dumps(r))
