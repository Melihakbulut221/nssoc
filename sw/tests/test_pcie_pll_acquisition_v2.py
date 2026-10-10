# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Publication-route inverse bridge and actual owned-process controls; no SPICE."""

import inspect
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import characterize_pcie_pll_acquisition_v2 as m


def test_exact_run_and_publisher_inverse_and_private_namespaces():
    old = m.run_source.replace("OwnedPublisherV2(owner)", "life.OwnedPublisher(owner)")
    assert (
        m.hashlib.sha256(old.encode()).hexdigest()
        == m.previous.BRIDGES["run"]["modified_sha256"]
    )
    original = m.publisher_source
    for before, after in reversed(m.BRIDGES["publisher"]["exact_replacements"]):
        assert original.count(after) == 1
        original = original.replace(after, before)
    assert original == inspect.getsource(m.life.OwnedPublisher)
    assert m.main_source == inspect.getsource(m.previous.main)
    assert m.previous.namespace["run"] is m.previous.run
    assert m.previous.namespace["life"].OwnedPublisher is m.life.OwnedPublisher
    assert m.life.publication is not m.publication
    assert m.life.publication.__file__.endswith("publish_pcie_native_capture.py")
    assert m.namespace is not m.previous.namespace
    assert m.namespace["verify_parent"] is m.verify_parent
    assert m.namespace["run"] is m.run
    assert m.namespace["__doc__"] == m.__doc__
    for name in m.previous.main.__code__.co_names:
        if name in m.previous.main.__globals__ and name not in {"run", "__doc__"}:
            assert m.namespace[name] is m.previous.main.__globals__[name]


def test_unchanged_electrical_numerical_and_lifecycle_function_objects():
    for name in ["stream_deck", "measurements", "startup_proof", "prerequisites"]:
        assert getattr(m, name) is getattr(m.previous, name)
    for name in [
        "capture",
        "native_wait",
        "Meter",
        "guard",
        "FLOOR",
        "CAP",
        "PART_BYTES",
        "life",
    ]:
        assert m.namespace[name] is m.previous.namespace[name]
    assert m.namespace["FLOOR"] == 512 * 1024**2 and m.namespace["CAP"] == 50 * 1024**2
    assert m.STOP == 1e-6
    assert m.previous.FREQUENCY_RELATIVE_LIMIT == 100e-6
    assert m.previous.PHASE_RANGE_LIMIT_S == 50e-12
    assert m.sha(m.previous.__file__) == m.PREVIOUS_SHA
    assert m.sha(m.publication.__file__) == m.PUBLISHER_SHA


@pytest.mark.parametrize("step", [5e-12, 2.5e-12])
def test_actual_native_deck_bytes_unchanged(step):
    source = (m.previous.previous.previous.ORIGINAL / "bench.cir").read_text()
    assert m.stream_deck(source, step, 1e-6) == m.previous.stream_deck(
        source, step, 1e-6
    )
    assert (
        m.stream_deck(source, step, 1e-6).count(
            f".tran {step:.12g} 1e-06 0 {step:.12g}\n"
        )
        == 1
    )


@pytest.mark.parametrize(
    "version,number,has",
    [
        (sys.version_info, "0.0", True),
        ((3, 14), "2.5.3", True),
        ((3, 12), "2.5.3", False),
    ],
)
def test_runtime_guard_is_not_weakened(version, number, has):
    with pytest.raises(RuntimeError):
        m.runtime.check_runtime(version, number, has)


def stub(tmp_path, monkeypatch, mode):
    p = tmp_path / "publisher.py"
    p.write_text(
        """import argparse,json,hashlib
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--out',type=Path);p.add_argument('--tag');p.add_argument('file',type=Path);a=p.parse_args()
assert a.tag=='evidence-20261005-pcie-continuation'
b=a.file.read_bytes()
mode=MODE
if mode=='nonzero':raise SystemExit(7)
asset={'name':a.file.name,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'authenticated_roundtrip':True,'anonymous_roundtrip':True,'url':'local-control-only'}
a.out.write_text(json.dumps({'status':'FAIL' if mode=='bad_receipt' else 'PASS_IMMUTABLE_RELEASE_ROUNDTRIPS','assets':[asset],'tag':a.tag}))
""".replace("MODE", repr(mode))
    )
    monkeypatch.setitem(
        m.publisher_namespace, "publication", SimpleNamespace(__file__=str(p))
    )
    monkeypatch.setitem(m.publisher_namespace, "PUBLISHER_SHA", m.sha(p))
    return p


