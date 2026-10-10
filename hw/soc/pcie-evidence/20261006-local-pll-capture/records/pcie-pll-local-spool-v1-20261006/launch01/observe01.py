"""Read-only live observation; no process adoption, signals, or native imports."""
from pathlib import Path
import datetime
import hashlib
import json
import lzma
import os
import re
import shutil
import struct

B = Path(__file__).resolve().parent
P = B.parent
policy = json.loads((B / 'policy.json').read_text())


def pin(path):
    path = Path(path)
    with path.open('rb') as stream:
        return dict(bytes=path.stat().st_size,
                    sha256=hashlib.file_digest(stream, 'sha256').hexdigest())


def observe(identity):
    pid = identity['pid']
    path = Path('/proc') / str(pid)
    try:
        fields = (path / 'stat').read_text().rsplit(') ', 1)[1].split()
        assert fields[19] == str(identity['start_ticks']), 'Birth changed'
        return dict(pid=pid, start_ticks=fields[19], state=fields[0],
                    parent_pid=int(fields[1]), process_group=int(fields[2]),
                    affinity=sorted(os.sched_getaffinity(pid)),
                    command=(path / 'cmdline').read_bytes().split(b'\0')[:-1],
                    cpu_ticks=int(fields[11]) + int(fields[12]))
    except FileNotFoundError:
        return dict(pid=pid, start_ticks=str(identity['start_ticks']), absent=True)


boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
assert boot == policy['boot_id']
native = Path(policy['native_out'])
spool = Path(policy['spool_out'])
publication = Path(policy['publisher_out'])
native_launch = json.loads((B / 'detached-launch-receipt.json').read_text())
worker_launch = json.loads((B / 'publication-detached-receipt.json').read_text())
owner = json.loads((native / 'owned-processes.json').read_text())
local_bytes = (spool / 'parts.json').read_bytes()
local = json.loads(local_bytes)
public_bytes = (publication / 'publication.json').read_bytes()
public = json.loads(public_bytes)
with (native / 'run.log').open('rb') as stream:
    stream.seek(max(0, os.fstat(stream.fileno()).st_size - 65536))
    tail = stream.read()
references = re.findall(rb'Reference value\s*:\s*([0-9.eE+\-]+)', tail)
first = local['parts'][0]
part = spool / 'committed' / f'{first["index"]:05d}' / first['name']
assert pin(part) == {key: first[key] for key in ('bytes', 'sha256')}
raw = lzma.decompress(part.read_bytes())
assert len(raw) == first['uncompressed_bytes']
assert hashlib.sha256(raw).hexdigest() == first['uncompressed_sha256']
row_bytes = len(raw) // first['rows']
assert row_bytes * first['rows'] == len(raw)
times = [struct.unpack_from('<d', raw, offset)[0]
         for offset in range(0, len(raw), row_bytes)]
assert all(left < right for left, right in zip(times, times[1:]))
assert public['assets'] and public['assets'][0]['row'] == first
receipt_path = Path(public['assets'][0]['receipt'])
assert pin(receipt_path) == public['assets'][0]['receipt_pin']
receipt = json.loads(receipt_path.read_text())
assert receipt['status'] == 'PASS_IMMUTABLE_RELEASE_ROUNDTRIPS'
assert receipt['assets'][0] == public['assets'][0]['asset']
assert receipt['assets'][0]['authenticated_roundtrip'] is True
assert receipt['assets'][0]['anonymous_roundtrip'] is True
reservation = spool / 'reservation.bin'
st = reservation.stat()
record = dict(
    status='OBSERVED_RUNNING_LOCAL_PLL_AND_SEPARATE_PUBLICATION_NOT_COMPLETION',
    utc=datetime.datetime.now(datetime.UTC).isoformat(), boot_id=boot,
    policy=pin(B / 'policy.json'), support_peer=pin(B / 'source-peer-vco01.json'),
    aggregate_peer=pin(P / 'source-saved-peer-root02.json'), observer=pin(__file__),
    producer=observe(native_launch['controller']),
    native=[observe(item['identity']) for item in owner['processes']
            if item['kind'] == 'native'],
    worker=observe(worker_launch['controller']),
    native_status=json.loads((native / 'result.json').read_text())['status'],
    native_owner_status=owner['status'],
    last_actual_native_reference_seconds=float(references[-1]),
    local_status=local['status'], local_parts=len(local['parts']),
    local_committed_rows=local['committed_rows'],
    local_snapshot=dict(bytes=len(local_bytes), sha256=hashlib.sha256(local_bytes).hexdigest()),
    publication_status=public['status'], public_parts=len(public['assets']),
    public_attempts=len(public['attempts']),
    publication_snapshot=dict(bytes=len(public_bytes), sha256=hashlib.sha256(public_bytes).hexdigest()),
    first_part=dict(row=first, receipt=pin(receipt_path),
                    asset=receipt['assets'][0], raw_rows=len(times),
                    first_time_seconds=times[0], last_time_seconds=times[-1],
                    raw_sha256=hashlib.sha256(raw).hexdigest()),
    reservation=dict(path=str(reservation), logical_bytes=st.st_size,
                     allocated_bytes=st.st_blocks * 512),
    native_directory=str(native), local_directory=str(spool),
    publication_directory=str(publication),
    RAM_free=shutil.disk_usage('/dev/shm').free,
    SSD_free=shutil.disk_usage(spool).free,
    scope='Read-only observations at separate instants, not one atomic global snapshot. '
          'Source and criteria unchanged; fresh time-zero native. Local/public/physical '
          'completion remain distinct. No EDA execution, network request, or signal.')
stamp = datetime.datetime.now(datetime.UTC).strftime('%Y%m%dT%H%M%S%fZ')
target = B / f'observation-{stamp}.json'
data = (json.dumps(record, indent=2,
                   default=lambda value: value.decode() if isinstance(value, bytes) else value) + '\n').encode()
with target.open('xb') as stream:
    stream.write(data)
    stream.flush()
    os.fsync(stream.fileno())
checkpoint = dict(status=record['status'], observation=dict(path=str(target), **pin(target)),
                  utc=record['utc'], policy=pin(B / 'policy.json'),
                  native_directory=str(native), local_directory=str(spool),
                  publication_directory=str(publication),
                  next_action='Read current exact births and local/public progress; never launch duplicate. '
                              'If terminal, independently verify canonical lossless capture, native terminal '
                              'retention, numerical results and full public/replay evidence separately.')
temporary = B / f'.active-checkpoint-{stamp}.tmp'
with temporary.open('xb') as stream:
    stream.write((json.dumps(checkpoint, indent=2) + '\n').encode())
    stream.flush()
    os.fsync(stream.fileno())
os.replace(temporary, B / 'active-checkpoint.json')
fd = os.open(B, os.O_RDONLY | os.O_DIRECTORY)
try:
    os.fsync(fd)
finally:
    os.close(fd)
print(json.dumps(dict(path=str(target), **pin(target),
                      producer=record['producer']['pid'], native=record['native'],
                      worker=record['worker']['pid'],
                      seconds=record['last_actual_native_reference_seconds'],
                      local_parts=record['local_parts'], public_parts=record['public_parts']),
                 default=lambda value: value.decode() if isinstance(value, bytes) else value))
