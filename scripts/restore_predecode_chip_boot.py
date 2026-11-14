import hashlib,json,pathlib,tarfile,zipfile
P=pathlib.Path
assert hashlib.sha256(P('source.zip').read_bytes()).hexdigest()=='c6848d124c65c6aae6af7ee70deb7b516d0a06e91886a0d4945ea12ce4645615'
assert hashlib.sha256(P('mapping.zip').read_bytes()).hexdigest()=='f11becfb6e2ab79646a58d29285409fc1dc1c6d30acf1501836e5a424dc3f695'
with zipfile.ZipFile('mapping.zip') as z:report=json.loads(z.read('mapping.json'))
assert report['source_head']=='b900da8cc1d57b8b2ce80416b6742c36239afd63' and report['registered_bit_count']==26
with zipfile.ZipFile('source.zip') as z:
 assert z.namelist()==['build.tgz'];z.extract('build.tgz')
root=P('hw/soc/out/corrpre-pcie-mbist-native-boot');seen=set()
with tarfile.open('build.tgz') as tar:
 for m in tar:
  path=P(m.name);assert not path.is_absolute() and '..' not in path.parts
  assert path==root or root in path.parents
  if m.isdir():continue
  assert m.isfile();rel=str(path.relative_to(root));assert rel in report['outputs'] and rel not in seen;seen.add(rel)
  data=tar.extractfile(m).read();assert hashlib.sha256(data).hexdigest()==report['outputs'][rel]
  assert not path.exists();path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
assert seen==set(report['outputs'])
for f,h in report['inputs'].items():assert hashlib.sha256(P(f).read_bytes()).hexdigest()==h
P('out').mkdir(exist_ok=True);P('out/source-binding.json').write_text(json.dumps({'source_run':43618915765,'source_head':report['source_head'],'authenticated_files':len(seen),'netlist_sha256':report['outputs']['synthesis/soc_top.netlist.v'],'accepted':False},indent=2))
