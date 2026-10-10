# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""The mirror generator is idempotent, and still fails on a reworded hold.

READ THE TREE BEFORE READING THE ASSERTIONS. This file ships to the
public mirror, where every fact it states about a held fragment is
inverted: upstream the fragment is present and the redaction is not,
and in the mirror it is the other way round. The first version of this
file did not account for that, shipped, and turned the mirror's own CI
red on its first push -- a guard that fails where it is published is
worse than the defect it was written for. `IN_MIRROR` decides which
half applies, and the selected state is checked without skipping the other branch.

Corrected 2026-09-19: the old public tests actually skipped the rejection
and regeneration cases. Both now execute the production generator here too.

WHY THIS GUARD EXISTS. `scripts/gen_public_mirror.py` asserted that
every held fragment matched its pattern exactly once. Run against the
tree it had itself produced, the fragment was already redacted, the
pattern matched zero times, and the assertion fired -- so the mirror's
own copy of `scripts/ci_local.sh` could never pass its own mirror gate.
An external reviewer found it that way: the generator is an
upstream-only tool that had been shipped into the mirror and then wired
into the mirror's gate.

THE ASSERTION WAS NOT THE DEFECT, and weakening it would have been. Its
comment states the guarantee it exists for: *a fragment that has been
reworded upstream must fail the build, because the alternative is that
it travels*. That guarantee is about sensitive text escaping into a
public repository, and it is worth more than the convenience it costs.

So the fix distinguishes the two zero-match cases, and this file is the
proof that it distinguishes them correctly:

  pattern matches once, marker absent   -> redact (the upstream case)
  pattern matches zero, marker present  -> already done (the mirror case)
  pattern matches zero, marker absent   -> FAIL (the reworded case)

The third row is the one that matters. A test that only checked
idempotence would pass on a generator that had simply deleted the
assertion.

