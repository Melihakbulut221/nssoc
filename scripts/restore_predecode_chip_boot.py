import subprocess,os
assert os.environ.get('GITHUB_ACTIONS')=='true'
import hashlib,json,pathlib,tarfile,zipfile
P=pathlib.Path
r=json.loads(subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/actions/runs/43635824821']))
assert r['status']=='completed' and r['conclusion']=='success' and r['head_sha']=='9339dd6eeda8cf65383c7dc606e0cc752c1d6432'

assert hashlib.sha256(P('source.zip').read_bytes()).hexdigest()=='b92718e6281f3c11a16b9154ba6de8fc661e60e9846c3001f61af1ec1308fac4'
assert hashlib.sha256(P('mapping.zip').read_bytes()).hexdigest()=='bd7755567790c904749b467dcd72d3faa59756e24dcf360726d5188fc32382a9'
with zipfile.ZipFile('mapping.zip') as z:report=json.loads(z.read('mapping.json'))
assert report['source_head']=='9339dd6eeda8cf65383c7dc606e0cc752c1d6432' and report['registered_bit_count']==26
assert report['crc_select_enabled'] and len(report['cached_eop_register'])==1
assert len(report['outputs'])==63
assert report['status']=='MAPPED_CRC_SELECT_EOP_CHIP_REQUIRES_GATE_BOOT_AND_PHYSICAL_IMPLEMENTATION'
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
P('out').mkdir(exist_ok=True);P('out/source-binding.json').write_text(json.dumps({'source_run':43635824821,'source_head':report['source_head'],'authenticated_files':len(seen),'netlist_sha256':report['outputs']['synthesis/soc_top.netlist.v'],'accepted':False},indent=2))
