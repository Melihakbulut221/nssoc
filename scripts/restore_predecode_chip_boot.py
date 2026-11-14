import subprocess,os
assert os.environ.get('GITHUB_ACTIONS')=='true'
import hashlib,json,pathlib,tarfile,zipfile
P=pathlib.Path
r=json.loads(subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/actions/runs/43651528850']))
assert r['status']=='completed' and r['conclusion']=='success' and r['head_sha']=='790a01e745ffa2a6b4b6db8e23a569749ddf06f5'

assert hashlib.sha256(P('source.zip').read_bytes()).hexdigest()=='dcd55025a9b50aa0e0a949cf7515f3f02057fbcdce2fea229bb84afa0b2b8145'
assert hashlib.sha256(P('mapping.zip').read_bytes()).hexdigest()=='05bdb7b2d6345c7010ea5ededb39aaa8c2cfc319ae05849a23d60914de31ad1e'
with zipfile.ZipFile('mapping.zip') as z:report=json.loads(z.read('mapping.json'))
assert report['source_head']=='790a01e745ffa2a6b4b6db8e23a569749ddf06f5' and report['registered_bit_count']==26
assert report['rx_cursor_local_reset_enabled']
assert report['inputs']['hw/soc/rtl/pcie/soc_pcie_rx_credit.v']=='6e8736695b6fe059716fd90b5b8d969ca80a326f6c3a4705325bb5b7ec8831c0'
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
P('out').mkdir(exist_ok=True);P('out/source-binding.json').write_text(json.dumps({'source_run':43651528850,'source_head':report['source_head'],'authenticated_files':len(seen),'netlist_sha256':report['outputs']['synthesis/soc_top.netlist.v'],'accepted':False},indent=2))
