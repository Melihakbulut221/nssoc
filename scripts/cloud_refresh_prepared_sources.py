# SPDX-License-Identifier: Apache-2.0
"""Regenerate current prepared-source evidence without editing historical receipts."""
import os,sys,json,hashlib,subprocess,tarfile,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'prepared-source-refresh';OUT.mkdir()
DERIVED=OUT/'derived';DERIVED.mkdir()
r=dict(source_head=os.environ.get('GITHUB_SHA'),status='RUNNING',accepted=False,full_phy_accepted=False)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save():(DERIVED/'result.json').write_text(json.dumps(r,indent=2)+'\n')
def command(argv,name):
 with (OUT/(name+'.log')).open('w')as f:subprocess.run(argv,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,check=True)
try:
 assert os.environ.get('GITHUB_ACTIONS')=='true' and os.environ.get('RUNNER_ENVIRONMENT')=='github-hosted'
 assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()==r['source_head']
 tracked=subprocess.check_output(['git','ls-files','-z']).decode().split('\0');protected={f:sha(ROOT/f)for f in tracked if f and (ROOT/f).is_file()}
 command(['make','soc-rtl-prepare','SOC_INTERFACE_PROFILE=full','PYTHON=python3','INTERFACE_PYTHON=python3'],'prepare')
 replay=OUT/'ibex-replay'
 command(['bash','hw/soc/flow/sv2v_ibex.sh','hw/soc/ext/ibex',str(replay),'hw/soc/tools/sv2v-Linux/sv2v'],'ibex-replay')
 sys.path.insert(0,str(ROOT/'hw/soc/flow'))
 import prepare_interfaces
 scratch=OUT/'interface-replay';scratch.mkdir();(scratch/'ext').symlink_to(ROOT/'hw/soc/ext',target_is_directory=True)
 prepare_interfaces.SOC=scratch
 prepare_interfaces.prepare('base');prepare_interfaces.prepare('full')
 sys.path.insert(0,str(ROOT/'scripts'))
 from collect_prepared_sources import collect
 package=OUT/'package';package.mkdir()
 metadata=package/'prepared-sources-current-20261115.json'
 collect(replay,scratch/'gen',metadata)
 record=json.loads(metadata.read_text());assert record['replays_byte_identical']
 assert record['transform_sha256']['hw/soc/flow/adapt_eth_mbist.py']==sha(ROOT/'hw/soc/flow/adapt_eth_mbist.py')
 archive=package/record['archive']['file'];assert sha(archive)==record['archive']['sha256']
 with tarfile.open(archive)as t:
  members=t.getmembers();assert len(members)==len(record['files']) and len({m.name for m in members})==len(members)
  assert {m.name for m in members}==set(record['files'])
  for member in members:
   assert member.isfile() and not Path(member.name).is_absolute() and '..'not in Path(member.name).parts
   raw=t.extractfile(member).read();entry=record['files'][member.name]
   assert len(raw)==entry['bytes'] and hashlib.sha256(raw).hexdigest()==entry['sha256']
   assert raw==(ROOT/member.name).read_bytes()
 assert all(sha(ROOT/f)==h for f,h in protected.items())
 assert not subprocess.check_output(['git','diff','--name-only'],text=True).strip()
 (DERIVED/metadata.name).write_bytes(metadata.read_bytes())
 notice=package/record['component_notices']['file'];assert sha(notice)==record['component_notices']['sha256']
 (DERIVED/notice.name).write_bytes(notice.read_bytes())
 r.update(status='REPLAYED_CURRENT_DEPENDENCIES_NOT_YET_PUBLISHED_OR_INTEGRATION_TESTED',file_count=len(record['files']),sources_unchanged=True,archive_sha256=sha(archive),metadata_sha256=sha(metadata),protected_inputs=protected)
except BaseException:
 r.update(status='FAIL_OR_ERROR',traceback=traceback.format_exc());raise
finally:
 for log in OUT.glob('*.log'):(DERIVED/log.name).write_bytes(log.read_bytes())
 r['outputs']={str(f.relative_to(OUT)):sha(f)for f in OUT.rglob('*')if f.is_file()and f!=DERIVED/'result.json'}
 save()
