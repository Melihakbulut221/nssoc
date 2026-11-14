# SPDX-License-Identifier: Apache-2.0
"""Summarize original CDL resistor metadata in cloud, without exporting circuits."""
import pathlib,hashlib,zipfile,tarfile,io,json,re,collections
b=pathlib.Path('native.zip').read_bytes()
assert hashlib.sha256(b).hexdigest()=='1500e77278169018c45451e0fc0d18c0d51bab3a7bb981b15b0e87bda3538654'
z=zipfile.ZipFile(io.BytesIO(b));names=[n for n in z.namelist() if n.endswith('.tgz')];assert len(names)==1
with tarfile.open(fileobj=io.BytesIO(z.read(names[0])),mode='r:gz') as t:
 ms=[m for m in t.getmembers() if m.name.endswith('/RM_IHPSG13_2P_256x16_c2_bm_bist.cdl')];assert len(ms)==1
 raw=t.extractfile(ms[0]).read()
assert hashlib.sha256(raw).hexdigest()=='1b307d5bd84ba57087717c1d1e631959352c6d20a27167b3ed08f637e3d312a8'
lines=[]
for line in raw.decode().splitlines():
 if line.lstrip().startswith('+'):
  assert lines;lines[-1]+=' '+line.lstrip()[1:]
 else:lines.append(line)
counts=collections.Counter();cell=None
for line in lines:
 text=line.strip()
 if text.lower().startswith('.subckt '):cell=text.split()[1]
 if text.lower().startswith('.ends'):cell=None
 if not text or text.startswith('*'):continue
 models=re.findall(r'(?i)\b(?:lvsres|res_metal[1-5]|res_topmetal[12])\b',text)
 if not models:continue
 attrs=dict(re.findall(r'([\w$]+)\s*=\s*([^\s]+)',text))
 markers=re.findall(r'(?i)\b(?:metal[1-5]|topmetal[12]|met[1-5]|layer)\b',text)
 counts[(cell,tuple(models),tuple(sorted(attrs.items())),tuple(markers))]+=1
r={'status':'REFERENCE_METADATA_DIAGNOSTIC_ONLY','cdl_sha256':hashlib.sha256(raw).hexdigest(),'records':[{'cell':k[0],'models':list(k[1]),'attributes':dict(k[2]),'layer_keywords':list(k[3]),'count':v} for k,v in counts.items()],'production_accepted':False}
assert counts
pathlib.Path('out').mkdir();pathlib.Path('out/resistor-metadata.json').write_text(json.dumps(r,indent=2));print(json.dumps({'groups':len(counts),'records':sum(counts.values())}))
