# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Circuit binding, physical fault targeting and owned lifecycle controls.

Native PCell generation, DRC and LVS are separate measured acceptance gates.
"""

from collections import Counter
from decimal import Decimal
import copy
import hashlib
import json
import os
from pathlib import Path
import signal
import sys
import threading

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "hw/soc/flow"), str(ROOT / "scripts")]
import make_pcie_clock_div4_v9_bias_v1 as m  # noqa: E402
import check_pcie_clock_div4_v9_bias_v1 as c  # noqa: E402


def test_all73_devices_match_independent_actual_analog_graph():
    import characterize_pcie_vco_v6_feedback_bias_v2 as analog

    expected = analog.core.n.graph(
        m.source_texts(ROOT),
        [("nssoc_clock_div4_hbt_v9", "div", [n.lower() for n in m.PORTS])],
    )
    actual = []
    for row in m.devices(ROOT):
        params = (
            {"nx": str(row["nx"])}
            if row["kind"] == "hbt"
            else {"w": f"{row['width_um']:g}u", "l": f"{row['length_um']:g}u"}
        )
        if row["kind"] == "resistor":
            params.update(b="0", sw_et="1")
        actual.append(
            dict(
                path=row["name"].replace("__", ".").lower(),
                model={"hbt": "npn13g2", "resistor": "rppd", "capacitor": "cap_cmim"}[
                    row["kind"]
                ],
                nets=[n.replace("__", ".").lower() for n in row["nets"]],
                params=params,
            )
        )
    assert actual == expected and len(actual) == 73
    assert Counter(r["kind"] for r in m.devices(ROOT)) == {
        "hbt": 34,
        "resistor": 33,
        "capacitor": 6,
    }
    import make_pcie_clock_div4_v8_cap_v1 as old
    changed = []
    for before, after in zip(old.devices(ROOT), m.devices(ROOT), strict=True):
        before = dict(before, source_subcircuit=after["source_subcircuit"])
        if before != after:
            assert before["width_um"] == 1 and before["length_um"] == 7
            assert after == dict(before, length_um=8)
            changed.append(after["name"])
    assert changed == ["DIV__XDP", "DIV__XDN"]


def test_compact_planner_preserves_graph_and_orders_with_separated_tracks():
    import make_pcie_clock_div4_v7_power_v2 as old
    rows = m.devices(ROOT)
    assert len(rows) == len(old.devices(ROOT)) == 73
    plan, starts, nets = m.placement_plan(rows)
    original, _, _ = old.placement_plan(rows)
    assert set(plan) == set(original)
    assert Counter(p[0] for p in plan.values()) == {0: 30, 1: 17, 2: 26}
    assert len({(p[1], p[2]) for p in plan.values()}) == 73
    assert max(p[1] for p in plan.values()) == 856
    assert starts == {0: 0.0, 1: 176.0, 2: 328.0}
    for rid in range(3):
        names = [n for n in plan if plan[n][0] == rid]
        assert sorted(names,key=lambda n:plan[n][1]) == sorted(names,key=lambda n:original[n][1])
        tracks = [m.bus_offset(nets[rid],n) for n in nets[rid]]
        assert tracks[0] == 72
        for i in range(1,len(tracks)):
            wide = bool(set(nets[rid][i-1:i+1]) & {"DIV_AVDD", "AVSS"})
            assert tracks[i]-tracks[i-1] == (8 if wide else 4)
        if rid < 2:
            assert starts[rid+1] == starts[rid]+tracks[-1]+24
    assert nets[0][5:7] == ["DIV__XFIRST__XCORE__XS__SE", "DIV__XFIRST__XCORE__XS__TE"]
    assert nets[1][3] == "DIV__LP"
    assert nets[2][5:7] == ["DIV__XSECOND__XS__TE", "DIV__XSECOND__XM__TE"]
    assert [rid for rid in nets if "CLKP" in nets[rid]] == [0]
    assert [rid for rid in nets if "DIV__S1P" in nets[rid]] == [0, 1]
    # Conservative intrinsic + left escape envelopes, independent of the
    # generated GDS. Actual DRC will verify native polygons and all routes.
    by = {r["name"]:r for r in rows}
    for rid in range(3):
        ordered = sorted((n for n in plan if plan[n][0]==rid), key=lambda n:plan[n][1])
        for before,after in zip(ordered,ordered[1:]):
            a = by[before]
            right = 8.9 if a["kind"]=="hbt" else a["width_um"]+0.6
            assert Decimal(str(plan[after][1]))-9-(Decimal(str(plan[before][1]))+Decimal(str(right))) >= (Decimal("2.4") if before in {"DIV__XCP", "DIV__XCN"} else 5)
        for name in ordered:
            row=by[name];y=plan[name][2]-starts[rid]
            top = 3.78 if row["kind"]=="hbt" else row["length_um"]+(0.61 if row["kind"]=="resistor" else 0.60)
            assert 59.77 <= y+top <= 60.001
    with pytest.raises(ValueError,match="row bus absent"):
        m.bus_offset(nets[0],"UNKNOWN")


@pytest.mark.parametrize("fault", ["omit", "duplicate", "unknown"])
def test_placement_rejects_missing_extra_or_unknown_actual_cell(fault):
    rows = copy.deepcopy(m.devices(ROOT))
    if fault == "omit":
        rows.pop()
    elif fault == "duplicate":
        rows[-1] = rows[0]
    else:
        rows[-1]["name"] = "UNSUPPORTED_NEW_CELL"
    with pytest.raises(ValueError):
        m.placement_plan(rows)


@pytest.mark.parametrize("filename", list(m.SOURCES))
def test_any_source_byte_mutation_is_rejected(tmp_path, filename):
    for path in m.SOURCES:
        p = tmp_path / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes((ROOT / path).read_bytes())
    p = tmp_path / filename
    p.write_text(p.read_text() + "\n")
    with pytest.raises(ValueError, match="Frozen source differs"):
        m.devices(tmp_path)


@pytest.mark.parametrize(
    "fault",
    [
        "duplicate",
        "unclosed",
        "outside",
        "ideal",
        "nx",
        "selfheat",
        "foreign_mos",
        "recursion",
        "arity",
    ],
)
def test_source_parser_rejects_unsupported_topology_or_geometry(fault):
    texts = m.source_texts(ROOT)
    key = "hw/soc/analog/pcie/clock_div4_hbt_v9.spice"
    s = texts[key]
    if fault == "duplicate":
        s += s
    elif fault == "unclosed":
        s = s.replace(".ends nssoc_clock_div4_hbt_v9", "")
    elif fault == "outside":
        s += "\nVFAKE qp qn 1\n"
    elif fault == "ideal":
        s = s.replace("XLREF lref lref avss sub npn13G2 Nx=1", "VFAKE qp qn 1")
    elif fault == "nx":
        s = s.replace("Nx=1", "Nx=20")
    elif fault == "selfheat":
        s = s.replace("sw_et=1", "sw_et=0", 1)
    elif fault == "foreign_mos":
        s = s.replace(
            "XLREF lref lref avss sub npn13G2 Nx=1",
            "XFAKE qp clkp avdd avdd sg13_hv_pmos w=1u l=1u ng=1 m=1",
        )
    elif fault == "recursion":
        s = s.replace("nssoc_clock_div2_conditioned_hbt_v3", "nssoc_clock_div4_hbt_v9")
    else:
        s = s.replace("XFIRST clkp clkn", "XFIRST clkp")
    texts[key] = s
    with pytest.raises(ValueError):
        m.flatten(texts)


def test_real_body_contacts_and_seven_ports_contain_no_oscillator_leftovers():
    text = m.physical_reference(ROOT)
    assert text.count("ptap1 A=4p P=8u") == 18
    assert m.PORTS == ("CLKP", "CLKN", "QP", "QN", "DIV_AVDD", "AVSS", "SUB")
    assert not any(
        token in text
        for token in ("OSC__", "VCTRL", "VCO_AVDD", "NWELL", "ntap", "pmos")
    )
    assert not any(
        line.startswith(("V", "I", "B", "E", "G")) for line in text.splitlines()
    )
    assert all(m.use_direction(n) == ("SIGNAL", "INPUT") for n in ("CLKP", "CLKN"))
    assert all(m.use_direction(n) == ("SIGNAL", "OUTPUT") for n in ("QP", "QN"))
    assert m.use_direction("DIV_AVDD") == ("POWER", "INOUT")
    assert m.use_direction("SUB") == m.use_direction("AVSS") == ("GROUND", "INOUT")


@pytest.mark.parametrize("fault", c.REFERENCE_FAULTS)
def test_each_real_reference_fault_binds_once(fault):
    text = m.physical_reference(ROOT)
    changed = c.fault_reference(text, fault)
    assert changed != text
    with pytest.raises(ValueError, match="exactly once"):
        c.fault_reference(changed, fault)


def normalized_reference_fixture():
    # Byte-exact saved native syntax; the new physical extraction is separate.
    path = (
        Path(__file__).parent / "fixtures/pcie_clock_div4_v7/native-deep-extracted.cir"
    )
    data = path.read_bytes()
    assert (
        hashlib.sha256(data).hexdigest()
        == "8a6af77904a94ec75c2b220a7017f5c179e1e8818cda437bf4af1d80c30fe4a6"
    )
    text=data.decode()
    assert text.count("w=20u l=20u A=400p P=80u") == 2
    text=text.replace("w=20u l=20u A=400p P=80u", "w=24u l=24u A=576p P=96u")
    assert text.count("rppd w=1u l=7u") == 2
    return text.replace("rppd w=1u l=7u", "rppd w=1u l=8u")


@pytest.mark.parametrize(
    "old,new",
    [
        ("A=72p", "A=68p"),
        ("P=144u", "P=136u"),
        ("ptap1", "ntap1"),
        ("Nx=2", "Nx=1"),
        ("we=70n", "we=71n"),
        ("m=1", "m=4"),
    ],
)
def test_strict_extracted_body_or_device_changes_are_rejected(old, new):
    good = normalized_reference_fixture()
    c.validate_expanded_devices(good)
    with pytest.raises(ValueError):
        c.validate_expanded_devices(good.replace(old, new, 1))


def test_actual_physical_mutations_use_new_clock_and_interstage_geometry():
    generated = dict(
        bbox_um=[0, 0, 1520, 920],
        origin_translation_um=[0, 0],
        ports={"CLKP": {"rect_um": [1518, 89, 1520, 91]}},
        peripheral_trunks={
            "DIV__S1P": dict(x_um=40, lower_y_um=150, upper_y_um=520),
            "DIV__S1N": dict(x_um=44, lower_y_um=160, upper_y_um=530),
        },
    )
    clk = c.mutation_source("gds", "wrong", generated, "clock_open")
    assert "pya.DBox(1516,88.0,1517,92.0)" in clk
    for name in ("row_trunk_open", "row_trunk_short"):
        code = c.mutation_source("gds", "wrong", generated, name)
        compile(code, "mutation", "exec")
        assert "layer(50,0)" in code and "340.0" not in code
    wrong = copy.deepcopy(generated)
    wrong["ports"]["CLKP"]["rect_um"] = [0, 89, 2, 91]
    with pytest.raises(ValueError, match="right-edge"):
        c.mutation_source("gds", "wrong", wrong, "clock_open")


def test_status_alone_and_unrelated_negative_never_pass():
    step = dict(
        name="feedback",
        audit_execution=dict(returncode=1),
        audit=dict(status="FAIL", circuit_status_counts={"Match": 1}),
    )
    with pytest.raises(ValueError, match="Unrelated"):
        c.validate_lvs(step, "", False)
    step = dict(
        audit_execution=dict(returncode=0),
        audit=dict(status="PASS within comparison scope", circuits=[]),
    )
    with pytest.raises(ValueError):
        c.validate_lvs(step, "", True)


@pytest.fixture
def owned_cpu(monkeypatch):
    # CI may expose two cores and64MiB tmpfs. This fixture adapts only the
    # lifecycle harness resources; production defaults stay independently
    # asserted below and native physical evidence still uses CPU10/1GiB.
    before = os.sched_getaffinity(0)
    target = 10 if 10 in before else min(before)
    monkeypatch.setattr(c, "CPU", target)
    monkeypatch.setattr(c, "ENTRY_FREE", 1024**2)
    monkeypatch.setattr(c, "SHARED_FLOOR", 1024**2)
    os.sched_setaffinity(0, {target})
    try:
        yield
    finally:
        os.sched_setaffinity(0, before)


def test_physical_resource_defaults_remain_strict():
    assert c.CPU == 10
    assert c.SCRATCH_LIMIT == 80 * 1024**2
    assert c.ENTRY_FREE == 1024**3
    assert c.SHARED_FLOOR == 512 * 1024**2
    assert c.LAUNCH_RESERVATION == 24 * 1024**2


def test_owned_execute_has_no_healthy_deadline_and_reaps_actual_process(
    tmp_path, monkeypatch, owned_cpu
):
    monkeypatch.setattr(c, "SCRATCH_ROOTS", (tmp_path,))
    assert os.sched_getaffinity(0) == {c.CPU}
    result = c.execute(
        [sys.executable, "-c", "import time; time.sleep(.35); print('completed')"],
        tmp_path,
        "healthy",
    )
    assert result["returncode"] == 0 and result["elapsed_watchdog"] is None
    owner = json.loads((tmp_path / "healthy.owned.json").read_text())
    assert owner["cleanup"] is None and owner["elapsed_watchdog_seconds"] is None
    assert owner["processes"][0]["status"] == "REAPED_NO_LIVE_MEMBERS"


def test_real_explicit_cancellation_closes_owned_group(
    tmp_path, monkeypatch, owned_cpu
):
    monkeypatch.setattr(c, "SCRATCH_ROOTS", (tmp_path,))
    timer = threading.Timer(0.4, lambda: os.kill(os.getpid(), signal.SIGTERM))
    timer.start()
    try:
        with pytest.raises(RuntimeError, match="SIGTERM"):
            c.execute(
                [sys.executable, "-c", "import time; time.sleep(30)"],
                tmp_path,
                "cancel",
            )
    finally:
        timer.cancel()
        timer.join()
    owner = json.loads((tmp_path / "cancel.owned.json").read_text())
    assert owner["status"] == "CANCELLED" and owner["cleanup"] is not None
    assert owner["processes"][0]["status"] == "FAILURE_REAPED"
    assert not any(
        p["state"] != "Z"
        for p in c.lifecycle()["group_members"](owner["processes"][0]["process_group"])
    )


def test_real_resource_failure_reaps_owned_native(tmp_path, monkeypatch, owned_cpu):
    monkeypatch.setattr(c, "SCRATCH_ROOTS", (tmp_path,))
    measurements = iter([0, c.SCRATCH_LIMIT + 1])
    monkeypatch.setattr(c, "scratch_bytes", lambda: next(measurements))
    with pytest.raises(ValueError, match="own scratch ceiling"):
        c.execute(
            [sys.executable, "-c", "import time; time.sleep(30)"], tmp_path, "resource"
        )
    owner = json.loads((tmp_path / "resource.owned.json").read_text())
    assert owner["status"] == "CANCELLED"
    assert owner["processes"][0]["status"] == "FAILURE_REAPED"
    assert not any(
        p["state"] != "Z"
        for p in c.lifecycle()["group_members"](owner["processes"][0]["process_group"])
    )


@pytest.mark.parametrize("boundary", ["complete", "teardown"])
def test_actual_completion_boundary_sigterm_is_never_lost(
    tmp_path, monkeypatch, owned_cpu, boundary
):
    monkeypatch.setattr(c, "SCRATCH_ROOTS", (tmp_path,))
    namespace = c.lifecycle()
    Base = namespace["ProcessOwner"]

    class BoundaryOwner(Base):
        terminal_saves = 0

        def save(self):
            super().save()
            if any(
                e["record"]["status"] == "REAPED_NO_LIVE_MEMBERS" for e in self.entries
            ):
                self.terminal_saves += 1
                if boundary == "teardown" and self.terminal_saves == 2:
                    os.kill(os.getpid(), signal.SIGTERM)

        def complete(self, process):
            result = super().complete(process)
            if boundary == "complete":
                os.kill(os.getpid(), signal.SIGTERM)
            return result

    monkeypatch.setattr(
        c, "lifecycle", lambda: dict(namespace, ProcessOwner=BoundaryOwner)
    )
    with pytest.raises(RuntimeError, match="SIGTERM"):
        c.execute([sys.executable, "-c", "print('complete')"], tmp_path, boundary)
    record = json.loads((tmp_path / (boundary + ".owned.json")).read_text())
    assert record["processes"][0]["status"] == "REAPED_NO_LIVE_MEMBERS"


def test_actual_fast_exiting_file_producer_checks_terminal_resource_limit(
    tmp_path, monkeypatch, owned_cpu
):
    monkeypatch.setattr(c, "SCRATCH_ROOTS", (tmp_path,))
    monkeypatch.setattr(c, "SCRATCH_LIMIT", 1024**2)
    monkeypatch.setattr(c, "LAUNCH_RESERVATION", 0)
    output = tmp_path / "actual-fast-native-output.bin"
    # A real child writes twoMiB and exits within one normal polling period.
    command = [
        sys.executable,
        "-c",
        "from pathlib import Path; import sys; Path(sys.argv[1]).write_bytes(b'X' * (2 * 1024**2))",
        str(output),
    ]
    with pytest.raises(ValueError, match="own scratch ceiling"):
        c.execute(command, tmp_path, "fast-producer")
    assert output.stat().st_size == 2 * 1024**2
    record = json.loads((tmp_path / "fast-producer.owned.json").read_text())
    assert record["processes"][0]["status"] == "REAPED_NO_LIVE_MEMBERS"
    assert record["status"] == "CANCELLED"


def test_all18_finite_tap_branches_are_clear_of_every_actual_device_escape_lane():
    rows = m.devices(ROOT)
    plan, starts, _ = m.placement_plan(rows)
    lanes = {i: [] for i in range(3)}
    for row in rows:
        rid, x, _ = plan[row["name"]]
        offsets = {"hbt": [-9, -6, -3], "resistor": [-6, -3], "capacitor": [-9, -5]}[row["kind"]]
        lanes[rid].extend(x + value for value in offsets)
    positions = [m.substrate_tap_position(i, starts) for i in range(18)]
    assert len(set(positions)) == 18
    for i, (x, y) in enumerate(positions):
        assert x == 170 + (i % 6) * 120 and y == starts[i // 6] + 4
        center = x + 1  # Exact native2x2 ptap pin center, independent of escape helpers.
        assert min(abs(center - lane) for lane in lanes[i // 6]) >= 4
    # Original compactV1 tap creates a real coincident M4 lane; do not lose
    # the triggering example merely because the new positions are clear.
    assert 301 in lanes[0] and 181 in lanes[1] and 301 in lanes[2]
    for i in [-1, 18]:
        with pytest.raises(ValueError, match="finite tap index"):
            m.substrate_tap_position(i, starts)


def test_only_two_pulldown_lengths_change_and_cap24_pitch_is_36um():
    before=(ROOT/"hw/soc/analog/pcie/clock_div4_hbt_v8.spice").read_text()
    after=(ROOT/"hw/soc/analog/pcie/clock_div4_hbt_v9.spice").read_text()
    original=[line for line in before.splitlines() if not line.startswith("*")]
    current=[line for line in after.splitlines() if not line.startswith("*")]
    expected=[]
    for line in original:
        line=line.replace("nssoc_clock_div4_hbt_v8", "nssoc_clock_div4_hbt_v9")
        if line.startswith(("XDP ", "XDN ")):
            assert "rppd w=1u l=7u" in line
            line=line.replace("rppd w=1u l=7u", "rppd w=1u l=8u")
        expected.append(line)
    assert current==expected
    rows=m.devices(ROOT);plan,_,_=m.placement_plan(rows)
    for name in ["DIV__XCP", "DIV__XCN"]:
        row=next(r for r in rows if r["name"]==name)
        assert row["width_um"]==row["length_um"]==24
        rid,x,y=plan[name]
        right=[p[1] for p in plan.values() if p[0]==rid and p[1]>x]
        if right:
            assert min(right)-x==36
        else:
            assert name=="DIV__XCN" and x+36<960
    assert plan["DIV__XCN"][1]-plan["DIV__XCP"][1]==36
