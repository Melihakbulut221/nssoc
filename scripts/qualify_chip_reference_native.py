# SPDX-License-Identifier: Apache-2.0
"""Qualify full independent reference using frozen native macro LVS reader."""
import pathlib,hashlib,json,zipfile,tarfile,subprocess,os,io
P=pathlib.Path;out=P('out');out.mkdir(exist_ok=True);(out/'derived').mkdir(exist_ok=True)
def sha(p):return hashlib.sha256(P(p).read_bytes()).hexdigest()
for archive,expected,inner,destination in [
 ('macro.zip','1b536d31758f4abf1fb7af4700a59fd64d891e41044ec1f1230da02b84a324c1','namespaced-native.tgz',out),
 ('reference.zip','894aa48ad4ee2c0f6e43724f1a88f20b278128e49d27b3584148759317c5c0b9','streamout-native.tgz',P('.'))]:
 assert sha(archive)==expected
 with zipfile.ZipFile(archive) as z:
  assert z.namelist()==[inner]
  with tarfile.open(fileobj=io.BytesIO(z.read(inner)),mode='r:gz') as t:
   for m in t.getmembers():assert not P(m.name).is_absolute() and '..' not in P(m.name).parts and (m.isfile() or m.isdir())
   t.extractall(destination,filter='data')
assert sha('/usr/bin/klayout')=='288ed7a513436fac79255686914ff71b1d351fd79bd98f2eb6f9fecd14e149f7'
ref=P('hw/soc/out/namespaced-streamout/pinmap-native/soc_top-full-transistor.cdl').resolve()
assert sha(ref)=='523438b6014557b86ee7d438f95ddbfaabb76f390265283fcb844c233fcb8aa4'
cmd=json.loads((out/'native/effective-command.json').read_text());assert cmd[:4]==['/usr/bin/klayout','-b','-zz','-r']
deck=P(cmd[4]);assert deck.is_relative_to(P.cwd()/'out/native') and deck.is_file()
text=deck.read_text();anchor='# Instantiate a writer using the new delegate';assert text.count(anchor)==1
(out/'derived/dp-lvs-deck-source.txt').write_text(text)
assert sha('sp-macro.zip')=='13b66b4e31ad144bd9d47e5a209845027b76d23ff3dc1183d94a45de104bf4f3'
with zipfile.ZipFile('sp-macro.zip') as z:
 assert z.namelist()==['namespaced-native.tgz']
 with tarfile.open(fileobj=io.BytesIO(z.read('namespaced-native.tgz')),mode='r:gz') as t:
  entries=[m for m in t.getmembers() if m.isfile() and m.name.endswith('/lvs/sg13g2.lvs')]
  assert len(entries)==1
  (out/'derived/sp-lvs-deck-source.txt').write_bytes(t.extractfile(entries[0]).read())

insertion=P('scripts/check_chip_reference_native.rb').read_text()+'\n'
deck.write_text(text.replace(anchor,insertion+anchor,1))
assert deck.read_text().replace(insertion,'',1)==text
indices=[i for i,v in enumerate(cmd) if v.startswith('schematic=')];assert len(indices)==1;cmd[indices[0]]='schematic='+str(ref)
(out/'derived/reader-command.json').write_text(json.dumps({'command':cmd,'original_deck_sha256':hashlib.sha256(text.encode()).hexdigest(),'patched_deck_sha256':sha(deck),'reference_sha256':sha(ref),'scope':'Schematic reader qualification only; no LVS comparison'},indent=2))
env=dict(os.environ);env.pop('GH_TOKEN',None);env.pop('GITHUB_TOKEN',None)
with (out/'derived/reader.log').open('w') as log:r=subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=900)
assert r.returncode==0,r.returncode
result=json.loads((out/'derived/native-reference-reader.json').read_text());assert result['status']=='NATIVE_REFERENCE_READER_PASSED'
assert sha(ref)=='523438b6014557b86ee7d438f95ddbfaabb76f390265283fcb844c233fcb8aa4'
print(json.dumps(result))
