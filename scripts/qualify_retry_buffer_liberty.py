# SPDX-License-Identifier: Apache-2.0
"""Actual Yosys SAT on exact frozen three-corner positive buffer functions."""
import pathlib,hashlib,tarfile,json,subprocess,os,base64
assert os.environ.get('GITHUB_ACTIONS')=='true'
P=pathlib.Path;out=P('out');native=out/'native';derived=out/'derived';native.mkdir(parents=True);derived.mkdir()
def sha(p):
 h=hashlib.sha256()
 with P(p).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
assert sha('/mnt/s/pkg.tgz')=='822dab7067d901fa79dabffffff784baf5c9965f0a5091eba67acdc48b9956f4'
contracts=[]
with tarfile.open('/mnt/s/pkg.tgz','r|gz') as t:
 for m in t:
  if m.isfile() and m.name.endswith('/input-contract.json'):contracts.append(json.loads(t.extractfile(m).read()))
assert len(contracts)==1;contract=contracts[0]
specs=[('fast','sg13g2_stdcell_fast_1p32V_m40C.lib','fd479d3fd11358bbacee450dc7352b46de8588cb'),('slow','sg13g2_stdcell_slow_1p08V_125C.lib','6dd075da1073a86a98d9804019842be3d2f13a9f'),('typ','sg13g2_stdcell_typ_1p20V_25C.lib','9654b7cb685cf7d376b9842089ea2903540448e8')]
result={'status':'RUNNING','scope':'Boolean equivalence of the exact buf1/buf4 Liberty models used by the frozen implementation package in each of three corners. Full physical timing, extraction, DRC/LVS and production approval remain separate.','manufacturing_approval':False,'corners':[]}
def save():(derived/'result.json').write_text(json.dumps(result,indent=2))
save()
for corner,name,blob in specs:
 raw=subprocess.check_output(['gh','api','repos/IHP-GmbH/IHP-Open-PDK/git/blobs/'+blob],timeout=60)
 data=base64.b64decode(json.loads(raw)['content']);assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==blob
 lib=native/name;lib.write_bytes(data);digest=sha(lib)
 matches={path:row['sha256'] for path,row in contract['input_files'].items() if path.endswith('/'+name)}
 assert matches and set(matches.values())=={digest},('Frozen library differs',name,matches,digest)
 if corner=='typ':assert digest=='968b0cfdcefc49a88d9a5c48874769eaad9aba3509e1240b5e14a821bb07a3c4'
 row={'corner':corner,'library':name,'git_blob':blob,'sha256':digest,'frozen_package_files':matches,'tests':[]};result['corners'].append(row);save()
 for negative in [False,True]:
  label=corner+('-inversion-control' if negative else '-equivalence')
  dut='sg13g2_inv_1 candidate(.A(a),.Y(y));' if negative else 'sg13g2_buf_4 candidate(.A(a),.X(y));'
  miter=native/(label+'.v');miter.write_text('module miter(input a,output equivalent); wire x,y; sg13g2_buf_1 reference(.A(a),.X(x)); '+dut+' assign equivalent=(x==y); endmodule\n')
  commands='read_liberty -ignore_miss_func '+str(lib)+'; read_verilog '+str(miter)+'; hierarchy -check -top miter; prep -top miter -flatten; check -assert; sat -verify -prove equivalent 1 -show a,x,y'
  env=dict(os.environ);env.pop('GH_TOKEN',None);env.pop('GITHUB_TOKEN',None)
  log=derived/(label+'.log')
  with log.open('w') as f:p=subprocess.run(['/mnt/s/librelane.AppImage','yosys','-Q','-p',commands],stdout=f,stderr=subprocess.STDOUT,env=env,timeout=300)
  text=log.read_text(errors='replace')
  passed=(p.returncode!=0 and 'proof did fail' in text.lower()) if negative else (p.returncode==0 and 'SAT proof finished - no model found: SUCCESS!' in text)
  row['tests'].append({'case':label,'returncode':p.returncode,'expected_counterexample':negative,'passed':passed,'log_sha256':sha(log)});save();assert passed,(label,p.returncode,text[-2000:])
assert len(result['corners'])==3 and all(len(c['tests'])==2 and all(t['passed'] for t in c['tests']) for c in result['corners'])
result['status']='FROZEN_THREE_CORNER_BUFFER_EQUIVALENCE_AND_INVERSION_CONTROLS_PASSED';save();print(json.dumps(result))
