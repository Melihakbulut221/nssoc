from pathlib import Path
import hashlib,json,ast
R=Path.cwd();B=Path(__file__).resolve().parent;O=B.parent/'pcie-integrity-v23-20261006';rows=[]
def pin(p):
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
for n in ['native_lifecycle02.py','balanced_import02.py','balanced_preplacement02.py','measure_registered_boundary.py','prove_balanced_import.py','review_timing.py','analyze_critical_path.py']:
 old=(O/n).read_text();s=old;edits=[]
 for a,b in [('v23','v24'),('V23','V24')]:
  if a in s:edits.append(dict(before=a,after=b,count=s.count(a)));s=s.replace(a,b)
 p=B/n;assert not p.exists();p.write_text(s);ast.parse(s)
 reverse=s
 for e in reversed(edits):reverse=reverse.replace(e['after'],e['before'])
 assert reverse==old
 rows.append(dict(parent=str(O/n),parent_pin=pin(O/n),path=str(p),pin=pin(p),replacements=edits))
p=B/'native-method-bridges-draft01.json';p.write_text(json.dumps(rows,indent=2)+'\n');print(pin(p));print('Seven prepared helpers only; full functional/control source gates still pending, no native launch.')
