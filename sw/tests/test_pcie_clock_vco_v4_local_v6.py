# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Exact local-route four-PMOS source and native extraction acceptance boundaries."""

import copy
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "hw/soc/flow"))
import check_pcie_clock_vco_v4_local_v6 as check
import make_pcie_clock_vco_v4_local_v6 as make

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
                device="REF",
                net="REF",
                source_layer=1,
                actual_pin_um="(400,140;402,140.2)",
                escape_lane_um=456,
                escape_y_um=140.1,
            ),
            dict(
                device="REF",
                net="REF",
                source_layer=1,
                actual_pin_um="(400,141;402,141.2)",
                escape_lane_um=459,
                escape_y_um=141.1,
            ),
            dict(
                device="REF",
                net="AVSS",
                source_layer=2,
                actual_pin_um="(400,140.5;402,140.7)",
                escape_lane_um=462,
                escape_y_um=140.6,
            ),
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


def return_array_witness():
    rows = [
        dict(device=n, landing_um=[x, 80.0])
        for n, x in zip(("T0", "T1", "T2", "REF"), (34, 190, 310, 394))
    ]
    expected = [("common_spine", 6, 7, [4, 145]), ("public_return", 5, 7, [4, 380])]
    for row in rows:
        expected += [
            (row["device"] + "_emitter", 2, 7, row["landing_um"]),
            (row["device"] + "_spine", 6, 7, [row["landing_um"][0], 145]),
        ]
    vias = []
    for name, bottom, top, center in expected:
        cuts = {}
        for i in range(bottom, top):
            layer = "Via" + str(i) if i <= 4 else "TopVia" + str(i - 4)
            cuts[layer] = [[j, 0, j + 0.1, 0.1] for j in range(8 if i <= 4 else 4)]
        vias.append(
            dict(
                return_role=name,
                net="AVSS",
                bottom=bottom,
                top=top,
                center_um=center,
                lower_array=[4, 2],
                upper_arrays=[2, 2],
                native_cut_boxes_um=cuts,
            )
        )
    return dict(local_bias_returns=rows, vias=vias)


def test_native_return_array_witness_positive():
    check.validate_return_arrays(return_array_witness())


@pytest.mark.parametrize(
    "fault",
    (
        "missing_stack",
        "duplicate_role",
        "wrong_net",
        "wrong_bottom",
        "wrong_center",
        "old_lower_array",
        "old_upper_array",
        "missing_layer",
        "extra_layer",
        "missing_cut",
        "duplicate_cut",
        "zero_cut",
    ),
)
def test_actual_return_cut_and_ownership_mutations_reject(fault):
    row = return_array_witness()
    stack = row["vias"][2]
    cuts = stack["native_cut_boxes_um"]
    if fault == "missing_stack":
        row["vias"].pop()
    elif fault == "duplicate_role":
        stack["return_role"] = row["vias"][0]["return_role"]
    elif fault == "wrong_net":
        stack["net"] = "SUB"
    elif fault == "wrong_bottom":
        stack["bottom"] = 1
    elif fault == "wrong_center":
        stack["center_um"] = [36, 80]
    elif fault == "old_lower_array":
        stack["lower_array"] = [4, 1]
    elif fault == "old_upper_array":
        stack["upper_arrays"] = [1, 1]
    elif fault == "missing_layer":
        cuts.pop("TopVia2")
    elif fault == "extra_layer":
        cuts["Via1"] = cuts["Via2"]
    elif fault == "missing_cut":
        cuts["Via2"].pop()
    elif fault == "duplicate_cut":
        cuts["Via2"][1] = cuts["Via2"][0]
    elif fault == "zero_cut":
        cuts["Via2"][1] = [0, 0, 0, 0]
    with pytest.raises(ValueError):
        check.validate_return_arrays(row)


def test_local_bias_route_census_and_wrong_body_or_link_rejected():
    positive = dict(
        local_bias_returns=[
            dict(
                device=n,
                net="AVSS",
                source_layer="Metal2",
                parallel_layer="TopMetal2",
                branch_width_um=4,
                common_spine_y_um=145,
            )
            for n in ["T0", "T1", "T2", "REF"]
        ],
        local_ref_diode=[dict(device="REF", net="REF", layer="Metal1", width_um=0.4)],
    )
    check.validate_local_bias_witness(positive)
    mutations = []
    for key, value in [
        ("net", "SUB"),
        ("net", "AVDD"),
        ("source_layer", "Metal1"),
        ("branch_width_um", 1.2),
    ]:
        row = copy.deepcopy(positive)
        row["local_bias_returns"][0][key] = value
        mutations.append(row)
    row = copy.deepcopy(positive)
    row["local_bias_returns"].pop()
    mutations.append(row)
    row = copy.deepcopy(positive)
    row["local_ref_diode"] = []
    mutations.append(row)
    row = copy.deepcopy(positive)
    row["local_ref_diode"][0]["net"] = "AVSS"
    mutations.append(row)
    for row in mutations:
        with pytest.raises(ValueError):
            check.validate_local_bias_witness(row)


