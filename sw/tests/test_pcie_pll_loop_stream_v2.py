# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Reproduce the real completion race and reject reordered-value corruption."""

import hashlib
from pathlib import Path
import sys

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import characterize_pcie_pll_loop_stream_v1 as old
import characterize_pcie_pll_loop_stream_v2 as new


def test_exact_terminal_completion_race_old_fails_new_succeeds(tmp_path, monkeypatch):
    executable = tmp_path / "native"
    executable.write_text("#!/bin/sh\nexit 0\n")
    executable.chmod(0o755)
    monkeypatch.setattr(old.n, "NG", executable)
    original_launch = old.life.ProcessOwner.launch

    def launch(owner, *args, **kwargs):
        process = original_launch(owner, *args, **kwargs)
        assert process.wait(timeout=5) == 0
        return process

    monkeypatch.setattr(old.life.ProcessOwner, "launch", launch)

    class Future:
        calls = 0

        def done(self):
            self.calls += 1
            return self.calls >= 2

        def result(self):
            return {"captured_at_terminal_branch": True}

    class Pool:
        def __init__(self, **kwargs):
            pass

        def submit(self, func):
            return Future()

        def shutdown(self, **kwargs):
            pass

    monkeypatch.setattr(old.concurrent.futures, "ThreadPoolExecutor", Pool)
    first, second = tmp_path / "old", tmp_path / "new"
    first.mkdir()
    second.mkdir()
    with pytest.raises(UnboundLocalError):
        old.native_wait(first, lambda *_: None)
    assert new.native_wait(second, lambda *_: None) == {
        "captured_at_terminal_branch": True
    }


def test_guard_allows_only_actual_file_disappearance(tmp_path, monkeypatch):
    victim = tmp_path / "published.bin"
    victim.write_bytes(b"proof")
    original = Path.stat

    def disappearing(path, *args, **kwargs):
        if path == victim:
            raise FileNotFoundError(path)
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "stat", disappearing)
    assert new.guard(tmp_path)[1] == 0

    def denied(path, *args, **kwargs):
        if path == victim:
            raise PermissionError(path)
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "stat", denied)
    with pytest.raises(PermissionError):
        new.guard(tmp_path)


def test_header_permutation_preserves_all_binary64_bits():
    columns = ["time", "v(b)", "v(a)"]
    a = np.array([[0.0, -0.0, 1.0], [1.0, 1.000000000000001, 3.0]], dtype="<f8")
    order = [0, 2, 1]
    b = a[:, order].copy()

    def digest(data, names):
        return hashlib.sha256(
            data.view("<u8")[:, new.canonical_indices(names)].tobytes()
        ).hexdigest()

    assert a.tobytes() != b.tobytes()
    assert digest(a, columns) == digest(b, [columns[i] for i in order])
    b.view("<u8")[0, 2] = 0  # Signed zero is still a real bit-level difference.
    assert digest(a, columns) != digest(b, [columns[i] for i in order])


@pytest.mark.parametrize("columns", [["v(a)", "time"], ["time", "v(a)", "v(a)"]])
def test_bad_header_identity_rejected(columns):
    with pytest.raises(ValueError):
        new.canonical_indices(columns)


def test_frozen_functions_and_original_namespace_unchanged():
    assert new.Meter is old.Meter and new.measurements is old.measurements
    assert old.guard is not new.guard and old.native_wait is not new.native_wait
    assert old.n.common.sha(old.__file__) == new.PREVIOUS_SHA
    bridge = new.BRIDGES["native_wait"]["exact_replacements"]
    assert len(bridge) == 1 and "captured = future.result()" in bridge[0][1]
    assert new.namespace["native_wait"] is new.native_wait
    assert new.namespace["capture"] is new.capture