def test_actual_owned_child_uses_explicit_new_release(tmp_path, monkeypatch):
    script = stub(tmp_path, monkeypatch, "success")
    part = tmp_path / "part.bin"
    part.write_bytes(bytes(range(256)))
    with m.life.ProcessOwner(tmp_path / "owned.json") as owner:
        result = m.OwnedPublisherV2(owner)(part, tmp_path / "receipt.json")
        assert result["sha256"] == m.sha(part)
    ledger = json.loads((tmp_path / "owned.json").read_text())
    row = ledger["processes"][0]
    assert row["command"][1:] == [
        str(script),
        "--tag",
        m.RELEASE_TAG,
        "--out",
        str(tmp_path / "receipt.json"),
        str(part),
    ]
    assert row["status"] == "REAPED_NO_LIVE_MEMBERS" and row["returncode"] == 0
    assert ledger["elapsed_watchdog_seconds"] is None


@pytest.mark.parametrize("mode", ["nonzero", "bad_receipt"])
def test_actual_publication_failure_cleans_owned_native_substitute(
    tmp_path, monkeypatch, mode
):
    stub(tmp_path, monkeypatch, mode)
    part = tmp_path / "part.bin"
    part.write_bytes(b"finite control")
    with pytest.raises(ValueError):
        with m.life.ProcessOwner(tmp_path / "owned.json") as owner:
            child = owner.launch(
                "native",
                [sys.executable, "-c", "import time;time.sleep(60)"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            m.OwnedPublisherV2(owner)(part, tmp_path / "receipt.json")
    assert child.poll() is not None
    ledger = json.loads((tmp_path / "owned.json").read_text())
    assert ledger["status"] == "CANCELLED"
    assert ledger["cleanup"]["groups"][0]["kill_sent"]
    assert ledger["processes"][0]["status"] == "FAILURE_REAPED"
    assert part.read_bytes() == b"finite control"


def test_publisher_pin_rejects_before_any_child(tmp_path, monkeypatch):
    stub(tmp_path, monkeypatch, "success")
    monkeypatch.setitem(m.publisher_namespace, "PUBLISHER_SHA", "0" * 64)
    p = tmp_path / "part.bin"
    p.write_bytes(b"x")
    with pytest.raises(ValueError, match="Frozen publisher"):
        with m.life.ProcessOwner(tmp_path / "owned.json") as owner:
            m.OwnedPublisherV2(owner)(p, tmp_path / "receipt.json")
    assert not json.loads((tmp_path / "owned.json").read_text())["processes"]


@pytest.mark.parametrize(
    "status,code",
    [
        ("PASS_NATIVE_STREAM_FINITE_SCREEN", 0),
        ("FAIL_NATIVE_STREAM_FINITE_SCREEN", 1),
        ("ERROR_NATIVE_OR_STREAM_CAPTURE", 1),
        ("RUNNING", 1),
    ],
)
def test_cli_status_only_never_launches_native(tmp_path, monkeypatch, status, code):
    # Status dispatch is independent of the executing pytest ABI; runtime guard
    # remains tested above and the native CLI still calls the original guard.
    monkeypatch.setitem(
        m.namespace, "runtime", SimpleNamespace(check_runtime=lambda *a: None)
    )
    monkeypatch.setitem(m.namespace, "run", lambda *a: {"status": status})
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "method",
            "--out",
            str(tmp_path / "out"),
            "--prefix",
            "control",
            "--step-ps",
            "2.5",
            "--reference",
            "reference",
            "--reference-sha",
            "x",
            "--prerequisites",
            "prerequisites",
            "--prerequisites-sha",
            "y",
        ],
    )
    assert m.main() == code
