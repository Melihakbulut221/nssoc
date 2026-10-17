# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Real parallel branches and exact capacitive-load identities, no Nx extrapolation."""

from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import characterize_pcie_clock_driver_v3 as new  # noqa: E402


@pytest.mark.parametrize("count", new.COUNTS)
def test_real_parallel_branches_keep_each_foundry_device_in_range(count):
    text = new.circuit(dict(new.old.BASE), count)
    hbts = new.contract(text, count)
    assert len(hbts) == 18 + 4 * (count - 1)
    for name in new.BRANCHES:
        for index in range(1, count):
            assert hbts[name + f"d{index}"] == hbts[name]
    assert max(nx for _, nx in hbts.values()) == 4
    source = new.CIRCUIT.read_text()
    original_lines = [
        x for x in source.splitlines() if not x.startswith((".subckt", ".ends"))
    ]
    assert all(x in text.splitlines() for x in original_lines)
    assert text.count("rppd ") == 9 and text.count("cap_cmim ") == 6


@pytest.mark.parametrize("count", [0, 2, 16])
def test_unreviewed_branch_count_rejected(count):
    with pytest.raises(ValueError):
        new.circuit(dict(new.old.BASE), count)


def test_out_of_model_emitter_count_rejected():
    text = new.circuit(dict(new.old.BASE), 4).replace("Nx=4", "Nx=16", 1)
    with pytest.raises(ValueError, match="Nx1..10"):
        new.contract(text, 4)


def test_duplicate_or_missing_physical_device_rejected():
    text = new.circuit(dict(new.old.BASE), 4)
    with pytest.raises(ValueError, match="Duplicate"):
        new.contract(text + "\nXFPD1 avdd bo_p clkp sub npn13G2 Nx=4\n", 4)
    with pytest.raises(ValueError, match="census"):
        new.contract(text.replace("XFPD1 avdd bo_p clkp sub npn13G2 Nx=4\n", ""), 4)


@pytest.mark.parametrize(
    "fault", ["", "no_bias", "no_feedback", "same_clock", "overload"]
)
def test_all_actual_devices_initialized_and_observed_without_stimulus_change(fault):
    case = dict(new.old.BASE, fault=fault)
    hbts = new.contract(new.circuit(case, 4), 4)
    text = new.deck(
        case, Path("/models"), [Path("/model.osdi")], 0.561e-12, 0.562e-12, hbts
    )
    assert text.count("alter @q.xosc.") == len(hbts) == 30
    assert len(set(new.vectors(hbts))) == len(new.vectors(hbts))
    assert set(new.old.vectors()).issubset(new.vectors(hbts))
    assert "tran 1e-12 12n 0 1e-12" in text
    assert ".options reltol=1e-4 abstol=1e-12" in text
    assert "uic" not in text and ".ic " not in text
    if fault == "overload":
        assert "CLOADN clkn 0 1e-10" in text and "CLOADP clkp 0 1e-10" in text
    else:
        assert "CLOADN clkn 0 5.62e-13" in text and "CLOADP clkp 0 5.61e-13" in text


def test_native_flag_coverage_is_every_new_instance():
    hbts = new.contract(new.circuit(dict(new.old.BASE), 4), 4)
    text = "".join(
        f"NSSOC_DRIVER_FLAG_BEGIN {n}\n device {n[:21]}\n off 1\nNSSOC_DRIVER_FLAG_END\n"
        for n in new.identities(hbts)
    )
    assert len(new.flags(text, hbts)) == 30
    for mutation in [
        text.replace("off 1", "off 0", 1),
        text + text,
        text.replace("q.xosc.xfpd1.qnpn13g2", "q.xosc.unknown.qnpn13g2"),
    ]:
        with pytest.raises(ValueError):
            new.flags(mutation, hbts)


def test_explicit_load_and_corner_cross_product():
    loads = [
        ("a", [1e-13, 2e-13]),
        ("b", [3e-13, 4e-13]),
        ("c", [5e-13, 6e-13]),
        ("d", [7e-13, 8e-13]),
    ]
    assert len(new.cases("loads", loads)) == 4
    assert len(new.cases("pvt", loads)) == 32
    assert len(new.cases("full", loads)) == 55
    assert len(new.cases("negative", loads)) == 4
    assert len({r[0]["name"] for r in new.cases("pvt", loads)}) == 32
    with pytest.raises(ValueError):
        new.cases("unknown", loads)


