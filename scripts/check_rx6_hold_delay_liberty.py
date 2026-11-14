# SPDX-License-Identifier: Apache-2.0
"""Require exact non-inverting Liberty function before endpoint hold ECO."""
import pathlib,gzip,re,json,hashlib
root=pathlib.Path('hw/soc/tools');rows=[]
def body(text,pattern):
 m=re.search(pattern,text);assert m,pattern
 start=text.index('{',m.start());depth=0
 for pos in range(start,len(text)):
  if text[pos]=='{':depth+=1
  elif text[pos]=='}':
   depth-=1
   if not depth:return text[start+1:pos]
 raise AssertionError('Unbalanced Liberty group')
for p in root.rglob('*'):
 if not p.is_file() or 'sg13g2_stdcell' not in str(p) or not str(p).endswith(('.lib','.lib.gz')):continue
 raw=p.read_bytes();s=(gzip.decompress(raw) if p.suffix=='.gz' else raw).decode()
 pat=r'\bcell\s*\(\s*"?sg13g2_dlygate4sd3_1"?\s*\)\s*\{'
 if not re.search(pat,s):continue
 c=body(s,pat);x=body(c,r'\bpin\s*\(\s*"?X"?\s*\)\s*\{')
 f=re.findall(r'\bfunction\s*:\s*"([^"]+)"\s*;',x);assert len(f)==1 and re.sub(r'[\s()]','',f[0])=='A',(p,f)
 directions=re.findall(r'\bdirection\s*:\s*([^;]+);',x)
 assert len(directions)==1 and directions[0].strip().strip(chr(34))=='output',(p,directions)
 assert not re.search(r'\b(?:ff|latch|statetable)\s*\(',c),(p,'unexpected state')
 rows.append({'path':str(p),'sha256':hashlib.sha256(raw).hexdigest(),'cell':'sg13g2_dlygate4sd3_1','function':f[0]})
assert rows,'No frozen delay Liberty models found'
for corner in ['slow','typ','fast']:assert any(corner in x['path'] for x in rows),corner
pathlib.Path('out').mkdir(exist_ok=True);pathlib.Path('out/rx6-hold-liberty-identity.json').write_text(json.dumps({'checked_models':rows,'scope':'Boolean identity only; fresh all-corner physical timing required','production_accepted':False},indent=2))
print('Verified noninverting delay cell in',len(rows),'Liberty models')
