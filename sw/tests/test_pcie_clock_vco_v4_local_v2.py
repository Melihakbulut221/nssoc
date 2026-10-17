# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Exact local-route four-PMOS source and native extraction acceptance boundaries."""

import copy
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "hw/soc/flow"))
import check_pcie_clock_vco_v4_local_v2 as check
import make_pcie_clock_vco_v4_local_v2 as make

SOURCE = (ROOT / make.CIRCUIT).read_text()


def test_literal_four_devices_and_separate_finite_bodies():
    rows = make.devices(SOURCE)
    assert len(rows) == 49
    mos = [r for r in rows if r["kind"] == "pmos"]
    assert {r["name"] for r in mos} == {"CTRL0", "CTRL1", "CTRL2", "CTRL3"}
    for row in mos:
        assert row["width_um"] == 8 and row["length_um"] == 0.45 and row["ng"] == 1
        assert row["nets"] == ["REF", "VCTRL", "AVDD", "AVDD"]
    assert (
        sorted(r["nx"] for r in rows if r["kind"] == "hbt")
        == [1] * 2 + [2] * 17 + [4] * 11
    )
    reference = make.physical_reference(SOURCE)
    assert reference.count("SUB BULK ptap1 A=4p P=8u") == 12
    assert reference.count("AVDD NWELL ntap1 A=4p P=8u") == 1
    assert reference.count("NWELL sg13_hv_pmos w=8u") == 4
    assert "w=32u" not in reference
    assert not any(
        line.startswith(("V", "I", ".ic", ".IC")) for line in reference.splitlines()
    )


@pytest.mark.parametrize(
    "old,new",
    [
        ("w=8u", "w=32u"),
        ("Nx=4", "Nx=3"),
        ("p1 p0", "p1 n0"),
        ("ref vctrl avdd avdd", "ref vctrl avdd sub"),
        ("sw_et=1", "sw_et=0"),
        ("l=0.45u", "l=0.46u"),
    ],
)
def test_source_drift_rejected(old, new):
    with pytest.raises(ValueError, match="frozen source"):
        make.devices(SOURCE.replace(old, new, 1))


def test_locality_preserves_ring_and_compacts_real_limiter_and_followers():
    import make_pcie_clock_vco_v4_local as prior

    rows = make.devices(SOURCE)
    positions = make.placement(rows)
    old = prior.placement(rows)
    assert len(positions) == len(set(positions.values())) == 49
    unchanged = [
        r["name"]
        for r in rows
        if r["name"]
        not in {
            "BP",
            "BN",
            "BT",
            "BRP",
            "BRN",
            "FP",
            "FN",
            "FTP",
            "FTN",
            *[p + "D" + str(i) for p in ("FP", "FN", "FTP", "FTN") for i in (1, 2, 3)],
        }
    ]
    assert len(unchanged) == 28
    for name in unchanged:
        assert positions[name] == old[name]
    assert positions["BP"][1] == positions["P0"][1]
    assert positions["BN"][1] == positions["N0"][1]
    assert positions["BP"][0] - positions["P0"][0] == 38
    assert positions["BN"][0] - positions["N0"][0] == 38
    output_names = [
        p + suffix
        for p in ("FP", "FN", "FTP", "FTN")
        for suffix in ("", "D1", "D2", "D3")
    ]
    assert max(positions[n][0] for n in output_names) == 510
    assert max(positions[n][2] + 6 for n in output_names) == 531
    lanes = [lane + offset for _, _, lane in positions.values() for offset in (0, 3, 6)]
    assert len(lanes) == len(set(lanes)) == 147
    assert min(b - a for a, b in zip(sorted(lanes), sorted(lanes)[1:])) >= 3
    # Native DRC and strict LVS separately establish actual geometry and
    # terminal connectivity; placement alone is not physical acceptance.
    assert make.physical_reference(SOURCE).replace(
        make.TOP, prior.TOP
    ) == prior.physical_reference(SOURCE)
    for wrong in (rows[:-1], rows + [dict(rows[0], name="OTHER")]):
        with pytest.raises(ValueError, match="placement census"):
            make.placement(wrong)


