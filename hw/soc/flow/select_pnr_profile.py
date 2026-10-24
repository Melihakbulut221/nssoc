#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Choose a physical profile whose SRAM instances match the mapped top.

This checks macro inventory, not physical correctness or timing closure.
Only a flattened, single-module mapped netlist is accepted. Historical
profiles remain available explicitly, but cannot silently omit new macros.
"""
import argparse
import json
from pathlib import Path
import re


def mapped_macros(path):
    text = Path(path).read_text()
    text = re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.S)
    modules = re.findall(r"\bmodule\s+(\w+)", text)
    if modules != ["soc_top"]:
        raise ValueError("Expected one flattened soc_top module")
    result = {}
    pattern = r"\b(RM_IHPSG13_\w+)\s+(\\\S+|\w+)\s*\("
    for master, name in re.findall(pattern, text):
        name = name.lstrip("\\")
        if name in result:
            raise ValueError(f"Duplicate macro instance: {name}")
        result[name] = master
    if not result:
        raise ValueError("Mapped netlist has no supported SRAM instances")
    return result


def configured_macros(config):
    result = {}
    for master, views in config.get("MACROS", {}).items():
        for name, placement in views.get("instances", {}).items():
            if name in result:
                raise ValueError(f"Duplicate configured macro instance: {name}")
            if "location" not in placement:
                raise ValueError(f"Macro has no floorplan location: {name}")
            result[name] = master
    return result


def select(netlist, directory, rom, override=None):
    directory = Path(directory).resolve()
    if override and not Path(override).resolve().is_relative_to(directory):
        raise ValueError(f"refusing: PNR_CONFIG must be under {directory}")
    actual = mapped_macros(netlist)
    candidates = [Path(override)] if override else [directory / name for name in (
        "config-interfaces-logicrom.json", "config-interfaces-synpre.json",
        "config-interfaces.json", "config-ecc-rom.json", "config-ecc.json",
        "config.json")]
    reasons = []
    for candidate in candidates:
        path = candidate.resolve()
        if not path.is_relative_to(directory):
            raise ValueError(f"refusing: PNR_CONFIG must be under {directory}")
        if not path.is_file():
            reasons.append(f"{path.name}: missing file")
            continue
        config = json.loads(path.read_text())
        if ("SOC_LOGIC_BOOT_ROM" in config.get("VERILOG_DEFINES", [])) != (rom == "logic"):
            reasons.append(f"{path.name}: ROM profile mismatch")
            continue
        planned = configured_macros(config)
        if planned == actual:
            return path
        missing = sorted(set(actual) - set(planned))
        extra = sorted(set(planned) - set(actual))
        types = sorted(n for n in actual.keys() & planned.keys() if actual[n] != planned[n])
        reasons.append(f"{path.name}: missing={missing}, extra={extra}, wrong_type={types}")
    raise ValueError("No matching physical profile; supply a matching PNR_CONFIG. " + "; ".join(reasons))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--netlist", required=True, type=Path)
    parser.add_argument("--directory", required=True, type=Path)
    parser.add_argument("--rom", choices=("legacy", "logic"), default="legacy")
    parser.add_argument("--config", type=Path)
    args = parser.parse_args()
    try:
        print(select(args.netlist, args.directory, args.rom, args.config))
    except (ValueError, OSError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
