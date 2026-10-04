# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Fail-closed patch boundary; physical acceptance needs separate native data."""

import hashlib
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import patch_magic_cap_precision_v3 as patcher  # noqa: E402

SIMPLE = '''void
ResDistributeCapacitance(nodelist, totalcap)
    resNode *nodelist;
    float totalcap;
{
    float totalarea = 0, capperarea;
    totalarea += nodelist->rn_float.rn_area;
    capperarea = totalcap / totalarea;
    nodelist->rn_float.rn_area *= capperarea;
}
void legacy(void) { (void) ResDistributeCapacitance(ResNodeList, resisdata->rg_nodecap); }
void unreduced(void) {
    TxPrintf("NSSOC_V2_INTRINSIC_DISTRIBUTION %s total=%g intrinsic=%g\\n", name, a, b);
    (void) ResDistributeCapacitance(ResNodeList, resisdata->rg_intrinsiccap);
}
'''
PRINT = r'fprintf(fp, "rnode \"%s\" 0 %g %d %d %d\n", name, c, x, y, 0);'


@pytest.fixture
def source(tmp_path, monkeypatch):
    root = tmp_path / "source"
    for name, value in {"resis/ResSimple.c": SIMPLE, "resis/ResPrint.c": PRINT,
                        "resis/resis.h": "struct native { float area; };\n"}.items():
        p = root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(value)
        monkeypatch.setitem(patcher.PINS, name, hashlib.sha256(value.encode()).hexdigest())
    return root


def test_precise_path_keeps_legacy_and_header(source, tmp_path):
    before = {p.name: p.read_bytes() for p in source.rglob("*") if p.is_file()}
    output = tmp_path / "private"
    result = patcher.patch(source, output)
    text = (output / "resis/ResSimple.c").read_text()
    original_function = SIMPLE[:SIMPLE.index("void legacy")]
    assert original_function in text
    assert "void legacy(void) { (void) ResDistributeCapacitance(ResNodeList, resisdata->rg_nodecap); }" in text
    assert text.count("    double totalarea = 0, capperarea;") == 1
    assert text.count("    float totalarea = 0, capperarea;") == 1
    assert "ResDistributeIntrinsicCapacitancePrecise(ResNodeList, resisdata->rg_intrinsiccap)" in text
    assert "total=%.17g intrinsic=%.17g" in text
    assert not (output / "resis/resis.h").exists()
    assert before == {p.name: p.read_bytes() for p in source.rglob("*") if p.is_file()}
    assert result["native_acceptance"] is False


@pytest.mark.parametrize("name", sorted(patcher.PINS))
def test_unknown_c_or_abi_header_rejected(source, tmp_path, name):
    path = source / name
    path.write_text(path.read_text() + "/* changed */")
    output = tmp_path / "private"
    with pytest.raises(ValueError, match="Frozen native source changed"):
        patcher.patch(source, output)
    assert not output.exists()


@pytest.mark.parametrize("relative,text", [
    ("resis/ResSimple.c", SIMPLE.replace("float totalarea = 0", "float totalarea = 1")),
    ("resis/ResSimple.c", SIMPLE + patcher.EDITS["resis/ResSimple.c"][0][0]),
    ("resis/ResPrint.c", PRINT + PRINT),
    ("resis/ResPrint.c", PRINT.replace(" 0 %g ", " 0 %e ")),
])
def test_missing_or_duplicate_construct_rejected(relative, text):
    with pytest.raises(ValueError):
        patcher.transform(relative, text)


def test_header_never_transformable():
    with pytest.raises(ValueError, match="Only the two"):
        patcher.transform("resis/resis.h", "native")


def test_existing_output_not_overwritten(source, tmp_path):
    output = tmp_path / "private"
    output.mkdir()
    (output / "keep").write_text("existing")
    with pytest.raises(ValueError, match="Fresh private"):
        patcher.patch(source, output)
    assert (output / "keep").read_text() == "existing"
