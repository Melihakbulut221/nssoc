# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0

"""The artefact manifest must cover what the paper cites.

WHY THIS EXISTS. `docs/80` pins artefacts by digest so that a number in
the paper can be traced to the bytes it came from, and
`scripts/artefact_digests.py --check` re-verifies them. But nothing ran
either. There was no test naming the script and `scripts/verify.sh` did
not call it, so the manifest was a thing a person runs -- and a manifest
nobody runs is a manifest that silently stops covering what it is for.

The specific failure it permits: `paper/claims.yaml` names artefact
paths under gitignored run trees, and nothing compared the two files, so
the next claim added could go unpinned exactly as several already had.

WHAT THIS DOES NOT DO. It does not run `--check`. That re-hashes
artefacts which are gitignored and mostly absent on a fresh clone, and a
test that fails on a clean checkout is a test people delete. It checks
the relationship between the two FILES, which is true in any checkout.
"""

import json
import pathlib
import sys
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "docs" / "80-artefact-digests.tsv"
CLAIMS = ROOT / "paper" / "claims.yaml"

# The directory prefixes that name a build artefact rather than a source
# file. docs/80 section 2's own list.
ARTEFACT_ROOTS = ("hw/soc/pnr/runs/", "hw/soc/out/", "hw/openlane/",
                  "formal/eqy/out/")


def _cited_artefacts():
    text = CLAIMS.read_text(errors="ignore")
    pat = re.compile(r"(?:" + "|".join(re.escape(r) for r in ARTEFACT_ROOTS)
                     + r")[^\s\"',\]}]+")
    return {m.group(0) for m in pat.finditer(text)}


def test_the_manifest_and_the_claims_registry_both_exist():
    """Neither file may quietly disappear: each is the other's check."""
    assert MANIFEST.is_file(), "docs/80's manifest is gone"
    assert CLAIMS.is_file(), "paper/claims.yaml is gone"


def test_every_run_tree_the_paper_cites_is_named_in_the_manifest():
    """A claim may point into a gitignored tree only if that tree is pinned.

    The unit is the RUN, not the file. claims.yaml cites individual
    reports inside a run directory and the manifest pins a selection of
    files from it; requiring an exact path match would fail on the
    difference between `runs/s77gate/final/metrics.json` and the rows
    that pin `runs/s77gate/...`. What must hold is that the run the
    paper leans on appears in the manifest at all -- otherwise the
    digest record does not reach the evidence.
    """
    manifest = MANIFEST.read_text(errors="ignore")
    cited = _cited_artefacts()
    assert cited, "claims.yaml cites no artefact paths at all -- the " \
                  "pattern above has probably stopped matching"

    def run_of(p):
        m = re.match(r"(hw/soc/pnr/runs/[^/]+)", p)
        return m.group(1) if m else None

    runs = {r for r in (run_of(p) for p in cited) if r}
    missing = sorted(r for r in runs if r not in manifest)
    assert not missing, (
        "paper/claims.yaml leans on {} run tree(s) that docs/80's "
        "manifest does not name: {}. Either pin them with "
        "scripts/artefact_digests.py or stop citing them -- a claim "
        "pointing into a gitignored directory that nothing pins is a "
        "claim a reader cannot reach.".format(len(missing), missing))


def test_the_manifest_is_not_empty_and_is_tab_separated():
    """A manifest that has become a blank file passes every other check."""
    rows = [r for r in MANIFEST.read_text(errors="ignore").split("\n")
            if r.strip() and not r.lstrip().startswith("#")]
    assert len(rows) > 50, (
        "docs/80's manifest has {} rows; it pinned hundreds. A manifest "
        "that shrank is the failure this file exists to notice."
        .format(len(rows)))
    assert all("\t" in r for r in rows[:20]), \
        "the manifest has stopped being tab-separated"


# =====================================================================
# docs/09 target #5's cross-check, as a gate rather than a script
# =====================================================================

