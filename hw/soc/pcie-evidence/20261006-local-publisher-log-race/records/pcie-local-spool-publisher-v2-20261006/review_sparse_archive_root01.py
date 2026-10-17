"""Full logical readback via bounded LZMAFile reads, including sparse fixtures."""
from pathlib import Path
import hashlib
import json
import lzma
import resource
import tarfile
import time

B = Path(__file__).resolve().parent
F = B / 'finite01'
def pin(p):
    p = Path(p)
    with p.open('rb') as stream:
        return dict(bytes=p.stat().st_size, sha256=hashlib.file_digest(stream, 'sha256').hexdigest())

archive = F / 'pcie-local-spool-publisher-v2-controls-20261006.tar.xz'
before = pin(archive)
manifest = json.loads((F / 'members.json').read_text())
expected = {name: {k: row[k] for k in ('bytes', 'sha256')} for name, row in manifest['files'].items()}
expected['members.json'] = pin(F / 'members.json')
seen = set()
total = 0
start = time.monotonic()
with lzma.open(archive, 'rb') as decoded:
    with tarfile.open(fileobj=decoded, mode='r|', bufsize=1024**2) as tar:
        for member in tar:
            assert member.isfile() and member.name not in seen
            stream = tar.extractfile(member)
            h = hashlib.sha256()
            size = 0
            while chunk := stream.read(1024**2):
                size += len(chunk)
                h.update(chunk)
            assert dict(bytes=size, sha256=h.hexdigest()) == expected[member.name]
            assert member.size == size
            total += size
            seen.add(member.name)
    # Consume through the compressed stream's true EOF/CRC, not merely tar EOF.
    while tail := decoded.read(1024**2):
        assert not any(tail), 'Only conventional tar zero padding follows members'
assert seen == set(expected) and before == pin(archive)
record = dict(status='PASS_FULL_SPARSE_FIXTURE_ARCHIVE_STREAM_READBACK', archive=before,
              members=len(seen), logical_bytes=total, elapsed_seconds=time.monotonic()-start,
              peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
              method=pin(__file__), runtime_tarfile=pin(tarfile.__file__),
              runtime_lzma=pin(lzma.__file__),
              scope='Every declared logical byte, including actual sparse-capacity fixture zeros, is read and hashed. No active native or publisher process interaction; original sealer remains untouched.')
(B / 'sparse-archive-readback-root01.json').write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps(record))
