"""Resume only independent publication; never adopt or signal the PLL native."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import shutil
import subprocess

R = Path.cwd()
B = Path(__file__).resolve().parent

def pin(path):
    path = Path(path)
    with path.open('rb') as stream:
        return dict(bytes=path.stat().st_size, sha256=hashlib.file_digest(stream, 'sha256').hexdigest())

def require(condition, message):
    if not condition:
        raise ValueError(message)

policy = json.loads((B / 'policy.json').read_text())
require(Path('/proc/sys/kernel/random/boot_id').read_text().strip() == policy['boot_id'], 'Exact boot')
for path, expected in policy['pins'].items():
    require(pin(path) == expected, 'Exact source or prerequisite: ' + path)
freeze = json.loads(Path(policy['source_freeze']).read_text())
for path, expected in freeze['pins'].items():
    require(pin(path) == expected, 'Exact frozen source/control: ' + path)
peer_path = B.parent / 'source-saved-peer-vco01.json'
peer = json.loads(peer_path.read_text())
require(peer['status'] == 'PASS_SOURCE_SAVED_PUBLISHER_V2_AND_LAUNCH' and not peer['findings'], 'Independent source and launch peer')
require(peer['freeze'] == pin(policy['source_freeze']) and peer['policy'] == pin(B / 'policy.json'), 'Peer binds exact freeze and policy')
spool = Path(policy['spool'])
out = Path(policy['out'])
require(not out.exists(), 'Fresh independent publication directory')
require(pin(spool / 'configuration.json') == policy['configuration'], 'Immutable native spool configuration')
require(not (spool / 'native-terminal-invalid.json').exists() and not (spool / 'terminal-retention-failure.json').exists(), 'No invalid local terminal')
failed = json.loads(Path(policy['failed_publication']).read_text())
require(failed['status'] == 'ERROR_INDEPENDENT_PUBLICATION_LOCAL_SOURCE_RETAINED' and failed['explicit_stop'] is False, 'Retained host-race failure')
for proc in Path('/proc').iterdir():
    if not proc.name.isdigit() or int(proc.name) == os.getpid():
        continue
    try:
        argv = (proc / 'cmdline').read_bytes().split(b'\0')
    except (FileNotFoundError, ProcessLookupError):
        continue
    worker = any(Path(os.fsdecode(arg)).name in ('publish_pcie_local_spool_v1.py', 'publish_pcie_local_spool_v2.py') for arg in argv if arg)
    require(not (worker and os.fsencode(str(spool)) in argv), 'No duplicate independent spool publisher')
require(shutil.disk_usage(B).free >= 1536 * 1024**2, 'Worker cap plus SSD floor available')
release = json.loads(subprocess.check_output(['gh', 'api', 'repos/Melihakbulut221/nssoc/releases/tags/' + policy['tag']], timeout=120))
pages = json.loads(subprocess.check_output(['gh', 'api', f'repos/Melihakbulut221/nssoc/releases/{release["id"]}/assets?per_page=100', '--paginate', '--slurp'], timeout=120))
assets = [asset for page in pages for asset in page]
require(release['tag_name'] == policy['tag'] and len({a['id'] for a in assets}) == len(assets), 'Exact release enumeration')
require(len(assets) + 515 <= 1000, 'Conservative remaining release asset headroom')
# All previously published parts are fully reconciled and downloaded afresh by
# the unchanged V4. No seed adoption, prefix skipping, clobber or native replay.
command = ['taskset', '-c', '14', str(R / 'hw/soc/tools/cocotb-venv/bin/python'),
           str(R / 'scripts/publish_pcie_local_spool_v2.py'), '--spool', str(spool),
           '--out', str(out), '--configuration-sha', policy['configuration']['sha256']]
env = {k: v for k, v in os.environ.items() if k not in ('PYTHONPATH', 'PYTHONHOME', 'PYTHONEXECUTABLE', 'PYTHONOPTIMIZE', 'LD_PRELOAD')}
env['PYTHONDONTWRITEBYTECODE'] = '1'
record = dict(utc=datetime.datetime.now(datetime.UTC).isoformat(), policy=pin(B / 'policy.json'),
              source_peer=pin(peer_path), source=pin(__file__), boot_id=policy['boot_id'], command=command,
              release_id=release['id'], observed_assets=len(assets), atomic_asset_reservation=False,
              native_signals_or_adoption=False, reused_receipts=False)
with (B / 'launch-once.json').open('x') as stream:
    json.dump(record, stream, indent=2)
with (B / 'publication.log').open('x') as log:
    child = subprocess.Popen(command, cwd=R, env=env, stdin=subprocess.DEVNULL, stdout=log,
                             stderr=subprocess.STDOUT, start_new_session=True, close_fds=True)
fields = (Path('/proc') / str(child.pid) / 'stat').read_text().rsplit(') ', 1)[1].split()
record.update(status='DETACHED_PUBLISHER_V2_LAUNCHED_ACTUAL_PROGRESS_REQUIRED',
              controller=dict(pid=child.pid, start_ticks=fields[19], process_group=int(fields[2])))
(B / 'detached-receipt.json').write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps(record))
