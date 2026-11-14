import hashlib,json,pathlib,tarfile,zipfile
P=pathlib.Path
assert hashlib.sha256(P('source.zip').read_bytes()).hexdigest()=='d32dd9bb9e0cc1d25f34e29cfbec4bb71908bef7bcaaa577327719602dcd3570'
assert hashlib.sha256(P('mapping.zip').read_bytes()).hexdigest()=='58963d3e81c870b90af23181ebb2fb313a995920cc33affc6cb303082b2b0898'
with zipfile.ZipFile('mapping.zip') as z:report=json.loads(z.read('mapping.json'))
assert report['source_head']=='bdd7cc588490425ff98c4718ea8986ecc06a128a' and report['registered_bit_count']==26
assert report['validation_run']==43631950511 and report['validation_head']=='a238c421772e0f1ccd8a8e4ef64e7d5aad1cb894'
assert report['validated_preserved_source_without_resynthesis'] and len(report['cached_eop_register'])==1
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
P('out').mkdir(exist_ok=True);P('out/source-binding.json').write_text(json.dumps({'source_run':43630345267,'source_head':report['source_head'],'authenticated_files':len(seen),'netlist_sha256':report['outputs']['synthesis/soc_top.netlist.v'],'accepted':False},indent=2))
