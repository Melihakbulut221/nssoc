# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Route metadata cleanup must leave real connections and ambiguous nets intact."""
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    "signal,ports,directions,guides,clear_works,expected",
    [
        ("SIGNAL", 0, ["OUTPUT"], 6, True, "REMOVED=6 LEFT=0"),
        ("SIGNAL", 0, ["OUTPUT"], 0, True, "REMOVED=0 LEFT=0"),
        ("SIGNAL", 0, ["OUTPUT", "INPUT"], 6, True, "REMOVED=0 LEFT=6"),
        ("SIGNAL", 1, ["OUTPUT"], 6, True, "REMOVED=0 LEFT=6"),
        ("SIGNAL", 0, ["INPUT"], 6, True, "REMOVED=0 LEFT=6"),
        ("SIGNAL", 0, ["INOUT"], 6, True, "REMOVED=0 LEFT=6"),
        ("SIGNAL", 0, [], 6, True, "REMOVED=0 LEFT=6"),
        ("CLOCK", 0, ["OUTPUT"], 6, True, "REMOVED=0 LEFT=6"),
        ("POWER", 0, ["OUTPUT"], 6, True, "REMOVED=0 LEFT=6"),
        ("GROUND", 0, ["OUTPUT"], 6, True, "REMOVED=0 LEFT=6"),
        ("SIGNAL", 0, ["OUTPUT"], 6, False, "ERROR=Failed to clear stale guides"),
    ],
)
def test_only_unloaded_internal_output_guides_are_cleared(
    signal, ports, directions, guides, clear_works, expected
):
    tclsh = shutil.which("tclsh")
    if not tclsh:
        pytest.skip("tclsh is required to exercise the OpenROAD Tcl cleanup")
    script = f"source {{{ROOT / 'hw/soc/flow/prune_orphan_guides.tcl'}}}\n"
    script += f"set guides [lrepeat {guides} guide]\n"
    for i, direction in enumerate(directions):
        script += f'proc pin{i} {{method}} {{if {{$method ne "getIoType"}} {{error "unexpected pin mutation"}}; return {direction}}}\n'
    script += "proc block {method} {if {$method ne \"getNets\"} {error \"unexpected block mutation\"}; return net}\n"
    script += f"""
proc net {{method}} {{
    global guides
    switch -- $method {{
        getSigType {{return {signal}}}
        getBTerms {{return [lrepeat {ports} port]}}
        getITerms {{return {{{' '.join(f'pin{i}' for i in range(len(directions)))}}}}}
        getGuides {{return $guides}}
        getName {{return orphan}}
        clearGuides {{{'set guides {}' if clear_works else 'return'}}}
        default {{error "unexpected net mutation: $method"}}
    }}
}}
if {{[catch {{prune_orphan_guides block}} result]}} {{
    puts "ERROR=$result"
}} else {{
    puts "REMOVED=$result LEFT=[llength $guides]"
}}
"""
    result = subprocess.run([tclsh], input=script, text=True, capture_output=True)
    assert result.returncode == 0 and not result.stderr, result.stderr
    assert expected in result.stdout
    if "REMOVED=0" in expected:
        assert "ORPHAN_GUIDES" not in result.stdout
