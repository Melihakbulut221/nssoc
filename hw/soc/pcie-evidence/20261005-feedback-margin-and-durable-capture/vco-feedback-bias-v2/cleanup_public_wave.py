# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import hashlib
import json
import sys
import tarfile

B = Path(__file__).resolve().parent
name = sys.argv[1]
assert name in ("06-01", "085-01", "disconnect-01", "modulus-01")
r = json.loads((B / f"release-{name}.json").read_text())
assert r["status"] == "PASS_IMMUTABLE_RELEASE_ROUNDTRIPS"
a = r["assets"][0]
assert a["authenticated_roundtrip"] and a["anonymous_roundtrip"]
cap = B / a["name"]
assert cap.stat().st_size == a["bytes"]
with cap.open("rb") as f:
    assert hashlib.file_digest(f, "sha256").hexdigest() == a["sha256"]
root = Path("/dev/shm/nssoc-vco-v6-feedback-bias-v2-" + name)
target = root / "wave.raw.gz"
member = "native/" + root.name + "/wave.raw.gz"
manifest = json.loads((B / f"members-{name}.json").read_text())
with tarfile.open(cap, "r|xz") as arc:
    seen = {}
    for entry in arc:
        assert entry.isfile()
        seen[entry.name] = dict(bytes=entry.size, sha256=hashlib.file_digest(arc.extractfile(entry), "sha256").hexdigest())
assert seen == manifest
with target.open("rb") as f:
    pin = dict(bytes=target.stat().st_size, sha256=hashlib.file_digest(f, "sha256").hexdigest())
assert pin == manifest[member]
matches = []
for proc in Path("/proc").glob("[0-9]*"):
    try:
        if (proc / "cwd").resolve() == root:
            matches.append(str(proc / "cwd"))
        for fd in (proc / "fd").iterdir():
            try:
                if fd.resolve() == target:
                    matches.append(str(fd))
            except (OSError, RuntimeError):
                pass
    except (OSError, RuntimeError):
        pass
assert not matches
record = dict(status="EXACT_CLOSED_PUBLIC_DUPLICATE", path=str(target), member=member,
              removed=pin, archive=a, full_members_rehashed=len(seen), live_fd_cwd_matches=matches)
p = B / f"cleanup-{name}.json"
p.write_text(json.dumps(record, indent=2) + "\n")
target.unlink()
record["deleted"] = True
p.write_text(json.dumps(record, indent=2) + "\n")
print(pin["bytes"])
