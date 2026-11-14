# SPDX-License-Identifier: Apache-2.0
import pathlib,zipfile,tarfile,hashlib,shutil,os
assert os.environ.get('GITHUB_ACTIONS')=='true'
P=pathlib.Path
h=hashlib.sha256()
with P('native.zip').open('rb') as f:
 for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
assert h.hexdigest()=='d67191c33b2015eb39b097946904044e564990b12fddcd0c6d88f643d9ada340'
P('out/native').mkdir(parents=True);P('out/derived').mkdir()
expected={'native/source.odb':'c9deaebb26a07bf0909c249547156b1a1cb96401c8ccfa3748acff818131d959','native/buf4-legalized-unrouted.odb':'972d9676e2f3af51fda24b2411048b60383e9dfffdb92cd8550a9caf9c53e0b9'}
found=set()
with zipfile.ZipFile('native.zip') as z:
 assert z.namelist()==['retry-buf4-native.tgz']
 with z.open(z.namelist()[0]) as packed,tarfile.open(fileobj=packed,mode='r|gz') as t:
  for m in t:
   if m.name in expected:
    assert m.isfile() and m.name not in found;found.add(m.name)
    path=P('out')/m.name
    with t.extractfile(m) as src,path.open('wb') as dst:shutil.copyfileobj(src,dst)
    assert hashlib.sha256(path.read_bytes()).hexdigest()==expected[m.name]
assert found==set(expected)