def test_compact_stage_tracks_keep_exact_devices_and_separate_escapes():
    import make_pcie_clock_vco_v4_local_v5 as prior

    rows = make.devices(SOURCE)
    positions = make.placement(rows)
    old = prior.placement(rows)
    assert len(positions) == len(set(positions.values())) == 49
    lanes = [lane + offset for _, _, lane in positions.values() for offset in (0, 3, 6)]
    assert len(lanes) == len(set(lanes)) == 147
    assert min(b - a for a, b in zip(sorted(lanes), sorted(lanes)[1:])) >= 3
    for i in range(3):
        x = 85 + 90 * i
        for prefix in ("P", "N", "T"):
            assert positions[prefix + str(i)][0] == x
        for prefix in ("RP", "CP", "CN"):
            assert positions[prefix + str(i)][0] == x + 30
        assert positions["RN" + str(i)][0] == x + 36
    assert positions["P2"][0] - positions["P0"][0] == 180
    assert old["P2"][0] - old["P0"][0] == 240
    for name in ("CTRL0", "CTRL1", "CTRL2", "CTRL3", "REF", "RB", "BREF"):
        assert positions[name] == old[name]
    assert make.devices(SOURCE) == prior.devices(SOURCE)
    assert make.physical_reference(SOURCE).replace(
        make.TOP, prior.TOP
    ) == prior.physical_reference(SOURCE)
    for wrong in (rows[:-1], rows + [dict(rows[0], name="OTHER")]):
        with pytest.raises(ValueError, match="placement census"):
            make.placement(wrong)


def test_narrow_native_ring_escapes_and_return_array_recipe_unchanged():
    import inspect
    import make_pcie_clock_vco_v4_local_v5 as prior

    a = inspect.getsource(make.main)
    b = inspect.getsource(prior.main)
    for function, end in [
        ("escape", "    for row in rows:"),
        ("via", "    def escape("),
    ]:
        assert (
            a.split("    def " + function + "(", 1)[1].split(end, 1)[0]
            == b.split("    def " + function + "(", 1)[1].split(end, 1)[0]
        )


def placement_witness():
    positions = make.placement(make.devices(SOURCE))
    rows = [
        dict(r, placement_um=list(positions[r["name"]][:2]))
        for r in make.devices(SOURCE)
    ]
    rows += [
        dict(
            name="NTAP",
            kind="well_tap",
            nets=["AVDD", "NWELL"],
            placement_um=[408, 23],
            area_um2=4,
            perimeter_um=8,
        )
    ]
    rows += [
        dict(
            name="TAP" + str(i),
            kind="substrate_tap",
            nets=["SUB", "BULK"],
            placement_um=[7 + 4 * i, 4],
            area_um2=4,
            perimeter_um=8,
        )
        for i in range(12)
    ]
    return dict(instances=rows)


def test_exact_all_native_placement_positive():
    check.validate_placement(placement_witness())


@pytest.mark.parametrize(
    "fault",
    [
        "missing",
        "duplicate",
        "position",
        "nx",
        "body",
        "tap_position",
        "tap_area",
        "well_net",
    ],
)
def test_native_placement_and_body_mutations_reject(fault):
    row = placement_witness()
    items = row["instances"]
    if fault == "missing":
        items.pop()
    elif fault == "duplicate":
        items[-1] = copy.deepcopy(items[-2])
    elif fault == "position":
        items[0]["placement_um"][0] += 0.005
    elif fault == "nx":
        next(r for r in items if r["kind"] == "hbt")["nx"] += 1
    elif fault == "body":
        next(r for r in items if r["kind"] == "hbt")["nets"][-1] = "AVSS"
    elif fault == "tap_position":
        items[-1]["placement_um"][0] += 0.005
    elif fault == "tap_area":
        items[-1]["area_um2"] = 48
    elif fault == "well_net":
        next(r for r in items if r["name"] == "NTAP")["nets"][-1] = "AVDD"
    with pytest.raises(ValueError):
        check.validate_placement(row)


@pytest.mark.parametrize("reverse", [False, True])
def test_actual_emitter_gap_is_independent_of_left_right_order(reverse):
    rows = [
        dict(
            actual_pin_um="(60.255,49.215;63.595,50.77)",
            escape_lane_um=75,
            escape_y_um=49.99,
        ),
        dict(
            actual_pin_um="(84.255,49.215;87.595,50.77)",
            escape_lane_um=120,
            escape_y_um=49.99,
        ),
    ]
    if reverse:
        rows.reverse()
    assert check.emitter_gap(rows) == (75, 85.925, 49.99)


@pytest.mark.parametrize("fault", ["overlap", "unaligned", "missing", "wrong_pin"])
def test_emitter_fault_requires_an_actual_gap(fault):
    rows = [
        dict(
            actual_pin_um="(60.255,49.215;63.595,50.77)",
            escape_lane_um=75,
            escape_y_um=49.99,
        ),
        dict(
            actual_pin_um="(84.255,49.215;87.595,50.77)",
            escape_lane_um=120,
            escape_y_um=49.99,
        ),
    ]
    if fault == "overlap":
        rows[0]["escape_lane_um"] = 90
    elif fault == "unaligned":
        rows[0]["escape_y_um"] = 51
    elif fault == "missing":
        rows.pop()
    else:
        rows[0]["actual_pin_um"] = "missing"
    with pytest.raises(ValueError):
        check.emitter_gap(rows)