def test_the_any_state_theorem_and_the_campaign_agree():
    """docs/09 gate F3: any disagreement here is a blocker.

    formal/lif_ctrl.sby's bmc_safe task proves that from an ILLEGAL
    state encoding the design reaches SAFE. The fault-injection
    campaigns corrupt exactly that encoding, so every lif_fsm record is
    an empirical instance of the theorem's antecedent, and the theorem
    forbids one outcome: silent data corruption.

    Nothing compared them until 2026-09-14. docs/35 called it the
    largest piece of unclaimed ground reachable without new RTL, and it
    stayed unclaimed because it sits across hw/tb/ and formal/ and
    neither pass owned it. The script that does the comparison is
    scripts/formal_fi_crosscheck.py; this is what makes it run.
    """
    import subprocess
    script = ROOT / "scripts" / "formal_fi_crosscheck.py"
    assert script.is_file(), "the cross-check script is gone"
    out = subprocess.run([sys.executable, str(script)], cwd=str(ROOT),
                         capture_output=True, text=True, timeout=300)
    assert out.returncode == 0, (
        "the any-state theorem and the injection campaign disagree, "
        "which docs/09 gate F3 calls a blocker:\n" + out.stdout + out.stderr)
    assert "AGREE" in out.stdout, out.stdout


# =====================================================================
# docs/evidence/: the records, covered here rather than in the manifest
# =====================================================================
#
# The external review's F6 acceptance asks that this file cover the
# committed evidence. It does NOT ask that docs/80 list it, and the two
# are different requests: that file's own header says every path in it
# is gitignored on purpose, because its job is to pin what git cannot
# see. docs/evidence/ is tracked, so git pins it already -- an edit is
# a diff -- and adding it to a manifest of untracked things would be a
# second, weaker copy of a guarantee git gives for free.
#
# What git does NOT give is the two properties below: that every run a
# claim or a document names has its record, and that the record is the
# one scripts/collect_evidence.py would write. Those are what this
# covers.


EVIDENCE = ROOT / "docs" / "evidence"
COLLECTOR = ROOT / "scripts" / "collect_evidence.py"


def _collector_runs():
    if not COLLECTOR.is_file():
        return {}
    import importlib.util
    spec = importlib.util.spec_from_file_location("collect_evidence", COLLECTOR)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return dict(mod.RUNS)


def test_every_run_the_collector_names_has_its_record_committed():
    runs = _collector_runs()
    if not runs:
        pytest.skip("scripts/collect_evidence.py is not in this tree")
    missing = []
    for tag in sorted(runs):
        for name in ("metrics.json", "resolved.json"):
            if not (EVIDENCE / tag / name).is_file():
                missing.append("%s/%s" % (tag, name))
    assert not missing, (
        "docs/evidence/ is missing %d files the collector names: %s. "
        "Run scripts/collect_evidence.py on a machine that has the run "
        "trees; without them the claims and tests that read these runs "
        "go back to skipping, which is where this started."
        % (len(missing), ", ".join(missing)))


def test_every_committed_record_is_json_with_content():
    if not EVIDENCE.is_dir():
        pytest.skip("docs/evidence/ is not in this tree")
    files = sorted(EVIDENCE.rglob("*.json"))
    assert files, "docs/evidence/ carries no records at all"
    for f in files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise AssertionError("%s is not JSON: %s"
                                 % (f.relative_to(ROOT), exc))
        assert isinstance(data, dict) and data, (
            "%s is empty, so it records nothing" % f.relative_to(ROOT))


def test_no_record_exists_for_a_run_the_collector_does_not_name():
    """A fossil record is worse than none: it reads as evidence."""
    runs = _collector_runs()
    if not runs or not EVIDENCE.is_dir():
        pytest.skip("collector or docs/evidence/ absent")
    stray = sorted(d.name for d in EVIDENCE.iterdir()
                   if d.is_dir() and d.name not in runs)
    assert not stray, (
        "docs/evidence/ carries records for runs the collector does not "
        "name: %s. Either add them to RUNS with the document that cites "
        "them, or delete them -- a record nothing points at is a number "
        "with no claim behind it." % ", ".join(stray))

