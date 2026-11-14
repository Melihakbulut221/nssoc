import subprocess,os
assert os.environ.get('GITHUB_ACTIONS')=='true'
import hashlib,json,pathlib,tarfile,zipfile
P=pathlib.Path
r=json.loads(subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/actions/runs/43638771489']))
assert r['status']=='completed' and r['conclusion']=='success' and r['head_sha']=='e92350d314fd8c04c9c06f2aa7d198f02b000cd1'

assert hashlib.sha256(P('source.zip').read_bytes()).hexdigest()=='5b92b8ded91a9d8b2d0042457d09f8473dd99064cb7a509644c08d47fe6f1586'
assert hashlib.sha256(P('mapping.zip').read_bytes()).hexdigest()=='716388bae108cddc07099c7dc0de28e058a9c0f888f6cb2b04c5a0fd75baa334'
with zipfile.ZipFile('mapping.zip') as z:report=json.loads(z.read('mapping.json'))
assert report['source_head']=='e92350d314fd8c04c9c06f2aa7d198f02b000cd1' and report['registered_bit_count']==26
assert report['rx_cursor_local_reset_enabled']
assert report['crc_select_enabled'] and len(report['cached_eop_register'])==1
assert len(report['outputs'])==63
assert report['status']=='MAPPED_RX_CURSOR_CRC_SELECT_EOP_CHIP_REQUIRES_GATE_BOOT_AND_PHYSICAL_IMPLEMENTATION'
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
P('out').mkdir(exist_ok=True);P('out/source-binding.json').write_text(json.dumps({'source_run':43638771489,'source_head':report['source_head'],'authenticated_files':len(seen),'netlist_sha256':report['outputs']['synthesis/soc_top.netlist.v'],'accepted':False},indent=2))
