# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
import importlib.util
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("profile", ROOT / "hw/soc/flow/select_pnr_profile.py")
profile = importlib.util.module_from_spec(spec)
spec.loader.exec_module(profile)


@pytest.fixture
def design(tmp_path):
    master = "RM_IHPSG13_1P_2048x64_c2_bm_bist"
    netlist = tmp_path / "mapped.v"
    netlist.write_text(f"module soc_top();\n{master} \\u_ram.ecc.u_b0  (.A_CLK(clk));\nendmodule\n")
    directory = tmp_path / "pnr"
    directory.mkdir()
    config = directory / "config-ecc-rom.json"
    config.write_text(json.dumps({"MACROS": {master: {"instances": {
        "u_ram.ecc.u_b0": {"location": [0, 0]}}}}}))
    return netlist, directory, config, master


def test_hardened_default_matches_mapped_names_without_loading_a_pdk(design):
    netlist, directory, config, master = design
    assert profile.mapped_macros(netlist) == {"u_ram.ecc.u_b0": master}
    assert profile.select(netlist, directory, "legacy") == config


@pytest.mark.parametrize("defect", ["missing", "extra", "type", "rom", "location"])
def test_explicit_profile_cannot_hide_incompatible_macro_inventory(design, defect):
    netlist, directory, config, master = design
    data = json.loads(config.read_text())
    if defect == "missing": data["MACROS"][master]["instances"].clear()
    if defect == "extra": data["MACROS"][master]["instances"]["u_obsolete"] = {"location": [1, 2]}
    if defect == "type": data["MACROS"]["RM_IHPSG13_wrong"] = data["MACROS"].pop(master)
    if defect == "rom": data["VERILOG_DEFINES"] = ["SOC_LOGIC_BOOT_ROM"]
    if defect == "location": data["MACROS"][master]["instances"]["u_ram.ecc.u_b0"] = {}
    config.write_text(json.dumps(data))
    with pytest.raises(ValueError): profile.select(netlist, directory, "legacy", config)


def test_symlink_cannot_escape_the_physical_directory(design, tmp_path):
    netlist, directory, config, _ = design
    outside = tmp_path / "outside.json"
    outside.write_bytes(config.read_bytes())
    link = directory / "escape.json"
    link.symlink_to(outside)
    with pytest.raises(ValueError, match="PNR_CONFIG must be under"):
        profile.select(netlist, directory, "legacy", link)


@pytest.mark.parametrize("text", ["module soc_top(); endmodule", "module other(); endmodule"])
def test_unmapped_or_wrong_top_is_rejected(design, text):
    netlist, directory, _, _ = design
    netlist.write_text(text)
    with pytest.raises(ValueError): profile.select(netlist, directory, "legacy")


def test_duplicate_macro_is_not_silently_overwritten(design):
    netlist, _, _, master = design
    netlist.write_text(netlist.read_text().replace("endmodule", f"{master} \\u_ram.ecc.u_b0 ();\nendmodule"))
    with pytest.raises(ValueError, match="Duplicate"): profile.mapped_macros(netlist)


def test_mbist_fifo_floorplan_and_power_match_all_banks(tmp_path):
    directory = ROOT / "hw/soc/pnr"
    legacy = json.loads((directory / "config-interfaces-logicrom.json").read_text())
    path = directory / "config-interfaces-mbist-logicrom.json"
    config = json.loads(path.read_text())
    master = "RM_IHPSG13_2P_256x16_c2_bm_bist"
    placements = config["MACROS"][master]["instances"]
    expected = {}
    for direction in ("rx", "tx"):
        for bank in range(8):
            prefix = f"u_eth.u_mac.{direction}_fifo.fifo_inst"
            name = f"{prefix}.u_sram.g_bank[{bank}].u_mem"
            expected[name] = legacy["MACROS"][master]["instances"][f"{prefix}.mem.0.{bank}"]
            odb_name = name.replace("[", r"\[").replace("]", r"\]")
            connections = [rule.split()[1:] for rule in config["PDN_MACRO_CONNECTIONS"]
                           if re.fullmatch(rule.split()[0], odb_name)]
            assert sorted(connections) == [["VPWR", "VGND", pin, "VSS!"]
                                           for pin in ("VDD!", "VDDARRAY!")]
    assert placements == expected
    mapped = tmp_path / "soc.v"
    mapped.write_text("module soc_top();\n" + "".join(
        f"{cell} \\{name} ();\n" for name, cell in profile.configured_macros(config).items()
    ) + "endmodule\n")
    assert profile.select(mapped, directory, "logic") == path