def test_only_four_original_output_nodes_share_new_copies():
    hbts = new.contract(new.circuit(dict(new.old.BASE), 8), 8)
    old_hbts = new.old.device_contract(new.old.CIRCUIT.read_text())[0]
    assert set(hbts) - set(old_hbts) == {
        n + f"d{i}" for n in new.BRANCHES for i in range(1, 8)
    }
    assert all(hbts[n] == old_hbts[n] for n in old_hbts)
    assert (
        new.old.LIMITS["min_vce_v"] == 0.4 and new.old.LIMITS["min_diff_peak_v"] == 0.3
    )


def test_added_branch_current_density_and_bias_observers_are_not_ignored(monkeypatch):
    hbts = new.contract(new.circuit(dict(new.old.BASE), 4), 4)
    data = {n: [0.0, 0.0, 0.0] for n in new.vectors(hbts)}
    data["time"] = [0.0, 4e-9, 5e-9]
    for n in hbts:
        data[f"@q.xosc.{n}.qnpn13g2[ic]"] = [0.0, 1e-3, 1e-3]
        data[f"@q.xosc.{n}.qnpn13g2[ib]"] = [0.0, 1e-6, 1e-6]
    monkeypatch.setattr(
        new.old,
        "measure",
        lambda _: dict(
            checks=dict.fromkeys(
                (*new.FUNCTIONAL_CHECKS, "headroom", "maximum_vce", "current_density"),
                True,
            ),
            screen_pass=True,
        ),
    )
    for instance, bad, good, nx in [
        ("xfpd1", 0.0121, 0.0119, 4),
        ("xftpd1", 0.0031, 0.0029, 1),
    ]:
        key = f"@q.xosc.{instance}.qnpn13g2[ic]"
        data[key] = [0.0, bad, bad]
        result = new.measure(data, hbts)
        assert result["devices"][instance]["nx"] == nx
        assert not result["checks"]["current_density"]
        data[key] = [0.0, good, good]
        assert new.measure(data, hbts)["checks"]["current_density"]
        data[key] = [0.0, 1e-3, 1e-3]
    bias = new.measure(data, hbts)["bias"]
    assert len(bias["bias_device_names"]) == 10
    assert bias["mean_sum_bref_base_current_a"] == pytest.approx(10e-6)
    assert bias["output_sink_mean_ic_a"] == pytest.approx(8e-3)


def test_electrical_violation_alone_does_not_reject_functional_negative():
    checks = dict.fromkeys(new.FUNCTIONAL_CHECKS, True)
    checks.update(headroom=False, maximum_vce=False, current_density=False)
    assert new.functional_clock_pass(dict(checks=checks))
    checks["frequency"] = False
    assert not new.functional_clock_pass(dict(checks=checks))
    del checks["duty"]
    with pytest.raises(ValueError):
        new.functional_clock_pass(dict(checks=checks))


def test_two_emitter_sink_geometry_changes_only_actual_sink_branches():
    first = new.contract(new.circuit(dict(new.old.BASE), 4, 1), 4)
    second = new.contract(new.circuit(dict(new.old.BASE), 4, 2), 4)
    for name, (nodes, nx) in second.items():
        assert nodes == first[name][0]
        assert nx == (2 if name.startswith(("xftp", "xftn")) else first[name][1])
    with pytest.raises(ValueError):
        new.circuit(dict(new.old.BASE), 4, 12)


def test_native_capture_must_start_at_zero(tmp_path):
    hbts = new.contract(new.circuit(dict(new.old.BASE), 1), 1)
    vs = new.vectors(hbts)
    p = tmp_path / "wave.dat"
    header = " ".join(["time", *vs]) + "\n"
    rows = [
        " ".join([str(11.001e-9 + i * 1e-12), *(["0"] * len(vs))]) for i in range(1000)
    ]
    p.write_text(header + "\n".join(rows) + "\n")
    with pytest.raises(ValueError, match="coverage"):
        new.read_wave(p, hbts, dict(new.old.BASE))


def test_disk_exhaustion_cannot_truncate_last_complete_receipt(tmp_path, monkeypatch):
    import errno

    path = tmp_path / "result.json"
    path.write_text('{"status":"previous-complete"}\n')
    previous = path.read_bytes()
    real_write = Path.write_text

    def fail(target, text, *args, **kwargs):
        if target.name == "result.json.tmp":
            real_write(target, text[:3], *args, **kwargs)
            raise OSError(errno.ENOSPC, "No space left on device")
        return real_write(target, text, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", fail)
    with pytest.raises(OSError):
        new.atomic_record(path, dict(status="new"))
    assert path.read_bytes() == previous
    monkeypatch.setattr(Path, "write_text", real_write)
    new.atomic_record(path, dict(status="new"))
    assert '"new"' in path.read_text()
    assert not (tmp_path / "result.json.tmp").exists()