ONE ENTRY IS A FIXED POINT AND THE OTHER TWO ARE NOT, which is worth
knowing before reading the assertions below. `scripts/ci_local.sh`'s
replacement, `'(account status, not published)'`, itself matches the
pattern `'[^']*'` that found the original, so a second pass rewrites it
to itself and the pattern is still there afterwards. The ROADMAP and
design-review entries are not like that: their patterns no longer match
once redacted. So the property that holds for all three is not "the
pattern is gone" -- it is that the marker is present and that
regenerating produces the same bytes. That is what is asserted.
"""

import pathlib
import re
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
GEN = ROOT / "scripts" / "gen_public_mirror.py"

sys.path.insert(0, str(ROOT / "scripts"))


def _fragments():
    if not GEN.exists():
        return []
    import importlib.util
    spec = importlib.util.spec_from_file_location("gen_public_mirror", GEN)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return list(mod.HELD_FRAGMENTS)


FRAGMENTS = _fragments()

# IS THIS TREE THE UPSTREAM OR THE MIRROR? The two have opposite truths
# about every fragment, so a test that assumed one of them failed in the
# other -- which is what happened: the first version of this file was
# written upstream, shipped to the mirror by the generator, and turned
# the mirror's own CI red on its first push. The generator appends a
# section to README.md naming itself, and that is the signal.
MIRROR_NOTE = "This repository is a published subset of a private development"


def _is_generated_mirror():
    readme = ROOT / "README.md"
    return readme.is_file() and MIRROR_NOTE in readme.read_text(
        encoding="utf-8", errors="ignore")


IN_MIRROR = _is_generated_mirror()


def test_the_source_matches_its_declared_publication_state():
    """Check the actual upstream/mirror state without skipping either checkout."""
    assert FRAGMENTS, "the generator and its held-fragment inventory are required"
    for rel, pattern, _replacement, marker, _why in FRAGMENTS:
        src = ROOT / rel
        assert src.is_file(), rel
        text = src.read_text(encoding="utf-8")
        n = len(re.findall(pattern, text, flags=re.S))
        if IN_MIRROR:
            assert marker in text, f"{rel}: public redaction marker is missing"
            assert n in (0, 1), f"{rel}: duplicate held fragment"
        else:
            assert n == 1, f"{rel}: upstream fragment was changed or duplicated"
            assert marker not in text, f"{rel}: redaction marker present upstream"


def test_the_generated_tree_is_redacted_and_regenerates_unchanged(tmp_path):
    """The mirror case: pattern gone, marker present, and running again is a no-op."""
    first = tmp_path / "m1"
    r = subprocess.run([sys.executable, str(GEN), "--out", str(first)],
                       capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stdout + r.stderr

    for rel, _pattern, _replacement, marker, _why in FRAGMENTS:
        out = first / rel
        assert out.exists(), "%s is not in the published set" % rel
        assert marker in out.read_text(encoding="utf-8"), (
            "%s was not redacted" % rel)

    # The generated tree must be a git repository before the generator
    # can run inside it: the generator enumerates its input with
    # `git ls-files`, so an un-inited output directory fails for a
    # reason that has nothing to do with redaction. The real mirror is
    # a repository, so this reproduces the real situation.
    ident = ["-c", "user.name=t", "-c", "user.email=t@example.invalid"]
    for cmd in (["git", "init", "-q"], ["git", "add", "-A"],
                ["git"] + ident + ["commit", "-qm", "generated"]):
        g = subprocess.run(cmd, capture_output=True, text=True, cwd=first)
        assert g.returncode == 0, " ".join(cmd) + ": " + g.stdout + g.stderr

    # And now the case that used to abort: the generator run against its
    # own output. It must succeed, and the held files must come out
    # byte-identical -- a fixed point, which is the whole claim.
    second = tmp_path / "m2"
    r = subprocess.run([sys.executable, str(first / "scripts" / GEN.name),
                        "--out", str(second)],
                       capture_output=True, text=True, cwd=first)
    assert r.returncode == 0, (
        "the generator cannot run inside the tree it produced:\n"
        + r.stdout + r.stderr)
    for rel, _pattern, _replacement, marker, _why in FRAGMENTS:
        a = (first / rel).read_bytes()
        b = (second / rel).read_bytes()
        assert a == b, (
            "%s is not a fixed point: regenerating the mirror from the "
            "mirror changed it, so the redaction is applied twice and "
            "the two runs do not agree." % rel)
        assert marker in b.decode("utf-8")


def test_a_reworded_fragment_is_not_mistaken_for_a_redacted_one():
    """Exercise the production rejection on altered text in BOTH tree types.

    The former test skipped on the public mirror and, upstream, only checked
    regex preconditions without invoking the generator. These assertions must
    fail if its rejection is removed. Only in-memory text is altered.
    """
    from gen_public_mirror import redact_fragment
    assert FRAGMENTS
    for rel, pattern, replacement, marker, why in FRAGMENTS:
        text = (ROOT / rel).read_text(encoding="utf-8")
        reworded = re.sub(pattern, "REWORDED FRAGMENT", text, flags=re.S)
        reworded = reworded.replace(marker, "REWORDED FRAGMENT")
        assert reworded != text, rel
        assert not re.search(pattern, reworded, flags=re.S), rel
        assert marker not in reworded, rel
        with pytest.raises(AssertionError, match="held fragment"):
            redact_fragment(reworded, rel, pattern, replacement, marker, why)


@pytest.mark.parametrize("source", ["held held", "held held [redacted]"])
def test_duplicate_matches_fail_even_when_a_marker_is_present(source):
    from gen_public_mirror import redact_fragment
    with pytest.raises(AssertionError, match="matched 2 times"):
        redact_fragment(source, "fixture.txt", r"held", "[redacted]",
                        "[redacted]", "synthetic test fragment")


def test_first_redaction_and_second_redaction_use_the_same_production_rule():
    from gen_public_mirror import redact_fragment
    args = ("fixture.txt", r"held", "[redacted]", "[redacted]", "test fragment")
    once = redact_fragment("before held after", *args)
    assert once == "before [redacted] after"
    assert redact_fragment(once, *args) == once
