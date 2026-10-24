"""Read-only actual /proc guard checks; no signal or process launch."""
from pathlib import Path
import ast,copy,hashlib,json,sys
R=Path.cwd();B=Path(__file__).resolve().parent
sys.path.insert(0,str(R/'scripts'))
import characterize_pcie_clock_trim_stream_v2 as life
source=B/'supersede_v16_after_validation_v2.py'
module=ast.parse(source.read_text());node=next(n for n in module.body if isinstance(n,ast.FunctionDef) and n.name=='same')
guards=json.loads((B/'supersession-identity-guards02.json').read_text())
namespace=dict(Path=Path,life=life,hashlib=hashlib,guards=guards)
exec(compile(ast.Module(body=[node],type_ignores=[]),str(source),'exec'),namespace)
same=namespace['same'];results=[]
for kind,expected in guards['jobs'].items():
 assert same(expected);results.append(dict(kind=kind,case='actual_owned_identity',result='PASS'))
 wrong=copy.deepcopy(expected);wrong['start_ticks']=str(int(wrong['start_ticks'])+1);assert not same(wrong)
 results.append(dict(kind=kind,case='wrong_start_refused',result='PASS'))
 for field,value in [('process_group',-1),('commandline_bytes',0),('commandline_sha256','0'*64)]:
  wrong=copy.deepcopy(expected);wrong[field]=value
  try:same(wrong)
  except AssertionError:results.append(dict(kind=kind,case='wrong_'+field+'_refused',result='PASS'))
  else:raise RuntimeError('guard escaped '+field)
 old=guards['boot_id'];guards['boot_id']='wrong-boot'
 try:
  try:same(expected)
  except AssertionError:results.append(dict(kind=kind,case='wrong_boot_refused',result='PASS'))
  else:raise RuntimeError('boot guard escaped')
 finally:guards['boot_id']=old
# The mutant omits the real emitted group assertion and must escape the wrong
# group negative: this checks that this predicate is actually discriminating.
mut=copy.deepcopy(node);before=len(mut.body)
mut.body=[n for n in mut.body if not (isinstance(n,ast.Assert) and 'process_group' in ast.unparse(n.test))]
assert len(mut.body)==before-1
ns=dict(namespace);exec(compile(ast.Module(body=[mut],type_ignores=[]),str(source)+':mutant','exec'),ns)
wrong=copy.deepcopy(guards['jobs']['idle_continuation']);wrong['process_group']=-1
assert ns['same'](wrong);results.append(dict(case='actual_guard_group_assertion_omission_mutant_escapes_negative_detected',result='PASS'))
def pin(p):return dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
r=dict(status='PASS_READ_ONLY_REAL_PROCESS_IDENTITY_GUARDS',source=pin(source),guard_record=pin(B/'supersession-identity-guards02.json'),method=pin(Path(__file__)),checks=results,signals_sent=False,scope='Exact same() AST from frozen superseder, live existing owned processes, wrongstart/group/commandbytes/hash/boot rejected; actual omission of group check detected by negative. No killpg, signal, lifecycle execution or independent source peer claimed.')
(B/'identity-guard-controls02.json').write_text(json.dumps(r,indent=2)+'\n');print(r['status'],len(results))
