# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Declared I/O substrate globals survive dialect conversion and cell selection."""
import sys
from pathlib import Path
import subprocess

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "hw/soc/flow"))
from io_cell_schematic import global_line, parse_io_cdl, select_io_cdl  # noqa: E402
from normalize_io_cdl import normalize  # noqa: E402

CHILD = ".SUBCKT child a b\nR0 a sub! 1000\nR1 sub! b 1000\n.ENDS child"
TOP = ".SUBCKT top a b c d\nX0 a b child\nX1 c d child\n.ENDS top"
UNUSED = ".SUBCKT unused a\nR0 a local! 17\n.ENDS unused"
BODY = "\n\n".join([CHILD, TOP, UNUSED]) + "\n"


def test_vendor_global_and_selected_primitive_bodies_survive():
    original = "*.GLOBAL sub!\n" + BODY
    normalized, changes = normalize(original)
    assert normalized == ".GLOBAL sub!\n" + BODY
    assert len(changes) == 1
    assert changes[0]["reason"] == "native_explicit_global_declaration"
    assert changes[0]["before"] == "*.GLOBAL sub!\n"
    assert normalize(normalized) == (normalized, [])
    selected, definitions, names = select_io_cdl(normalized, "TOP")
    assert names == ["sub!"]
    assert definitions == {"child": CHILD, "top": TOP}
    assert selected == ".GLOBAL sub!\n" + CHILD + "\n\n" + TOP + "\n"
    assert select_io_cdl(original, "top") == (selected, definitions, names)


def test_names_are_never_inferred_as_globals():
    selected, _, names = select_io_cdl(BODY, "top")
    assert not names
    assert ".GLOBAL" not in selected
    assert "sub!" in selected


def test_case_preservation_and_repeated_identical_declarations():
    definitions, names = parse_io_cdl("*.GLOBAL sub! WELL!\n.GLOBAL sub!\n" + BODY)
    assert names == ["sub!", "WELL!"]
    assert definitions["child"] == CHILD
    with pytest.raises(ValueError, match="Ambiguous global-name case"):
        parse_io_cdl("*.GLOBAL sub!\n.GLOBAL SUB!\n" + BODY)


@pytest.mark.parametrize("line", ["*.GLOBAL", ".GLOBAL", "*.GLOBAL {substrate}",
                                  "*.GLOBAL sub! sub!", ".GLOBAL sub! $comment"])
def test_ambiguous_or_empty_global_declarations_fail_closed(line):
    with pytest.raises(ValueError):
        global_line(line)
    with pytest.raises(ValueError):
        normalize(line + "\n" + BODY)


@pytest.mark.parametrize("outside", [".INCLUDE other.cir", ".CONNECT iovss vss", "+ sub!"])
def test_other_directives_are_not_discarded(outside):
    with pytest.raises(ValueError, match="outside subcircuits"):
        select_io_cdl(outside + "\n" + BODY, "top")


def test_local_global_declaration_is_rejected():
    with pytest.raises(ValueError, match="outside subcircuits"):
        select_io_cdl(CHILD.replace("R0", "*.GLOBAL sub!\nR0"), "child")


def test_missing_child_is_still_an_error():
    with pytest.raises(ValueError, match="Unresolved CDL subcircuit"):
        select_io_cdl("*.GLOBAL sub!\n" + TOP, "top")


def test_global_like_prose_stays_a_comment():
    text = "* global substrate note\n* .GLOBAL is not an explicit CDL directive\n" + BODY
    assert normalize(text) == (text, [])
    assert select_io_cdl(text, "top")[2] == []


@pytest.mark.parametrize("script", ["normalize_io_cdl.py", "io_cell_schematic.py"])
@pytest.mark.parametrize("fault", ["output_receipt_alias", "crlf"])
def test_cli_rejects_ambiguous_outputs_and_newline_conversion(tmp_path, script, fault):
    source = tmp_path / "source.cdl"
    text = "*.GLOBAL sub!\n" + BODY
    source.write_bytes(text.replace("\n", "\r\n").encode() if fault == "crlf" else text.encode())
    output = tmp_path / "selected.cir"
    receipt = output if fault == "output_receipt_alias" else tmp_path / "receipt.json"
    command = [sys.executable, str(Path(__file__).resolve().parents[2] / "hw/soc/flow" / script),
               str(source), str(output), "--receipt", str(receipt)]
    if script == "io_cell_schematic.py":
        command += ["--top", "top"]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    assert completed.returncode != 0
    assert ("distinct paths" if fault == "output_receipt_alias" else "LF newlines") in completed.stderr
    assert not output.exists()
    assert not receipt.exists()


def test_string_api_also_rejects_crlf():
    text = BODY.replace("\n", "\r\n")
    with pytest.raises(ValueError, match="LF newlines"):
        normalize(text)
    with pytest.raises(ValueError, match="LF newlines"):
        select_io_cdl(text, "top")
