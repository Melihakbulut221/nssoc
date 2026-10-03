# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""The recorded evidence is complete, is real JSON, and has not drifted.

WHY THIS GUARD EXISTS. `docs/evidence/` is the answer to the review's
largest finding: every `runs/` tree is gitignored, so on a clone no
layout claim could be checked and a quarter of the suite skipped. The
two small files per run that carry the checkable numbers are now
committed, and the tests read them through `sw/tests/evidence.py`.

That introduces a new way to be wrong: a record that has drifted from
the run it claims to record. On a machine with the run trees this
compares them and fails on any difference. On a machine without them --
a clone, the mirror, CI -- there is nothing to compare against and the
comparison honestly skips, while the completeness and shape checks
still run.

CORRECTED 2026-09-19: the former paragraph said these tracked records
should not be in docs/80-artefact-digests.tsv. Review F6 explicitly
requires them there. They are now covered by its docs-evidence group;
test_artefact_digests.py checks their path set, size and SHA-256. This
file independently compares the records with live runs where available.
"""

import json
import pathlib

import pytest

import evidence as ev

ROOT = pathlib.Path(__file__).resolve().parents[2]
COLLECTOR = ROOT / "scripts" / "collect_evidence.py"


def _runs():
    if not COLLECTOR.is_file():
        return {}
    import importlib.util
    spec = importlib.util.spec_from_file_location("collect_evidence", COLLECTOR)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return dict(mod.RUNS)


RUNS = _runs()
NAMES = ("metrics.json", "resolved.json")
CASES = [(tag, name) for tag in sorted(RUNS) for name in NAMES]


def test_missing_artifact_identity_never_borrows_a_different_runs_digest(
        tmp_path, monkeypatch):
    """Same basename is insufficient evidence, even with identical run suffixes."""
    monkeypatch.setattr(ev, "ROOT", tmp_path)
    manifest = tmp_path / "docs/80-artefact-digests.tsv"
    manifest.parent.mkdir()
    digest = "a" * 64
    manifest.write_text(
        "# recorded identities\npath\tbytes\tsha256\n"
        f"runs/original/final/nl/soc_top.nl.v\t12\t{digest}\n")
    relative = "runs/original/final/nl/soc_top.nl.v"
    message = ev.artifact_identity(tmp_path / relative)
    assert digest in message and relative in message and "12 bytes" in message
    assert "new build is a separate measurement" in message
    for different in ("runs/changed/final/nl/soc_top.nl.v",
                      "runs/original-copy/final/nl/soc_top.nl.v"):
        message = ev.artifact_identity(different)
        assert digest not in message
        assert "No historical SHA-256" in message and different in message
    with manifest.open("a") as f:
        f.write(f"{relative}\t12\t{'b' * 64}\n")
    with pytest.raises(AssertionError, match="Conflicting recorded identities"):
        ev.artifact_identity(relative)


@pytest.mark.skipif(not RUNS, reason="scripts/collect_evidence.py is not in this tree")
@pytest.mark.parametrize("tag,name", CASES, ids=lambda v: v)
def test_every_cited_run_has_its_evidence_committed(tag, name):
    path = ev.recorded_path(tag, name)
    assert path.is_file(), (
        "%s is not committed. Every run a document cites must carry its "
        "own metrics.json and resolved.json under docs/evidence/, or the "
        "claims that name it cannot be checked from a clone. Run "
        "scripts/collect_evidence.py on a machine that has the run tree."
        % path.relative_to(ROOT))
    data = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict) and data, "%s is empty" % path


@pytest.mark.skipif(not RUNS, reason="scripts/collect_evidence.py is not in this tree")
def test_records_match_available_originals_including_recovered_snapshots(historical_snapshot):
    """A record that has drifted from its run is a record of nothing.

    ONE test and not thirty. The first version parametrised over every
    run and file, which reads well on a machine holding the run trees
    and turns into thirty identical skips on every machine that does
    not -- a clone, the mirror, CI. Thirty skips saying the same thing
    is not thirty facts, and this repository's own rule is that a skip
    must carry a reason worth reading. Where the trees ARE present this
    still names every file it compared.
    """
    checked, absent = [], []
    for tag in sorted(RUNS):
        base = ROOT / RUNS[tag] / tag
        for name in NAMES:
            live = base / ("final/metrics.json" if name == "metrics.json"
                           else "resolved.json")
            if not live.is_file():
                recovered = historical_snapshot / live.relative_to(ROOT)
                if recovered.is_file():
                    # Original raw file restored from a separately hash-pinned
                    # snapshot. This comparison is not a current physical rerun.
                    recorded = ev.recorded_path(tag, name)
                    assert recovered.read_bytes() == recorded.read_bytes(), (
                        f'Recovered original differs from committed record: {tag}/{name}')
                    checked.append('recovered original: %s/%s' % (tag, name))
                    continue
                absent.append("%s/%s" % (tag, name))
                continue
            # evidence.load raises on a mismatch, naming both paths.
            got = ev.load(tag, name, live)
            assert got is not None and got.is_live
            checked.append("%s/%s" % (tag, name))
    assert checked, "nothing compared"


@pytest.mark.skipif(not RUNS, reason="scripts/collect_evidence.py is not in this tree")
def test_the_sign_off_metrics_carry_the_keys_the_documents_read():
    """The sign-off run's record is the one most claims lean on."""
    m = ev.metrics("s83romecc5")
    assert m is not None, "docs/evidence/s83romecc5/metrics.json is absent"
    for key in ("design__instance__count",
                "design__instance__utilization",
                "route__drc_errors"):
        assert key in m, (
            "%s is not in the recorded sign-off metrics; the documents "
            "read it, so its absence makes them uncheckable" % key)
