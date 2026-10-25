"""Prepare exact existing same-profile methods; no native launch or acceptance."""
from pathlib import Path
import hashlib,json
R=Path.cwd();B=Path(__file__).resolve().parent;O=B.parent/'pcie-integrity-v22-20261006';rows=[]
def pin(p):
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
for n in ['native_lifecycle02.py','balanced_import02.py','balanced_preplacement02.py','measure_registered_boundary.py','prove_balanced_import.py','review_timing.py','analyze_critical_path.py']:
 s=(O/n).read_text();edits=[]
 for a,b in [('v22','v23'),('V22','V23')]:
  if a in s:edits.append(dict(before=a,after=b,count=s.count(a)));s=s.replace(a,b)
 p=B/n;assert not p.exists();p.write_text(s)
 rows.append(dict(parent=str(O/n),parent_pin=pin(O/n),path=str(p),pin=pin(p),replacements=edits))
p=B/'native-method-bridges-draft01.json';p.write_text(json.dumps(rows,indent=2)+'\n');print(pin(p))
