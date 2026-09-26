# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Integration receipt guard: a success marker never overrides simulation errors."""

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "chip_mbist", ROOT / "scripts/check_soc_mbist_integration.py"
)
mbist = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mbist)


@pytest.mark.parametrize(
    "log",
    [
        "PASS chip\n%Fatal: incomplete raw test",
        "PASS chip\n%Error: simulation failed",
        "FATAL: bad comparison\nPASS chip",
        "PASS chip\nERROR: timeout",
        "PASS chip\nAssertion failed",
        "no result",
    ],
)
def test_pass_marker_cannot_hide_simulator_failure(log):
    assert not mbist.passed_log(log)


def test_clean_independent_verdict_is_required():
    assert mbist.passed_log("MBIST completed\nPASS chip MBIST accesses=655360\n")


@pytest.mark.parametrize(
    "enabled,logic", [(False, False), (False, True), (True, False), (True, True)]
)
def test_physical_config_mbist_profile_preserves_settings(tmp_path, enabled, logic):
    import json
    import os
    import subprocess
    import sys

    text = (ROOT / "hw/soc/flow/pnr_soc_top.sh").read_text()
    start = text.index("import json, os, sys\nsrc, dst = sys.argv[1], sys.argv[2]")
    generator = text[start : text.index("\nPY", start)]
    generator = generator.replace("$SRCS", "/test/core.v /test/top.v").replace(
        "$IF_DEFINE", ""
    )
    original = {
        "CLOCK_PERIOD": 20,
        "MACROS": {"example": {"unchanged": True}},
        "VERILOG_DEFINES": ["USER_SETTING"] + (["SOC_LOGIC_BOOT_ROM"] if logic else []),
    }
    src, dst = tmp_path / "config.json", tmp_path / "resolved.json"
    src.write_text(json.dumps(original))
    p = subprocess.run(
        [sys.executable, "-c", generator, str(src), str(dst)],
        env=dict(
            os.environ,
            SOC_BOOT_ROM="logic" if logic else "legacy",
            SOC_SRAM_MBIST="1" if enabled else "0",
        ),
        capture_output=True,
        text=True,
    )
    if enabled and not logic:
        assert p.returncode != 0 and "MBIST requires immutable logic ROM" in p.stderr
        assert not dst.exists()
    else:
        assert p.returncode == 0, p.stderr
        actual = json.loads(dst.read_text())
        assert actual.pop("VERILOG_FILES") == ["/test/core.v", "/test/top.v"]
        if enabled:
            actual["VERILOG_DEFINES"].remove("SOC_SRAM_MBIST")
        assert actual == original
