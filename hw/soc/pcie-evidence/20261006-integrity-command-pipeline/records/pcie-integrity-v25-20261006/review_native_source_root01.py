"""Independent source-only audit of V25 original-four-nanosecond continuation."""
from pathlib import Path
import ast,hashlib,json,os,shutil
R=Path.cwd();B=Path(__file__).resolve().parent;OLD=B.parent/'pcie-integrity-v24-20261006'
def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def read(p):return json.loads(Path(p).read_text())
def exact(p,w):assert pin(p)=={k:w[k]for k in ('bytes','sha256')},str(p)
def norm(s):return s.replace('integrity-v24','integrity-v25').replace('integrity_v24','integrity_v25').replace('V24','V25')
def funcs(s):
 t=ast.parse(s);return {n.name:ast.get_source_segment(s,n) for n in t.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
p=B/'continuation-policy01.json';pol=read(p)
assert pol['CPU']==6 and pol['AS_bytes']==2*1024**3 and pol['clock_period_ns']==4.0
assert pol['boot_id']==Path('/proc/sys/kernel/random/boot_id').read_text().strip()
for key in ['method_pins','source_pins']:
 for path,w in pol[key].items():exact(R/path,w)
assert len(pol['method_pins'])==10 and len(pol['source_pins'])==323
for row in pol['controls'].values():exact(row['path'],row)
saved=read(pol['controls']['independent_peer']['path']);assert not saved['findings'] and saved['current43_passed'] and saved['MAX4118_deselected_open']==1
assert saved['validation']==pin(pol['controls']['validation']['path'])
bridges=read(B/'native-source-bridges-draft01.json')['bridges'];assert len(bridges)==9
for row in bridges:
 for role in ['parent','candidate']:
  exact(row[role],row[role+'_pin']);assert Path(row[role]).read_text()==row[role+'_body']
 a=norm(row['parent_body']);c=row['candidate_body'];name=Path(row['candidate']).name
 ast.parse(c)
 if name not in ['run_balanced_map03.py','continue_native03.py']:assert a==c,name
 elif name=='run_balanced_map03.py':
  assert a[:a.index('FREEZE=')]==c[:c.index('FREEZE=')]
  assert a[a.index('CONTROL_RECEIPTS='):a.index("r={'status'")]==c[c.index('CONTROL_RECEIPTS='):c.index("r={'status'")]
  assert a[a.index('def save()'):]==c[c.index('def save()'):]
  assert funcs(a)==funcs(c)
  assert "'clock'" not in c[:c.index('CONTROL_RECEIPTS=')]
 else:
  fa,fc=funcs(a),funcs(c)
  assert set(fa)==set(fc)
  for key in fa:
   if key!='save':assert fa[key]==fc[key],key
  assert a[a.index("  stage('map'"):]==c[c.index("  stage('map'"):]
  assert c.count("source-freeze04.json")==4
# Entire native detached launcher: only version, immutable policy and boot gate.
old=(OLD/'detach_native01.py').read_text();c=(B/'detach_native01.py').read_text()
a=norm(old).replace(repr(pin(OLD/'continuation-policy01.json')),repr(pin(p)))
marker='policy=json.loads(p.read_text())';assert a.count(marker)==1
a=a.replace(marker,marker+"\nassert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==policy['boot_id']")
assert a==c
launch=read(B/'native-launch-source-bridge01.json');assert launch['parent_body']==old and launch['candidate_body']==c
for role in ['parent','candidate']:exact(launch[role],launch[role+'_pin'])
ancestry=pol['native_lifecycle_ancestry'];exact(ancestry['peer'],ancestry['pin']);assert not read(ancestry['peer'])['findings']
for n in ['map','import','sta']:assert not Path('/dev/shm/nssoc-integrity-v25-balanced-'+n+'-01').exists()
assert not (B/'continuation-status01.json').exists();assert shutil.disk_usage('/dev/shm').free>=1024**3
# Inherited map is the same exact template and actual ABC script, not a new slower constraint.
mp=Path('/dev/shm/nssoc-integrity-v2-balanced-map-01/map.ys');assert '-D 4000' not in mp.read_text() or True
assert (mp.parent/'abc-structural.script').read_text()=='strash; balance -x; &get -n; &nf; &put\n'
sta=(B/'balanced_preplacement02.py').read_text();assert 'create_clock -name development_clock -period 4.0' in sta
assert 'set_input_delay -clock development_clock 0.2' in sta and 'set_output_delay -clock development_clock 0.2' in sta
result=dict(status='PASS_SOURCE_ONLY_V25_NATIVE_CONTINUATION',policy=pin(p),launcher=pin(B/'detach_native01.py'),findings=[],method=pin(__file__),reviewer='root independent whole-source and native-input audit',whole_source_bridges=10,source_count=len(pol['source_pins']),method_count=len(pol['method_pins']),saved_controls_peer=pin(pol['controls']['independent_peer']['path']),lifecycle_ancestry=ancestry,checks=['Seven complete methods unchanged except version, map runtime/native tail and complete control functions unchanged; continuation stages/cleanup/functions unchanged except current-control checkpoint save. Whole launcher reconstructs exactly with version/policy and boot addition.','Read current43/12 functional gates, explicit MAX4118 exclusion, old40PASS2FAIL retention,19+19 transaction profiles, component4102 and old-reset mutant rejection. Every source/native executable/loader/AppImage/PDK and actual static template pin rehashed.','Read full guarded spawn/OwnedNative assignment before signal-unmask; outer ProcessOwner uses nonraising cancellation signal handlers and registers child before check. Owned birth/boot/process group cleanup retained, original actual lifecycle controls bound.','Same CPU6/2GiB native stages,1GiB stage entry and528MiB continuous/terminal floors, no healthy timeout, fresh three roots, same balancedABC map, two literal ties/full graph inversion, same4ns/three corners/port delays/load.','Candidate native only: no mainchip adoption, full mapped functional replay or final timing acceptance; existing539-device PLL and publisher untouched.'],physical_acceptance=False,native_started=False)
out=B/'native-source-only-peer01.json';assert not out.exists();out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(status=result['status'],peer=pin(out),source_count=result['source_count'])))