def extracted_document():
    """Native syntax with explicit geometry rather than a simplified parallel device."""
    result = []
    for line in make.physical_reference(SOURCE).splitlines():
        if "rppd" in line:
            line = line.replace(" b=0", " ps=0u b=0")
        if "cap_cmim" in line:
            line = line.replace(
                " m=1",
                " A=146.4p P=48.4u m=1" if "w=12.2u" in line else " A=144p P=48u m=1",
            )
        if "sg13_hv_pmos" in line:
            line = line.replace(
                "w=8u l=0.45u ng=1 m=1",
                "L=0.45u W=8u AS=2.72p AD=2.72p PS=16.68u PD=16.68u rfmode=0",
            )
        result.append(line.replace("we=0.07u le=0.9u", "we=70n le=900n"))
    return "\n".join(result)


def positive():
    return dict(
        name="lvs",
        audit_execution={"returncode": 0},
        audit={
            "status": "PASS within comparison scope",
            "circuit_status_counts": {"Match": 1},
            "circuits": [
                dict(layout_devices_recursive=62, schematic_devices_recursive=62)
            ],
        },
    )


def test_unsimplified_native_source_geometry_passes():
    check.validate_lvs(positive(), extracted_document(), True)


@pytest.mark.parametrize(
    "old,new",
    [
        ("W=8u", "W=32u"),
        ("L=0.45u", "L=0.46u"),
        ("Nx=4", "Nx=3"),
        ("Nx=4 we=70n le=900n m=1", "Nx=4 we=70n le=900n m=4"),
        ("we=70n", "we=71n"),
        ("A=4p P=8u", "A=48p P=96u"),
        ("SUB BULK ptap1", "SUB AVSS ptap1"),
        ("AVDD NWELL ntap1", "AVDD AVDD ntap1"),
        ("w=12.2u", "w=12u"),
        ("AS=2.72p", "AS=2.73p"),
        ("rfmode=0", "rfmode=1"),
        ("b=0", "b=1"),
    ],
)
def test_native_geometry_and_finite_contact_faults_reject(old, new):
    text = extracted_document()
    assert old in text
    with pytest.raises(ValueError):
        check.validate_native_devices(text.replace(old, new, 1))


def test_missing_or_combined_control_device_cannot_pass_count():
    text = extracted_document()
    lines = text.splitlines()
    i = next(i for i, line in enumerate(lines) if line.startswith("MCTRL3 "))
    lines.pop(i)
    with pytest.raises(ValueError, match="sixty-two"):
        check.validate_native_devices("\n".join(lines))


@pytest.mark.parametrize("fault", check.REFERENCE_FAULTS)
def test_reference_controls_bind_exactly_once(fault):
    reference = make.physical_reference(SOURCE)
    wrong = check.fault_reference(reference, fault)
    assert wrong != reference and wrong.splitlines()[2] == reference.splitlines()[2]
    for invalid in ("", reference + reference, wrong):
        with pytest.raises(ValueError):
            check.fault_reference(invalid, fault)


@pytest.mark.parametrize("fault", check.PHYSICAL_FAULTS)
def test_actual_geometric_controls_are_executable(fault):
    generated = dict(
        instances=[
            {"name": "NTAP", "body_connection_geometry_um": "(399,16;411,119)"},
            {"name": "CTRL1", "bbox_um": "(399,49;406,61)"},
            {"name": "CTRL2", "bbox_um": "(399,79;406,91)"},
        ],
        bbox_um=[0, 0, 760, 412],
        origin_translation_um=[0, 0],
        ports={
            name: dict(rect_um=[0, 230 + 4 * i, 2, 232 + 4 * i])
            for i, name in enumerate(make.PORTS)
        },
        routes=[
            dict(
                device="N0",
                net="T0",
                source_layer=2,
                actual_pin_um="(40.1,49.8;41.8,50.2)",
                escape_lane_um=75,
                escape_y_um=49.995,
            ),
            dict(
                device="BN",
                net="BT",
                source_layer=2,
                actual_pin_um="(78.1,49.8;79.8,50.2)",
                escape_lane_um=102,
                escape_y_um=49.995,
            ),
            dict(
                device="FPD2",
                net="AVDD",
                actual_pin_um="(540,50;548,50.3)",
                escape_lane_um=569,
                escape_y_um=50.2,
            ),
        ],
    )
    for name in ("CLKP", "CLKN"):
        generated["ports"][name]["rect_um"][0:3:2] = [758, 760]
    code = check.mutation_source(
        Path("/source.gds"), Path("/wrong.gds"), generated, fault
    )
    compile(code, "native geometry mutation", "exec")
    assert "l.write" in code
    if fault == "well_open":
        assert "l.layer(31,0)" in code and "region-=" in code


