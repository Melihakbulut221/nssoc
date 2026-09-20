# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Resolve a run's small evidence: the live run tree first, the record second.

WHY THIS EXISTS. Every `runs/` tree is gitignored, for the good reason
that a 113 MB GDS does not belong in git. The consequence was that on a
clone a quarter of the suite skipped and no layout claim could be
checked at all. `scripts/collect_evidence.py` now commits the two small
files that carry most of the checkable numbers, and this is what the
tests read them through.

THE ORDER MATTERS AND SO DOES SAYING WHICH ONE ANSWERED. A live run
tree is the real thing and wins. The committed record is a record: it
proves what the run reported, not that the run can be reproduced here.
`source` says which was used so a test can report *checked against the
recorded artefact* rather than *checked*, which is a weaker claim and
deliberately so.

WHEN BOTH ARE PRESENT THEY MUST AGREE. A committed record that has
drifted from the tree it was taken from is worse than no record, so
`load` compares them and raises. `scripts/collect_evidence.py --check`
is the same comparison across every run at once.

WHAT IT DOES NOT DO. It does not make a netlist, a DEF or a GDS
appear. A test that needs one still skips, and `skip_reason` gives it a
message that names the digest in `docs/80-artefact-digests.tsv` the
absent file would have to match.
"""

import csv
import hashlib
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
RECORDED = ROOT / "docs" / "evidence"

LIVE, RECORD = "run tree", "recorded evidence"


class Evidence:
    """One JSON artefact, with where it came from."""

    def __init__(self, data, source, path):
        self.data = data
        self.source = source
        self.path = path

    @property
    def is_live(self):
        return self.source == LIVE

    def qualify(self, claim):
        """`claim`, phrased for whichever source answered."""
        if self.is_live:
            return "%s (checked against %s)" % (claim, self.path)
        return ("%s (checked against the RECORDED artefact %s, not against "
                "a run: this tree has no %s)"
                % (claim, self.path.relative_to(ROOT), self.path.name))

    def __contains__(self, key):
        return key in self.data

    def __getitem__(self, key):
        return self.data[key]

    def get(self, key, default=None):
        return self.data.get(key, default)

    def keys(self):
        return self.data.keys()

    def __iter__(self):
        return iter(self.data)


def _digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def recorded_path(tag, name):
    return RECORDED / tag / name


def load(tag, name, live_path=None):
    """Evidence for `tag`/`name`, or None if neither source has it.

    `live_path` is where the run tree would keep it. When both exist
    they are compared, because a record that has drifted from its run
    is a record of nothing.
    """
    rec = recorded_path(tag, name)
    live = pathlib.Path(live_path) if live_path else None
    if live is not None and live.is_file():
        if rec.is_file() and _digest(rec) != _digest(live):
            raise AssertionError(
                "%s differs from %s. The committed record and the run tree "
                "disagree; re-run scripts/collect_evidence.py if the tree is "
                "the newer one, and read the diff before you do."
                % (rec.relative_to(ROOT), live))
        return Evidence(json.loads(live.read_text(encoding="utf-8")),
                        LIVE, live)
    if rec.is_file():
        return Evidence(json.loads(rec.read_text(encoding="utf-8")),
                        RECORD, rec)
    return None


def metrics(tag, run_dir=None):
    live = pathlib.Path(run_dir) / "final" / "metrics.json" if run_dir else None
    return load(tag, "metrics.json", live)


def resolved(tag, run_dir=None):
    live = pathlib.Path(run_dir) / "resolved.json" if run_dir else None
    return load(tag, "resolved.json", live)


def skip_reason(tag, what, regenerate=None):
    """A skip message that names what is absent and what would satisfy it."""
    msg = ("%s for run %r is not in this tree. Run outputs are gitignored, "
           "and this file is too large to record: docs/evidence/ carries "
           "metrics.json and resolved.json only."
           % (what, tag))
    digests = ROOT / "docs" / "80-artefact-digests.tsv"
    if digests.is_file():
        msg += (" If it is regenerated it must match its row in "
                "docs/80-artefact-digests.tsv.")
    if regenerate:
        msg += " Regenerate with: %s" % regenerate
    return msg


def artifact_identity(path):
    """Name the exact retained bytes, without substituting another run's hash.

    Rebuilding current RTL may legitimately produce different bytes. The digest
    identifies the historical artifact to restore; it is not a reproducibility
    assertion about a newly generated artifact.
    """
    path = pathlib.Path(path)
    if path.is_absolute():
        path = path.relative_to(ROOT)
    relative = path.as_posix()
    manifest = ROOT / "docs/80-artefact-digests.tsv"
    rows = csv.DictReader(
        (line for line in manifest.read_text().splitlines()
         if line.strip() and not line.startswith("#")), delimiter="\t")
    matches = [row for row in rows if row["path"] == relative]
    if not matches:
        return (f" No historical SHA-256 is recorded for {relative} in "
                "docs/80-artefact-digests.tsv; another artifact's digest "
                "cannot establish its identity.")
    identities = {(row["sha256"], row["bytes"]) for row in matches}
    if len(identities) != 1:
        raise AssertionError(f"Conflicting recorded identities for {relative}")
    digest, size = identities.pop()
    return (f" Historical artifact: {relative}; SHA-256 {digest}; {size} bytes "
            "(docs/80-artefact-digests.tsv). Restore these bytes to recheck "
            "that historical result; a new build is a separate measurement.")


def recorded_netlist(metadata, output_dir, live_root=ROOT):
    """Unpack a hash-pinned netlist snapshot; compare its exact live run if present.

    This supplies the actual graph to the existing census and mutation tests.
    It is a recorded design, not a synthesis or physical verdict at current HEAD.
    """
    import gzip
    metadata = pathlib.Path(metadata)
    record = json.loads(metadata.read_text())
    archive_name = record["archive"]["file"]
    assert pathlib.Path(archive_name).name == archive_name, "Unsafe archive path"
    archive = metadata.parent / archive_name
    assert archive.resolve().is_relative_to(metadata.parent.resolve()), "Archive symlink escapes evidence"
    assert archive.stat().st_size == record["archive"]["bytes"], "Archive size mismatch"
    assert _digest(archive) == record["archive"]["sha256"], "Archive digest mismatch"
    notice = record["component_notices"]
    assert pathlib.Path(notice["file"]).name == notice["file"], "Unsafe notice path"
    assert _digest(metadata.parent / notice["file"]) == notice["sha256"], "Component notices mismatch"
    size = record["netlist"]["bytes"]
    assert isinstance(size, int) and 0 < size <= 64 * 1024 * 1024, "Invalid netlist size"
    with gzip.open(archive, "rb") as stream:
        data = stream.read(size + 1)
    assert len(data) == size, "Decompressed size mismatch"
    assert hashlib.sha256(data).hexdigest() == record["netlist"]["sha256"], "Netlist digest mismatch"
    original = pathlib.PurePosixPath(record["netlist"]["original_path"])
    assert not original.is_absolute() and ".." not in original.parts, "Unsafe live path"
    live = pathlib.Path(live_root) / original
    if live.is_file():
        assert _digest(live) == record["netlist"]["sha256"], "Live run differs from recorded netlist"
    output = pathlib.Path(output_dir) / "soc_top.nl.v"
    with output.open("xb") as stream:
        stream.write(data)
    return output


def recorded_bundle(metadata, output_dir, live_root=ROOT):
    """Restore selected original files into an empty scratch root, not a live run.

    Validate the complete archive before writing. Original files present in the
    checkout must agree with their recorded identities. No tar extraction API,
    symlinks, extra members, oversized payloads or path traversal is accepted.
    """
    import tarfile
    metadata, output_dir = pathlib.Path(metadata), pathlib.Path(output_dir)
    record = json.loads(metadata.read_text())

    def relative(name):
        path = pathlib.PurePosixPath(name)
        assert name not in ('', '.') and not path.is_absolute() and '..' not in path.parts, 'Unsafe bundle path'
        assert str(path) == name and '\\' not in name, 'Noncanonical bundle path'
        return path

    archive_name = record['archive']['file']
    assert relative(archive_name).name == archive_name, 'Unsafe archive path'
    archive = metadata.parent / archive_name
    assert archive.resolve().parent == metadata.parent.resolve(), 'Archive symlink escape'
    assert archive.stat().st_size == record['archive']['bytes'], 'Archive size mismatch'
    assert _digest(archive) == record['archive']['sha256'], 'Archive digest mismatch'
    notice = record['component_notices']
    assert relative(notice['file']).name == notice['file'], 'Unsafe notice path'
    assert (metadata.parent / notice['file']).resolve().parent == metadata.parent.resolve(), 'Notice symlink escape'
    assert _digest(metadata.parent / notice['file']) == notice['sha256'], 'Notice mismatch'
    directories, files = record['directories'], record['files']
    assert len(set(directories)) == len(directories), 'Repeated directory'
    assert not set(directories) & files.keys(), 'File/directory collision'
    for name in directories + list(files):
        path = relative(name)
        assert not any(str(parent) in files for parent in path.parents), 'File used as directory'
    assert sum(row['bytes'] for row in files.values()) <= 256 * 1024**2, 'Bundle too large'
    for name, row in files.items():
        assert isinstance(row['bytes'], int) and 0 <= row['bytes'] <= 64 * 1024**2, 'Invalid file size'
        live = pathlib.Path(live_root) / name
        if live.is_file():
            assert _digest(live) == row['sha256'], 'Live artifact differs: ' + name
    data, seen = {}, set()
    with tarfile.open(archive, 'r:gz') as stream:
        for member in stream:
            name = member.name
            relative(name)
            assert name not in seen, 'Duplicate archive member'
            seen.add(name)
            if name in directories:
                assert member.isdir(), 'Expected directory'
                continue
            assert name in files and member.isfile(), 'Unexpected member or link'
            row = files[name]
            assert member.size == row['bytes'], 'Member size mismatch'
            content = stream.extractfile(member).read(row['bytes'] + 1)
            assert len(content) == row['bytes'], 'Truncated member'
            assert hashlib.sha256(content).hexdigest() == row['sha256'], 'Member digest mismatch'
            data[name] = content
    assert seen == set(directories) | files.keys(), 'Missing archive members'
    assert not output_dir.exists() or not any(output_dir.iterdir()), 'Scratch root must be empty'
    output_dir.mkdir(parents=True, exist_ok=True)
    for name in directories:
        (output_dir / name).mkdir(parents=True, exist_ok=True)
    for name, content in data.items():
        destination = output_dir / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open('xb') as output:
            output.write(content)
    return output_dir
