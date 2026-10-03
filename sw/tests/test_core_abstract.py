# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Reject under-covered obstructions and changed hard-core interfaces."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "compact_core_abstract", ROOT / "hw/soc/flow/compact_core_abstract.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def source(tmp_path):
    path = tmp_path / "source.lef"
    header = "MACRO core\n  PIN A\n  END A\n  OBS\n"
    boxes = "    RECT -0.005 0 1 2 ;\n    RECT 3 4 5 6 ;\n"
    path.write_text(header + "".join(
        f"    LAYER {layer} ;\n" + boxes
        for layer in ["Metal1", "Metal2", "Metal3", "Metal4", "Metal5",
                      "TopMetal1", "TopMetal2"]) + "  END\nEND core\n")
    return path


def test_compaction_keeps_interface_upper_metal_and_covers_gaps(tmp_path):
    original, output = source(tmp_path), tmp_path / "compact.lef"
    result = MODULE.compact(original, output)
    assert result["output"]["counts"]["Metal1"] == 1
    assert result["output"]["bounds"]["Metal1"] == [-0.005, 0, 5, 6]
    assert result["output"]["counts"]["TopMetal2"] == 2
    assert result["output"]["outside_sha256"] == result["source"]["outside_sha256"]
    assert result["timing_accepted"] is False


@pytest.mark.parametrize("fault", ["lost_upper", "shrunken_lower", "changed_pin"])
def test_real_candidate_mutations_are_rejected(tmp_path, fault):
    original, output = source(tmp_path), tmp_path / "compact.lef"
    MODULE.compact(original, output)
    text = output.read_text()
    if fault == "lost_upper":
        text = text.replace("    RECT 3 4 5 6 ;\n", "", 1)
    elif fault == "shrunken_lower":
        text = text.replace("-0.005000000", "0.000000000", 1)
    else:
        text = text.replace("PIN A", "PIN B", 1)
    output.write_text(text)
    with pytest.raises(ValueError):
        MODULE.verify(original, output)


@pytest.mark.parametrize("fault", ["nan", "reversed", "unknown_syntax", "missing_layer"])
def test_invalid_source_is_rejected_without_creating_a_view(tmp_path, fault):
    original = source(tmp_path)
    text = original.read_text()
    if fault == "nan":
        text = text.replace("-0.005", "nan", 1)
    elif fault == "reversed":
        text = text.replace("RECT -0.005 0 1 2", "RECT 2 0 1 2", 1)
    elif fault == "unknown_syntax":
        text = text.replace("RECT", "POLYGON", 1)
    else:
        text = text.replace("LAYER TopMetal2", "LAYER Other", 1)
    original.write_text(text)
    output = tmp_path / "invalid.lef"
    with pytest.raises(ValueError):
        MODULE.compact(original, output)
    assert not output.exists()
