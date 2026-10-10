from pathlib import Path
import ast,hashlib,json
B=Path(__file__).resolve().parent
def pin(p):
 p=Path(p)
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
f=B/'targeted-source-freeze.json';assert pin(f)==dict(bytes=3686,sha256='55568e8e9abcfab63a784b398fe8b8766bbe9e3bd44c970f173d644b0a936072')
x=json.loads(f.read_text());assert pin(B/'source-freeze.json')==x['base_freeze'];assert pin(B/'source-only-peer-root.json')==x['base_peer'];assert pin(B/'derive_targeted_screens.py')==x['method']
basepeer=json.loads((B/'source-only-peer-root.json').read_text());assert basepeer['status'].startswith('PASS_')and not basepeer['findings']
rows=[]
for name,v in x['variants'].items():
 old,new=Path(v['before']['path']),Path(v['after']['path'])
 for p,record in [(old,v['before']),(new,v['after'])]:assert pin(p)=={k:record[k]for k in ['bytes','sha256']}
 a,b=old.read_text(),new.read_text();inverse=b
 for sub in reversed(v['whole_source_substitutions']):
  assert inverse.count(sub['after'])==1;inverse=inverse.replace(sub['after'],sub['before'])
 assert inverse==a
 fa={n.name:ast.dump(n,include_attributes=False)for n in ast.parse(a).body if isinstance(n,ast.FunctionDef)}
 fb={n.name:ast.dump(n,include_attributes=False)for n in ast.parse(b).body if isinstance(n,ast.FunctionDef)}
 for n in v['unchanged_functions']:assert fa[n]==fb[n]
 report=next(n for n in ast.parse(b).body if isinstance(n,ast.FunctionDef)and n.name=='report')
 namespace={};exec(compile(ast.Module(body=[report],type_ignores=[]),str(new),'exec'),namespace)
 commands=namespace['report']('PEER_ONLY_NO_NATIVE');checks=[s for s in commands if s.startswith('report_checks')and '-to' in s]
 assert len(checks)==18 and len(set(checks))==18
 expected={f'report_checks -corner {c} -to [get_pins {e}/D] -path_delay {d} -group_path_count 1 -fields {{slew cap fanout}} -digits 6'for e in ['_26191_','_26187_','_26189_']for c in ['slow','typical','fast']for d in ['max','min']}
 assert set(checks)==expected
 assert not Path(v['new_output']).exists()
 rows.append(dict(variant=name,before=pin(old),after=pin(new),whole_source_inverse=True,unchanged_functions=v['unchanged_functions'],unique_target_report_checks=18,emitted_strings_only=True))
r=dict(status='PASS_SOURCE_ONLY_RX14_TARGETED_GRT_REPORTS',freeze=pin(f),method=pin(__file__),findings=[],variants=rows,scope='Independent complete-source inverse plus five function AST identities and pure report-string generation. Only fresh output path and18 endpoint/corner/minmax reports added. All physical operations, resource/cleanup and unchanged constraints inherit root-reviewed RX14 sources. No EDA/proof/DRT/simulation executed; no measured gain or timing closure claim.')
p=B/'targeted-source-only-peer-pll.json';assert not p.exists();p.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(path=str(p),**pin(p))))