def test_failed_native_process_or_topology_never_passes_geometry_only():
    text = extracted_document()
    for key, value in [
        ("status", "FAIL"),
        ("circuits", []),
        (
            "circuits",
            [dict(layout_devices_recursive=61, schematic_devices_recursive=62)],
        ),
    ]:
        step = positive()
        step["audit"][key] = value
        with pytest.raises(ValueError):
            check.validate_lvs(step, text, True)
    step = positive()
    step["audit_execution"]["returncode"] = 1
    with pytest.raises(ValueError):
        check.validate_lvs(step, text, True)
    for missing in make.PORTS:
        lines = text.splitlines()
        lines[2] = lines[2].replace(" " + missing, "")
        with pytest.raises(ValueError):
            check.validate_lvs(positive(), "\n".join(lines), True)


def test_negative_must_be_actual_native_topology_mismatch():
    negative = dict(
        name="well_open",
        audit_execution={"returncode": 1},
        audit={"status": "FAIL", "circuit_status_counts": {"NoMatch": 1}},
    )
    check.validate_lvs(negative, "", False)
    for wrong in (
        dict(negative, audit_execution={"returncode": 2}),
        dict(negative, audit={"status": "FAIL", "circuit_status_counts": {}}),
    ):
        with pytest.raises(ValueError):
            check.validate_lvs(copy.deepcopy(wrong), "", False)


def test_control_open_requires_exact_missing_port_and_all_devices():
    step = positive()
    step["name"] = "control_open"
    step["audit_execution"]["returncode"] = 1
    step["audit"]["status"] = "FAIL"
    text = extracted_document()
    lines = text.splitlines()
    lines[2] = lines[2].replace(" VCTRL", "")
    opened = "\n".join(lines)
    check.validate_lvs(step, opened, False)
    for wrong in (
        text,
        opened.replace(
            ".subckt " + make.TOP + " CLKP", ".subckt " + make.TOP + " CLKN"
        ),
        opened.replace("Nx=4", "Nx=3", 1),
    ):
        with pytest.raises(ValueError):
            check.validate_lvs(step, wrong, False)
    step["audit"]["circuits"][0]["layout_devices_recursive"] = 61
    with pytest.raises(ValueError):
        check.validate_lvs(step, opened, False)


def test_well_fault_tracks_actual_relocated_native_bridge():
    generated = {
        "origin_translation_um": [0, -3.97],
        "instances": [
            {"name": "NTAP", "body_connection_geometry_um": "(399,16;411,119)"},
            {"name": "CTRL1", "bbox_um": "(399,49;406,61)"},
            {"name": "CTRL2", "bbox_um": "(399,79;406,91)"},
        ],
    }
    result = check.mutation_source(
        Path("input.gds"), Path("wrong.gds"), generated, "well_open"
    )
    assert "398.0" in result and "412.0" in result
    assert "335" not in result and "355" not in result
    generated["instances"][2]["bbox_um"] = "(399,62;406,74)"
    with pytest.raises(ValueError, match="well-only gap"):
        check.mutation_source(
            Path("input.gds"), Path("wrong.gds"), generated, "well_open"
        )
